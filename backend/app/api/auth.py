# -*- coding: utf-8 -*-
import base64
import os
import re
import secrets
import urllib.parse
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, current_app, redirect, request, session
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import LoginEmailCode, LoginSmsCode, User
from app.services.captcha import issue_login_captcha, verify_login_captcha_payload
from app.services.audit_log_service import record_auth_event, record_page_view_event
from app.services.notify import send_login_email_code, send_login_sms_code
from app.services.org_service import user_display_job_title
from app.services.permissions import admin_capabilities
from app.utils.branding import APP_DISPLAY_NAME
from app.utils.response import fail, ok
from app.utils.user_utils import (
    find_user_by_login_identifier,
    normalize_email,
    normalize_phone,
)

auth_api = Blueprint('auth_api', __name__)

DESKTOP_CLIENT_HEADER = 'X-TPC-Client'
DESKTOP_CLIENT_VALUE = 'desktop'


def _is_desktop_client_request() -> bool:
    """Windows 桌面客户端：请求头标识，仅用于邮箱验证码流程免图形验证码（Web 不受影响）。"""
    from flask import request

    if (request.headers.get(DESKTOP_CLIENT_HEADER) or '').strip().lower() == DESKTOP_CLIENT_VALUE:
        return True
    data = request.get_json(silent=True) or {}
    return (data.get('client_channel') or '').strip().lower() == DESKTOP_CLIENT_VALUE


def _verify_login_captcha_optional(data: dict) -> tuple[bool, str]:
    if _is_desktop_client_request():
        return True, ''
    return verify_login_captcha_payload(data, consume=True)


def _project_upload_base() -> str:
    return os.path.abspath(os.path.join(current_app.root_path, '..', 'uploads'))


def _normalize_avatar_path(raw: str | None) -> str | None:
    if not raw:
        return None
    path = str(raw).replace('\\', '/').strip()
    if not path:
        return None
    if path.startswith('uploads/'):
        return path
    if '/' not in path:
        return f'uploads/avatars/{path}'
    return path


def _avatar_public_url(user: User) -> str | None:
    rel = _normalize_avatar_path(user.avatar_path)
    if not rel:
        return None
    return f'/api/v1/files/{rel}'


@auth_api.route('/captcha', methods=['GET'])
def get_captcha():
    """获取登录图形验证码（无需登录）。"""
    return ok(issue_login_captcha())


@auth_api.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    mode = (data.get('mode') or 'password').strip()
    if mode == 'email_code':
        return _login_email_code(data)
    if mode == 'sms_code':
        return _login_sms_code(data)
    return _login_password(data)


def _login_password(data: dict):
    ok_cap, msg = verify_login_captcha_payload(data, consume=True)
    if not ok_cap:
        return fail(msg, status=400)
    identifier = (data.get('username') or data.get('identifier') or '').strip()
    password = data.get('password') or ''
    if not identifier or not password:
        return fail('请输入账号与密码', status=400)
    user = find_user_by_login_identifier(identifier)
    if not user or not user.check_password(password):
        record_auth_event(
            'login_failed',
            status='fail',
            subject=identifier,
            message='账号或密码错误',
            detail={'mode': 'password'},
        )
        return fail('账号或密码错误', status=401)
    login_user(user, remember=bool(data.get('remember')))
    record_auth_event(
        'login_success',
        user_id=user.id,
        subject=user.display_label(),
        message='密码登录',
        detail={'mode': 'password'},
    )
    return ok(_user_payload(user), '登录成功')


@auth_api.route('/device/register', methods=['POST'])
@login_required
def device_register():
    """登录后注册 Windows 客户端设备令牌（不影响 Web Session）。"""
    from app.services.device_auth import register_device

    data = request.get_json(silent=True) or {}
    try:
        payload = register_device(
            current_user,
            device_uid=data.get('device_uid') or data.get('device_id'),
            device_name=data.get('device_name'),
        )
    except ValueError as exc:
        return fail(str(exc))
    return ok(payload, '设备已注册')


@auth_api.route('/device/refresh', methods=['POST'])
def device_refresh():
    """使用刷新令牌换取新的访问令牌（无需 Session）。"""
    from app.services.device_auth import refresh_device_tokens

    data = request.get_json(silent=True) or {}
    payload = refresh_device_tokens(
        device_uid=data.get('device_uid') or data.get('device_id'),
        refresh_token=data.get('refresh_token') or '',
    )
    if not payload:
        return fail('刷新令牌无效或已过期', status=401, code='unauthorized')
    return ok(payload, '令牌已刷新')


@auth_api.route('/device', methods=['GET'])
@login_required
def device_list():
    from app.services.device_auth import list_user_devices

    return ok(list_user_devices(current_user.id))


@auth_api.route('/device/<int:device_id>', methods=['DELETE'])
@login_required
def device_revoke(device_id: int):
    from app.services.device_auth import revoke_device

    if not revoke_device(current_user, device_id):
        return fail('设备不存在', status=404)
    return ok(None, '设备已注销')


def _login_email_code(data: dict):
    ok_cap, msg = _verify_login_captcha_optional(data)
    if not ok_cap:
        return fail(msg, status=400)
    email = normalize_email(data.get('email'))
    code = (data.get('code') or '').strip()
    if not email or not code:
        return fail('请输入邮箱与验证码')
    user = User.query.filter(db.func.lower(User.email) == email, User.is_active.is_(True)).first()
    if not user:
        record_auth_event(
            'login_failed',
            status='fail',
            subject=email,
            message='邮箱未绑定账号',
            detail={'mode': 'email_code'},
        )
        return fail('该邮箱未绑定系统账号')
    row = LoginEmailCode.query.filter_by(email=email).order_by(LoginEmailCode.id.desc()).first()
    if not row or row.expires_at < datetime.now():
        record_auth_event(
            'login_failed',
            status='fail',
            user_id=user.id,
            subject=email,
            message='验证码已过期',
            detail={'mode': 'email_code'},
        )
        return fail('验证码已过期，请重新获取')
    if not check_password_hash(row.code_hash, code):
        record_auth_event(
            'login_failed',
            status='fail',
            user_id=user.id,
            subject=email,
            message='验证码错误',
            detail={'mode': 'email_code'},
        )
        return fail('验证码错误')
    LoginEmailCode.query.filter_by(email=email).delete(synchronize_session=False)
    db.session.commit()
    login_user(user, remember=True)
    record_auth_event(
        'login_success',
        user_id=user.id,
        subject=user.display_label(),
        message='邮箱验证码登录',
        detail={'mode': 'email_code'},
    )
    payload = _user_payload(user)
    msg = '登录成功'
    if payload.get('need_set_password'):
        msg = '登录成功，请在右上角头像菜单中设置登录密码'
    return ok(payload, msg)


def _login_sms_code(data: dict):
    ok_cap, msg = verify_login_captcha_payload(data, consume=True)
    if not ok_cap:
        return fail(msg, status=400)
    phone = normalize_phone(data.get('phone'))
    code = (data.get('code') or '').strip()
    if not phone or not code:
        return fail('请输入手机号与验证码')
    user = User.query.filter_by(phone=phone, is_active=True).first()
    if not user:
        record_auth_event(
            'login_failed',
            status='fail',
            subject=phone,
            message='手机号未绑定账号',
            detail={'mode': 'sms_code'},
        )
        return fail('该手机号未绑定系统账号')
    row = LoginSmsCode.query.filter_by(phone=phone).order_by(LoginSmsCode.id.desc()).first()
    if not row or row.expires_at < datetime.now():
        record_auth_event(
            'login_failed',
            status='fail',
            user_id=user.id,
            subject=phone,
            message='验证码已过期',
            detail={'mode': 'sms_code'},
        )
        return fail('验证码已过期，请重新获取')
    if not check_password_hash(row.code_hash, code):
        record_auth_event(
            'login_failed',
            status='fail',
            user_id=user.id,
            subject=phone,
            message='验证码错误',
            detail={'mode': 'sms_code'},
        )
        return fail('验证码错误')
    LoginSmsCode.query.filter_by(phone=phone).delete(synchronize_session=False)
    db.session.commit()
    login_user(user, remember=True)
    record_auth_event(
        'login_success',
        user_id=user.id,
        subject=user.display_label(),
        message='短信验证码登录',
        detail={'mode': 'sms_code'},
    )
    payload = _user_payload(user)
    msg = '登录成功'
    if payload.get('need_set_password'):
        msg = '登录成功，请在右上角头像菜单中设置登录密码'
    return ok(payload, msg)


@auth_api.route('/email-code/send', methods=['POST'])
def send_email_code():
    data = request.get_json(silent=True) or {}
    ok_cap, msg = _verify_login_captcha_optional(data)
    if not ok_cap:
        return fail(msg, status=400)
    email = normalize_email(data.get('email'))
    if not email:
        return fail('请输入邮箱')
    user = User.query.filter(db.func.lower(User.email) == email).first()
    if not user:
        return fail('该邮箱未绑定系统账号')
    last = LoginEmailCode.query.filter_by(email=email).order_by(LoginEmailCode.created_at.desc()).first()
    if last and (datetime.now() - last.created_at) < timedelta(seconds=60):
        return fail('发送过于频繁，请 60 秒后再试')
    LoginEmailCode.query.filter_by(email=email).delete(synchronize_session=False)
    code_plain = f'{secrets.randbelow(1000000):06d}'
    db.session.add(
        LoginEmailCode(
            email=email,
            code_hash=generate_password_hash(code_plain),
            expires_at=datetime.now() + timedelta(minutes=10),
        ),
    )
    db.session.commit()
    ok_send, err = send_login_email_code(current_app, email, code_plain, user_id=user.id)
    record_auth_event(
        'verify_email_sent',
        status='success' if ok_send else 'fail',
        user_id=user.id,
        subject=email,
        message='登录邮箱验证码' if ok_send else err,
    )
    if not ok_send:
        return fail(f'验证码发送失败：{err}')
    return ok(message='验证码已发送至邮箱')


@auth_api.route('/sms-code/send', methods=['POST'])
def send_sms_code():
    data = request.get_json(silent=True) or {}
    ok_cap, msg = verify_login_captcha_payload(data, consume=True)
    if not ok_cap:
        return fail(msg, status=400)
    phone = normalize_phone(data.get('phone'))
    if not phone:
        return fail('请输入手机号')
    user = User.query.filter_by(phone=phone).first()
    if not user:
        return fail('该手机号未绑定系统账号')
    last = LoginSmsCode.query.filter_by(phone=phone).order_by(LoginSmsCode.created_at.desc()).first()
    if last and (datetime.now() - last.created_at) < timedelta(seconds=60):
        return fail('发送过于频繁，请 60 秒后再试')
    LoginSmsCode.query.filter_by(phone=phone).delete(synchronize_session=False)
    code_plain = f'{secrets.randbelow(1000000):06d}'
    db.session.add(
        LoginSmsCode(
            phone=phone,
            code_hash=generate_password_hash(code_plain),
            expires_at=datetime.now() + timedelta(minutes=10),
        ),
    )
    db.session.commit()
    ok_send, err = send_login_sms_code(current_app, phone, code_plain, user_id=user.id)
    record_auth_event(
        'verify_sms_sent',
        status='success' if ok_send else 'fail',
        user_id=user.id,
        subject=phone,
        message='登录短信验证码' if ok_send else err,
    )
    if not ok_send:
        return fail(f'验证码发送失败：{err}')
    return ok(message='验证码已发送至手机')


@auth_api.route('/page-view', methods=['POST'])
@login_required
def record_page_view():
    """前端 SPA 路由切换时上报页面访问（一条记录对应一个页面，非逐条接口）。"""
    data = request.get_json(silent=True) or {}
    path = (data.get('path') or '').strip()
    if not path:
        return fail('缺少页面路径')
    route_name = (data.get('route_name') or '').strip() or None
    title = (data.get('title') or '').strip() or None
    record_page_view_event(
        path=path[:512],
        route_name=route_name[:64] if route_name else None,
        title=title[:128] if title else None,
        user_id=current_user.id,
    )
    return ok(message='已记录')


@auth_api.route('/password', methods=['PUT'])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    new_password = (data.get('new_password') or data.get('password') or '').strip()
    if len(new_password) < 6:
        return fail('新密码至少 6 位')
    has_password = bool(current_user.password_hash)
    if has_password:
        old = data.get('old_password') or ''
        if not old:
            return fail('请输入当前密码')
        if not current_user.check_password(old):
            return fail('当前密码不正确')
    current_user.set_password(new_password)
    db.session.commit()
    return ok(_user_payload(current_user), '密码已更新')


@auth_api.route('/avatar', methods=['POST'])
@login_required
def upload_avatar():
    data = request.get_json(silent=True) or {}
    b64 = data.get('avatar_data') or ''
    if not b64.startswith('data:image'):
        return fail('无效图片数据')
    match = re.match(r'data:image/(png|jpeg|jpg|webp);base64,(.+)', b64, re.I)
    if not match:
        return fail('仅支持 PNG/JPEG/WEBP')
    ext = match.group(1).lower().replace('jpeg', 'jpg')
    raw = base64.b64decode(match.group(2))
    avatar_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', _project_upload_base()), 'avatars')
    os.makedirs(avatar_dir, exist_ok=True)
    fname = f'{current_user.id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.{ext}'
    path = os.path.join(avatar_dir, fname)
    with open(path, 'wb') as f:
        f.write(raw)
    rel = f'uploads/avatars/{fname}'
    current_user.avatar_path = rel
    db.session.commit()
    return ok({'avatar_path': rel, 'avatar_url': f'/api/v1/files/{rel}'}, '头像已更新')


@auth_api.route('/azure/login-url', methods=['GET'])
def azure_login_url():
    tenant = current_app.config.get('AZURE_TENANT_ID')
    client_id = current_app.config.get('AZURE_CLIENT_ID')
    redirect_uri = current_app.config.get('AZURE_REDIRECT_URI')
    if not tenant or not client_id:
        return fail('未配置 Office 365 / Azure AD 登录')
    state = secrets.token_urlsafe(16)
    session['azure_oauth_state'] = state
    params = urllib.parse.urlencode({
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'response_mode': 'query',
        'scope': current_app.config.get('AZURE_SCOPES', 'openid profile email'),
        'state': state,
    })
    url = (
        f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{params}'
    )
    return ok({'url': url})


@auth_api.route('/azure/callback', methods=['GET', 'POST'])
def azure_callback():
    data = request.get_json(silent=True) or request.args
    code = data.get('code')
    state = data.get('state')
    if not code:
        return fail('缺少授权码')
    if state != session.get('azure_oauth_state'):
        return fail('状态校验失败')
    token = _exchange_azure_code(code)
    if not token:
        return fail('无法获取访问令牌')
    profile = _fetch_azure_profile(token)
    if not profile:
        return fail('无法获取用户信息')
    user = _find_or_create_azure_user(profile)
    login_user(user, remember=True)
    record_auth_event(
        'login_success',
        user_id=user.id,
        subject=user.display_label(),
        message='Azure AD 单点登录',
        detail={'mode': 'azure_sso'},
    )
    session.pop('azure_oauth_state', None)
    frontend = current_app.config.get('FRONTEND_URL', 'http://127.0.0.1:5173')
    return redirect(f'{frontend}/auth/azure/callback?azure=ok')


def _exchange_azure_code(code: str) -> str | None:
    import requests

    tenant = current_app.config.get('AZURE_TENANT_ID')
    token_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
    data = {
        'client_id': current_app.config.get('AZURE_CLIENT_ID'),
        'client_secret': current_app.config.get('AZURE_CLIENT_SECRET'),
        'code': code,
        'redirect_uri': current_app.config.get('AZURE_REDIRECT_URI'),
        'grant_type': 'authorization_code',
    }
    resp = requests.post(token_url, data=data, timeout=15)
    if resp.status_code != 200:
        return None
    return resp.json().get('access_token')


def _fetch_azure_profile(token: str) -> dict | None:
    import requests

    resp = requests.get(
        'https://graph.microsoft.com/v1.0/me',
        headers={'Authorization': f'Bearer {token}'},
        timeout=15,
    )
    if resp.status_code != 200:
        return None
    return resp.json()


def _find_or_create_azure_user(profile: dict) -> User:
    email = normalize_email(profile.get('mail') or profile.get('userPrincipalName'))
    oid = profile.get('id')
    name = profile.get('displayName') or email or 'Azure用户'
    user = None
    if oid:
        user = User.query.filter_by(external_id=oid, auth_provider='azure_ad').first()
    if not user and email:
        user = User.query.filter(db.func.lower(User.email) == email).first()
    if not user:
        base = (email or oid or 'azure').split('@')[0][:32]
        username = base
        n = 0
        while User.query.filter_by(username=username).first():
            n += 1
            username = f'{base}{n}'
        user = User(
            username=username,
            display_name=name,
            email=email,
            auth_provider='azure_ad',
            external_id=oid,
        )
        db.session.add(user)
    else:
        user.auth_provider = user.auth_provider or 'azure_ad'
        user.external_id = oid or user.external_id
        if name:
            user.display_name = name
        if email and not user.email:
            user.email = email
    db.session.commit()
    return user


@auth_api.route('/logout', methods=['POST'])
@login_required
def logout():
    uid = current_user.id
    name = current_user.display_label()
    logout_user()
    record_auth_event('logout', user_id=uid, subject=name, message='用户退出登录')
    return ok(message='已退出登录')


@auth_api.route('/me', methods=['GET', 'PATCH'])
@login_required
def me():
    if request.method == 'PATCH':
        data = request.get_json(silent=True) or {}
        if 'display_name' in data:
            current_user.display_name = (data.get('display_name') or '').strip() or current_user.username
        if 'phone' in data:
            current_user.phone = normalize_phone(data.get('phone')) or None
        if 'locale' in data:
            loc = (data.get('locale') or '').strip()
            if loc:
                current_user.locale = loc.replace('_', '-')
        db.session.commit()
        return ok(_user_payload(current_user), '已更新')
    return ok(_user_payload(current_user))


@auth_api.route('/login-methods', methods=['GET'])
def login_methods():
    from app.services.company_branding import get_company_logo_url, get_company_name

    return ok({
        'password': True,
        'email_code': True,
        'sms_code': True,
        'azure_sso': bool(current_app.config.get('AZURE_CLIENT_ID')),
        'company_name': get_company_name(),
        'company_logo_url': get_company_logo_url(),
        'app_name': APP_DISPLAY_NAME,
    })


def _user_payload(user: User) -> dict:
    memberships = []
    for m in user.org_memberships:
        memberships.append({
            'id': m.id,
            'company_id': m.company_id,
            'company_name': m.company.name if m.company else None,
            'department_id': m.department_id,
            'department_name': m.department.name if m.department else None,
            'is_primary': m.is_primary,
            'job_title': m.job_title,
        })
    caps = admin_capabilities(user)
    avatar_url = _avatar_public_url(user)
    avatar_path = _normalize_avatar_path(user.avatar_path)
    return {
        'id': user.id,
        'username': user.username,
        'display_name': user.display_label(),
        'email': user.email,
        'phone': user.phone,
        'job_title': user_display_job_title(user.id),
        'locale': user.locale,
        'is_system_admin': user.is_system_admin,
        'auth_provider': user.auth_provider,
        'memberships': memberships,
        'has_password': bool(user.password_hash),
        'need_set_password': not bool(user.password_hash),
        'avatar_path': avatar_path,
        'avatar_url': avatar_url,
        **caps,
    }
