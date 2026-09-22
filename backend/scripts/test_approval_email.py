# -*- coding: utf-8 -*-
"""验证审批邮件：摘要生成、令牌、模拟发送（需配置 SMTP）。"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from app.extensions import db
from app.models import SystemSetting, TaskInstance
from app.services.approval_token import create_task_email_token, get_valid_token
from app.services.email_content import build_approval_email
from app.services.notify import get_mail_config, notify_approval_task_email
from scripts.upgrade_db import _ensure_columns


def main() -> int:
    app = create_app()
    with app.app_context():
        _ensure_columns()
        task = (
            TaskInstance.query.filter_by(status='pending')
            .order_by(TaskInstance.id.desc())
            .first()
        )
        if not task:
            print('无待办任务，请先发起流程并产生 pending 任务后再运行本脚本')
            return 1

        base_row = SystemSetting.query.get('PUBLIC_BASE_URL')
        public_base = (base_row.value if base_row and base_row.value else '') or app.config.get(
            'PUBLIC_BASE_URL', 'http://127.0.0.1:5173',
        )
        subject, text, html = build_approval_email(task, public_base_url=str(public_base))
        print('=== 邮件主题 ===')
        print(subject)
        print('\n=== 纯文本摘要（前 1200 字）===')
        print(text[:1200])
        print('\n=== 快速审批令牌 ===')
        tok = create_task_email_token(task, 'approve')
        db.session.commit()
        print('approve token:', tok)
        print('valid:', bool(get_valid_token(tok)))

        mail = get_mail_config(app)
        if not mail.get('MAIL_SERVER'):
            print('\n未配置 SMTP，跳过实际发送。请在系统设置中配置邮件后重试。')
            return 0

        from app.models import User

        assignee = User.query.get(task.assignee_id)
        if not assignee or not assignee.email:
            print('\n审批人未配置邮箱，无法发送。')
            return 1

        ok, err = notify_approval_task_email(app, task.id)
        print(f'\n发送结果: ok={ok} err={err or "无"}')
        return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
