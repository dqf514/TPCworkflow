# -*- coding: utf-8 -*-
"""客户端 Bearer 认证：与 Flask-Login Session 并存，Session 优先。"""
from __future__ import annotations

from functools import wraps

from flask import request
from flask_login import current_user, login_user

from app.services.device_auth import resolve_user_by_access_token


def _bearer_token() -> str | None:
    auth = (request.headers.get('Authorization') or '').strip()
    if not auth.lower().startswith('bearer '):
        return None
    token = auth[7:].strip()
    return token or None


def resolve_request_user():
    """返回当前请求用户：已登录 Session 或 Bearer 设备令牌。"""
    if current_user.is_authenticated:
        return current_user
    token = _bearer_token()
    if not token:
        return None
    return resolve_user_by_access_token(token)


def client_auth_required(fn):
    """要求 Session 或设备 Bearer 令牌。"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = resolve_request_user()
        if not user:
            from app.utils.response import fail

            return fail('未登录或令牌无效', status=401, code='unauthorized')
        if not current_user.is_authenticated:
            login_user(user, remember=False)
        return fn(*args, **kwargs)

    return wrapper
