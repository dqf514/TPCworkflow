# -*- coding: utf-8 -*-
"""任务创建：异常处理、自动审批。"""
import json
from datetime import datetime

from app.extensions import db
from app.models import InstanceTimeline, TaskInstance, User
from app.services.assignee_resolver import (
    AssigneeResolver,
    apply_dept_manager_skip_policy,
    is_dept_manager_assignee_config,
)


def system_admin_user_ids() -> list[int]:
    return [u.id for u in User.query.filter_by(is_system_admin=True, is_active=True).all()]


def filter_active_assignees(user_ids: list[int]) -> tuple[list[int], list[int]]:
    """返回 (在职用户, 已离职用户)。"""
    active, resigned = [], []
    for uid in user_ids:
        u = User.query.get(uid)
        if u and u.is_active:
            active.append(uid)
        elif u:
            resigned.append(uid)
    return active, resigned


def resolve_assignees_for_node(
    inst,
    config: dict,
    settings: dict,
    node_type: str,
) -> tuple[list[int], bool, str | None]:
    """
    解析审批人列表。
    返回 (user_ids, auto_skip_node, skip_reason)。
    auto_skip_node=True 表示无需创建任务（自动通过）。
    """
    resolver = AssigneeResolver(inst)
    raw_ids = resolver.resolve(config)
    active, resigned = filter_active_assignees(raw_ids)

    prefix = 'approver' if node_type == 'approver' else 'handler'
    dept_mgr_node = is_dept_manager_assignee_config(config)

    if resigned:
        action = settings.get(f'{prefix}_resigned_action', 'auto_transfer')
        if action == 'auto_transfer':
            tid = settings.get(f'{prefix}_resigned_transfer_user_id')
            if tid:
                tu = User.query.get(int(tid))
                if tu and tu.is_active:
                    return [int(tid)], False, None
        if action == 'admin_handover':
            admins = system_admin_user_ids()
            if admins:
                return admins[:1], False, None

    if active:
        if dept_mgr_node:
            assignees, skip, reason = apply_dept_manager_skip_policy(inst, active)
            if skip:
                return [], True, reason
            return assignees, False, None
        return active, False, None

    if dept_mgr_node:
        assignees, skip, reason = apply_dept_manager_skip_policy(inst, [])
        if skip:
            return [], True, reason

    action = settings.get(f'{prefix}_empty_action', 'auto_approve')
    if action == 'transfer':
        tid = settings.get(f'{prefix}_empty_transfer_user_id')
        if tid:
            tu = User.query.get(int(tid))
            if tu and tu.is_active:
                return [int(tid)], False, None
    if action == 'admin_handover':
        admins = system_admin_user_ids()
        if admins:
            return admins[:1], False, None
    if action == 'auto_approve':
        return [], True, '审批人为空，已按设置自动同意'
    return [], True, '审批人为空，已按设置自动同意'


def should_auto_approve_duplicate(inst, settings: dict, user_id: int) -> bool:
    mode = settings.get('duplicate_approver_mode', 'every_node')
    if mode == 'every_node':
        return False
    approved = (
        inst.tasks.filter_by(assignee_id=user_id, status='approved')
        .order_by(TaskInstance.completed_at.asc())
        .all()
    )
    if not approved:
        return False
    if mode == 'first_only':
        return True
    if mode == 'consecutive_only':
        last = (
            inst.tasks.filter_by(status='approved')
            .order_by(TaskInstance.completed_at.desc())
            .first()
        )
        return last is not None and last.assignee_id == user_id
    return False


def append_auto_approve_timeline(inst_id: int, node_id: str, reason: str) -> None:
    db.session.add(
        InstanceTimeline(
            instance_id=inst_id,
            actor_id=None,
            action='auto_approve',
            node_id=node_id,
            comment=reason,
        ),
    )


def create_auto_approved_task(inst, node_id: str, node_type: str, user_id: int, reason: str) -> None:
    """记录已自动同意的节点（便于审计）。"""
    t = TaskInstance(
        instance_id=inst.id,
        node_id=node_id,
        node_type=node_type,
        assignee_id=user_id,
        status='approved',
        completed_at=datetime.now(),
        action_meta=json.dumps({'auto_approve': True, 'reason': reason}, ensure_ascii=False),
    )
    db.session.add(t)
    append_auto_approve_timeline(inst.id, node_id, reason)
