# -*- coding: utf-8 -*-
"""客户端设备令牌：签发、校验、刷新。"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User, UserDevice

ACCESS_TOKEN_TTL_HOURS = 24
REFRESH_TOKEN_TTL_DAYS = 90


def _issue_token() -> str:
    return secrets.token_urlsafe(48)


def _hash_token(token: str) -> str:
    return generate_password_hash(token)


def _verify_token(token: str, token_hash: str) -> bool:
    return check_password_hash(token_hash, token)


def register_device(
    user: User,
    *,
    device_uid: str,
    device_name: str | None = None,
) -> dict:
    uid = (device_uid or '').strip()
    if not uid:
        raise ValueError('设备标识不能为空')
    name = (device_name or '').strip() or 'Windows 客户端'
    now = datetime.now()
    access_token = _issue_token()
    refresh_token = _issue_token()
    row = UserDevice.query.filter_by(user_id=user.id, device_uid=uid).first()
    if not row:
        row = UserDevice(user_id=user.id, device_uid=uid)
        db.session.add(row)
    row.device_name = name
    row.access_token_hash = _hash_token(access_token)
    row.refresh_token_hash = _hash_token(refresh_token)
    row.access_expires_at = now + timedelta(hours=ACCESS_TOKEN_TTL_HOURS)
    row.refresh_expires_at = now + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
    row.last_used_at = now
    row.revoked_at = None
    db.session.commit()
    return {
        'device_id': row.id,
        'device_uid': row.device_uid,
        'device_name': row.device_name,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'access_expires_at': row.access_expires_at.isoformat(timespec='seconds'),
        'refresh_expires_at': row.refresh_expires_at.isoformat(timespec='seconds'),
    }


def refresh_device_tokens(*, device_uid: str, refresh_token: str) -> dict | None:
    uid = (device_uid or '').strip()
    token = (refresh_token or '').strip()
    if not uid or not token:
        return None
    row = UserDevice.query.filter_by(device_uid=uid, revoked_at=None).first()
    if not row or row.refresh_expires_at < datetime.now():
        return None
    if not _verify_token(token, row.refresh_token_hash):
        return None
    user = User.query.get(row.user_id)
    if not user or not user.is_active:
        return None
    now = datetime.now()
    access_token = _issue_token()
    new_refresh = _issue_token()
    row.access_token_hash = _hash_token(access_token)
    row.refresh_token_hash = _hash_token(new_refresh)
    row.access_expires_at = now + timedelta(hours=ACCESS_TOKEN_TTL_HOURS)
    row.refresh_expires_at = now + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
    row.last_used_at = now
    db.session.commit()
    return {
        'device_id': row.id,
        'device_uid': row.device_uid,
        'device_name': row.device_name,
        'access_token': access_token,
        'refresh_token': new_refresh,
        'access_expires_at': row.access_expires_at.isoformat(timespec='seconds'),
        'refresh_expires_at': row.refresh_expires_at.isoformat(timespec='seconds'),
        'user_id': user.id,
    }


def resolve_user_by_access_token(access_token: str) -> User | None:
    token = (access_token or '').strip()
    if not token:
        return None
    now = datetime.now()
    rows = (
        UserDevice.query.filter(
            UserDevice.revoked_at.is_(None),
            UserDevice.access_expires_at >= now,
        )
        .order_by(UserDevice.last_used_at.desc().nullslast(), UserDevice.id.desc())
        .limit(200)
        .all()
    )
    for row in rows:
        if _verify_token(token, row.access_token_hash):
            user = User.query.get(row.user_id)
            if user and user.is_active:
                row.last_used_at = now
                db.session.commit()
                return user
    return None


def list_user_devices(user_id: int) -> list[dict]:
    rows = (
        UserDevice.query.filter_by(user_id=user_id, revoked_at=None)
        .order_by(UserDevice.last_used_at.desc().nullslast(), UserDevice.id.desc())
        .all()
    )
    return [
        {
            'id': r.id,
            'device_uid': r.device_uid,
            'device_name': r.device_name,
            'last_used_at': r.last_used_at.isoformat(timespec='seconds') if r.last_used_at else None,
            'created_at': r.created_at.isoformat(timespec='seconds') if r.created_at else None,
            'access_expires_at': r.access_expires_at.isoformat(timespec='seconds'),
            'refresh_expires_at': r.refresh_expires_at.isoformat(timespec='seconds'),
        }
        for r in rows
        if r.is_active
    ]


def revoke_device(user: User, device_id: int) -> bool:
    row = UserDevice.query.filter_by(id=device_id, user_id=user.id, revoked_at=None).first()
    if not row:
        return False
    row.revoked_at = datetime.now()
    db.session.commit()
    return True
