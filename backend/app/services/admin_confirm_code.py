# -*- coding: utf-8 -*-
"""管理员敏感操作：邮箱验证码发送与校验。"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import AdminEmailConfirmCode, User
from app.utils.user_utils import normalize_email

PURPOSE_DELETE_WORKFLOW_INSTANCE = 'delete_workflow_instance'
_CODE_TTL_MINUTES = 10
_SEND_COOLDOWN_SECONDS = 60


def send_admin_email_confirm_code(user: User, purpose: str) -> tuple[bool, str]:
    email = normalize_email(user.email or '')
    if not email:
        return False, '当前账号未绑定邮箱，无法发送验证码'

    last = (
        AdminEmailConfirmCode.query.filter_by(user_id=user.id, purpose=purpose)
        .order_by(AdminEmailConfirmCode.created_at.desc())
        .first()
    )
    if last and (datetime.now() - last.created_at) < timedelta(seconds=_SEND_COOLDOWN_SECONDS):
        return False, '发送过于频繁，请 60 秒后再试'

    AdminEmailConfirmCode.query.filter_by(user_id=user.id, purpose=purpose).delete(
        synchronize_session=False,
    )
    code_plain = f'{secrets.randbelow(1000000):06d}'
    db.session.add(
        AdminEmailConfirmCode(
            user_id=user.id,
            purpose=purpose,
            code_hash=generate_password_hash(code_plain),
            expires_at=datetime.now() + timedelta(minutes=_CODE_TTL_MINUTES),
        ),
    )
    db.session.commit()

    from app.services.notify import send_admin_confirm_email_code

    app = current_app._get_current_object()
    ok, err = send_admin_confirm_email_code(
        app,
        email,
        purpose,
        code_plain,
        user_id=user.id,
        operator_name=user.display_label(),
    )
    if not ok:
        return False, f'验证码发送失败：{err}'
    return True, '验证码已发送至您的邮箱'


def verify_admin_email_confirm_code(user: User, purpose: str, code: str) -> tuple[bool, str]:
    code = (code or '').strip()
    if not code:
        return False, '请输入邮箱验证码'

    row = (
        AdminEmailConfirmCode.query.filter_by(user_id=user.id, purpose=purpose)
        .order_by(AdminEmailConfirmCode.created_at.desc())
        .first()
    )
    if not row or row.expires_at < datetime.now():
        return False, '验证码已过期，请重新获取'
    if not check_password_hash(row.code_hash, code):
        return False, '验证码错误'

    AdminEmailConfirmCode.query.filter_by(user_id=user.id, purpose=purpose).delete(
        synchronize_session=False,
    )
    db.session.commit()
    return True, ''
