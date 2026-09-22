# -*- coding: utf-8 -*-
"""系统审计：登录、访问、通知落库辅助。"""
from __future__ import annotations

import json

from flask import has_request_context, request
from flask_login import current_user

from app.extensions import db
from app.models import LoginAccessLog

_ACCESS_SKIP_PREFIXES = (
    '/api/v1/health',
    '/api/v1/i18n/messages',
    '/api/v1/auth/captcha',
    '/api/v1/auth/login-methods',
    '/api/v1/auth/page-view',
    '/api/v1/public/',
    '/api/v1/files/',
)


def client_ip() -> str | None:
    if not has_request_context():
        return None
    forwarded = (request.headers.get('X-Forwarded-For') or '').strip()
    if forwarded:
        return forwarded.split(',')[0].strip()[:64]
    return (request.remote_addr or '')[:64] or None


def client_user_agent() -> str | None:
    if not has_request_context():
        return None
    return (request.headers.get('User-Agent') or '')[:512] or None


def _write_log(
    *,
    log_category: str,
    event_type: str,
    status: str = 'success',
    user_id: int | None = None,
    subject: str | None = None,
    message: str | None = None,
    detail: dict | None = None,
    request_method: str | None = None,
    request_path: str | None = None,
    commit: bool = True,
) -> None:
    row = LoginAccessLog(
        log_category=log_category,
        event_type=event_type,
        user_id=user_id,
        subject=(subject or '')[:256] if subject else None,
        ip_address=client_ip(),
        user_agent=client_user_agent(),
        request_method=(request_method or '')[:16] if request_method else None,
        request_path=(request_path or '')[:512] if request_path else None,
        status=status,
        message=(message or '')[:512] if message else None,
        detail_json=json.dumps(detail, ensure_ascii=False) if detail else None,
    )
    db.session.add(row)
    if commit:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


def record_auth_event(
    event_type: str,
    *,
    status: str = 'success',
    user_id: int | None = None,
    subject: str | None = None,
    message: str | None = None,
    detail: dict | None = None,
    commit: bool = True,
) -> None:
    _write_log(
        log_category='auth',
        event_type=event_type,
        status=status,
        user_id=user_id,
        subject=subject,
        message=message,
        detail=detail,
        commit=commit,
    )


def record_page_view_event(
    *,
    path: str,
    route_name: str | None = None,
    title: str | None = None,
    user_id: int | None = None,
    commit: bool = True,
) -> None:
    subject = None
    if user_id and current_user.is_authenticated and current_user.id == user_id:
        subject = current_user.display_label()
    _write_log(
        log_category='access',
        event_type='page_view',
        status='success',
        user_id=user_id,
        subject=subject,
        message=(title or route_name or path or '')[:512],
        detail={'route_name': route_name, 'path': path} if route_name or path else None,
        request_method='PAGE',
        request_path=(path or '')[:512],
        commit=commit,
    )


def record_access_event(
    *,
    request_method: str,
    request_path: str,
    status: str = 'success',
    user_id: int | None = None,
    message: str | None = None,
    detail: dict | None = None,
    commit: bool = True,
) -> None:
    subject = None
    if user_id and current_user.is_authenticated and current_user.id == user_id:
        subject = current_user.display_label()
    _write_log(
        log_category='access',
        event_type='api_access',
        status=status,
        user_id=user_id,
        subject=subject,
        message=message,
        detail=detail,
        request_method=request_method,
        request_path=request_path,
        commit=commit,
    )


def should_log_api_access() -> bool:
    """已改为前端按页面记录访问，不再逐条记录接口请求。"""
    return False


def log_api_access_after_request(status_code: int) -> None:
    if not should_log_api_access():
        return
    if not current_user.is_authenticated:
        return
    status = 'success' if status_code < 400 else 'fail'
    try:
        record_access_event(
            request_method=request.method,
            request_path=request.path,
            status=status,
            user_id=current_user.id,
            message=f'HTTP {status_code}',
            detail={'query': request.query_string.decode('utf-8', errors='ignore')[:200]},
            commit=True,
        )
    except Exception:
        db.session.rollback()
