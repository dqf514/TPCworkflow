# -*- coding: utf-8 -*-
"""全局管理员与分级管理员权限。"""
from __future__ import annotations

import json

from app.models import User, UserScopedAdmin


def is_global_admin(user: User | None) -> bool:
    return bool(user and user.is_system_admin)


def _parse_sector_ids(raw: str | None) -> list[int]:
    try:
        ids = json.loads(raw or '[]')
        return [int(x) for x in ids if x is not None]
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def get_scoped_admin(user: User | None) -> UserScopedAdmin | None:
    if not user:
        return None
    return UserScopedAdmin.query.filter_by(user_id=user.id).first()


def get_user_sector_ids(user: User | None) -> list[int]:
    if is_global_admin(user):
        return []
    row = get_scoped_admin(user)
    if not row:
        return []
    return _parse_sector_ids(row.sector_ids)


def is_sector_admin(user: User | None) -> bool:
    if is_global_admin(user):
        return False
    return bool(get_user_sector_ids(user))


def user_can_access_sector(user: User | None, sector_id: int | None) -> bool:
    if not sector_id:
        return is_global_admin(user)
    if is_global_admin(user):
        return True
    return sector_id in get_user_sector_ids(user)


def user_can_design_sector(user: User | None, sector_id: int | None) -> bool:
    if is_global_admin(user):
        return True
    row = get_scoped_admin(user)
    if not row or not row.can_design_workflow:
        return False
    return sector_id in _parse_sector_ids(row.sector_ids) if sector_id else False


def user_can_view_sector_instances(user: User | None, sector_id: int | None) -> bool:
    if is_global_admin(user):
        return True
    row = get_scoped_admin(user)
    if not row or not row.can_view_instances:
        return False
    return sector_id in _parse_sector_ids(row.sector_ids) if sector_id else False


def user_can_export_sector(user: User | None, sector_id: int | None) -> bool:
    if is_global_admin(user):
        return True
    row = get_scoped_admin(user)
    if not row or not row.can_export_instances:
        return False
    return sector_id in _parse_sector_ids(row.sector_ids) if sector_id else False


def admin_capabilities(user: User | None) -> dict:
    row = get_scoped_admin(user)
    return {
        'is_global_admin': is_global_admin(user),
        'is_sector_admin': is_sector_admin(user),
        'sector_ids': get_user_sector_ids(user),
        'can_design_workflow': is_global_admin(user) or bool(row and row.can_design_workflow),
        'can_view_instances': is_global_admin(user) or bool(row and row.can_view_instances),
        'can_export_instances': is_global_admin(user) or bool(row and row.can_export_instances),
    }
