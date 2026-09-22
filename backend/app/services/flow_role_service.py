# -*- coding: utf-8 -*-
"""流程角色与成员维护。"""
from __future__ import annotations

from app.extensions import db
from app.models import FlowRole, FlowRoleMember, User
from app.services.assignee_resolver import is_dept_manager_flow_role


def flow_role_dict(role: FlowRole, *, member_count: int | None = None) -> dict:
    cnt = member_count
    if cnt is None:
        cnt = FlowRoleMember.query.filter_by(flow_role_id=role.id).count()
    return {
        'id': role.id,
        'code': role.code,
        'name': role.name,
        'description': role.description,
        'is_active': role.is_active,
        'member_count': cnt,
        'is_dept_manager_role': is_dept_manager_flow_role(role.code),
    }


def flow_role_member_dict(m: FlowRoleMember) -> dict:
    u = User.query.get(m.user_id)
    return {
        'id': m.id,
        'user_id': m.user_id,
        'username': u.username if u else None,
        'display_name': u.display_label() if u else None,
        'email': u.email if u else None,
        'is_active': bool(u.is_active) if u else False,
        'company_id': m.company_id,
        'department_id': m.department_id,
    }


def find_global_member(role_id: int, user_id: int) -> FlowRoleMember | None:
    return FlowRoleMember.query.filter_by(
        flow_role_id=role_id,
        user_id=user_id,
        company_id=None,
        department_id=None,
    ).first()


def add_flow_role_member(role_id: int, user_id: int) -> tuple[FlowRoleMember | None, str | None]:
    role = FlowRole.query.get(role_id)
    if not role or not role.is_active:
        return None, '流程角色不存在或已停用'
    user = User.query.get(user_id)
    if not user:
        return None, '用户不存在'
    if not user.is_active:
        return None, '该用户已停用，无法加入流程角色'
    if find_global_member(role_id, user_id):
        return None, '该用户已在角色成员列表中'
    m = FlowRoleMember(
        flow_role_id=role_id,
        user_id=user_id,
        company_id=None,
        department_id=None,
    )
    db.session.add(m)
    db.session.flush()
    return m, None


def set_flow_role_members(role_id: int, user_ids: list[int]) -> tuple[list[dict], str | None]:
    role = FlowRole.query.get(role_id)
    if not role:
        return [], '流程角色不存在'
    cleaned: list[int] = []
    seen: set[int] = set()
    for raw in user_ids:
        try:
            uid = int(raw)
        except (TypeError, ValueError):
            continue
        if uid <= 0 or uid in seen:
            continue
        seen.add(uid)
        cleaned.append(uid)
    for uid in cleaned:
        u = User.query.get(uid)
        if not u or not u.is_active:
            return [], f'用户 #{uid} 不存在或已停用'
    existing = FlowRoleMember.query.filter_by(
        flow_role_id=role_id,
        company_id=None,
        department_id=None,
    ).all()
    existing_by_user = {m.user_id: m for m in existing}
    for uid in cleaned:
        if uid not in existing_by_user:
            db.session.add(
                FlowRoleMember(
                    flow_role_id=role_id,
                    user_id=uid,
                    company_id=None,
                    department_id=None,
                ),
            )
    for uid, row in existing_by_user.items():
        if uid not in seen:
            db.session.delete(row)
    db.session.flush()
    rows = FlowRoleMember.query.filter_by(
        flow_role_id=role_id,
        company_id=None,
        department_id=None,
    ).all()
    return [flow_role_member_dict(m) for m in rows], None


def list_user_flow_role_ids(user_id: int) -> list[int]:
    rows = FlowRoleMember.query.filter_by(
        user_id=user_id,
        company_id=None,
        department_id=None,
    ).all()
    return [m.flow_role_id for m in rows]


def set_user_flow_roles(user_id: int, role_ids: list[int]) -> tuple[list[dict], str | None]:
    user = User.query.get(user_id)
    if not user:
        return [], '用户不存在'
    cleaned: list[int] = []
    seen: set[int] = set()
    for raw in role_ids:
        try:
            rid = int(raw)
        except (TypeError, ValueError):
            continue
        if rid <= 0 or rid in seen:
            continue
        role = FlowRole.query.get(rid)
        if not role or not role.is_active:
            return [], f'流程角色 #{rid} 不存在或已停用'
        seen.add(rid)
        cleaned.append(rid)
    existing = FlowRoleMember.query.filter_by(
        user_id=user_id,
        company_id=None,
        department_id=None,
    ).all()
    existing_by_role = {m.flow_role_id: m for m in existing}
    for rid in cleaned:
        if rid not in existing_by_role:
            db.session.add(
                FlowRoleMember(
                    flow_role_id=rid,
                    user_id=user_id,
                    company_id=None,
                    department_id=None,
                ),
            )
    for rid, row in existing_by_role.items():
        if rid not in seen:
            db.session.delete(row)
    db.session.flush()
    roles = (
        FlowRole.query.filter(FlowRole.id.in_(cleaned)).order_by(FlowRole.code).all()
        if cleaned
        else []
    )
    return [flow_role_dict(r) for r in roles], None
