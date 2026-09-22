# -*- coding: utf-8 -*-
import os

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager

from app.extensions import db, login_manager
from app.models import User
from config import Config

login_manager.login_view = None


@login_manager.unauthorized_handler
def _unauthorized():
    from flask import jsonify

    return jsonify({'ok': False, 'message': '未登录或会话已过期', 'code': 'unauthorized'}), 401


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 识别 nginx / 负载均衡后的 X-Forwarded-*，保证 HTTPS 下 Session Cookie 正确
    if os.environ.get('BEHIND_PROXY', 'false').lower() in ('1', 'true', 'yes'):
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)

    # 补齐 ORM 新表（仅首次空库；已有表时跳过以加快重启）
    import app.models as _app_models  # noqa: F401

    from app.startup import ensure_db_tables

    ensure_db_tables(app)

    @app.before_request
    def _resolve_device_bearer_auth():
        """桌面客户端 Bearer 令牌与 Web Session 并存；仅在有 Authorization 头时生效。"""
        from flask import request
        from flask_login import current_user, login_user

        if current_user.is_authenticated:
            return None
        path = request.path or ''
        if not path.startswith('/api/v1/'):
            return None
        from app.utils.client_auth import _bearer_token
        from app.services.device_auth import resolve_user_by_access_token

        token = _bearer_token()
        if not token:
            return None
        user = resolve_user_by_access_token(token)
        if user:
            login_user(user, remember=False)
        return None

    CORS(
        app,
        supports_credentials=True,
        origins=os.environ.get(
            'CORS_ORIGINS',
            'http://127.0.0.1:5321,http://localhost:5321,http://127.0.0.1:5173,http://localhost:5173',
        ).split(','),
    )

    from app.api.admin import admin_api
    from app.api.admin_logs import admin_logs_api
    from app.api.auth import auth_api
    from app.api.i18n import i18n_api
    from app.api.org import org_api
    from app.api.uploads import files_api, public_files_api, uploads_api
    from app.api.users import users_api
    from app.api.forms import forms_api
    from app.api.workflow import workflow_api
    from app.api.option_sets import option_sets_api
    from app.api.exchange_rates import exchange_rates_api
    from app.api.llm_providers import llm_providers_api
    from app.api.ai_recognition import ai_recognition_api
    from app.api.print_templates import print_templates_api
    from app.api.client import client_api
    from app.api.leave_calendar import leave_calendar_api
    from app.api.holidays import holidays_api

    app.register_blueprint(auth_api, url_prefix='/api/v1/auth')
    app.register_blueprint(org_api, url_prefix='/api/v1/org')
    app.register_blueprint(i18n_api, url_prefix='/api/v1/i18n')
    app.register_blueprint(workflow_api, url_prefix='/api/v1/workflow')
    app.register_blueprint(forms_api, url_prefix='/api/v1/forms')
    app.register_blueprint(users_api, url_prefix='/api/v1/users')
    app.register_blueprint(admin_api, url_prefix='/api/v1/admin')
    app.register_blueprint(client_api, url_prefix='/api/v1/client')
    app.register_blueprint(print_templates_api, url_prefix='/api/v1')
    app.register_blueprint(admin_logs_api, url_prefix='/api/v1/admin')
    app.register_blueprint(leave_calendar_api, url_prefix='/api/v1')
    app.register_blueprint(holidays_api, url_prefix='/api/v1')

    from app.services.audit_log_service import log_api_access_after_request

    @app.after_request
    def _audit_api_access(response):
        try:
            log_api_access_after_request(response.status_code)
        except Exception:
            pass
        return response
    app.register_blueprint(option_sets_api, url_prefix='/api/v1')
    app.register_blueprint(exchange_rates_api, url_prefix='/api/v1')
    app.register_blueprint(llm_providers_api, url_prefix='/api/v1')
    app.register_blueprint(ai_recognition_api, url_prefix='/api/v1')
    app.register_blueprint(uploads_api, url_prefix='/api/v1/uploads')
    app.register_blueprint(files_api, url_prefix='/api/v1/files')
    app.register_blueprint(public_files_api, url_prefix='/api/v1/public/files')

    @app.route('/api/v1/health')
    def health():
        return {'ok': True, 'message': '服务正常'}

    dist = os.path.join(
        os.path.dirname(app.root_path),
        '..',
        'frontend',
        'dist',
    )
    dist = os.path.abspath(dist)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def spa_fallback(path):
        if path.startswith('api/'):
            return {'ok': False, 'message': '接口不存在'}, 404
        index = os.path.join(dist, 'index.html')
        if os.path.isfile(index):
            if path and os.path.isfile(os.path.join(dist, path)):
                return send_from_directory(dist, path)
            return send_from_directory(dist, 'index.html')
        return {
            'ok': True,
            'message': 'IMC Workflow API 已运行；请构建前端 frontend/dist',
        }

    return app
