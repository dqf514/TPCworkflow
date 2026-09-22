# -*- coding: utf-8 -*-
"""发起人视角：申请进度更新与已读状态。"""
from datetime import datetime

from sqlalchemy import func

from app.extensions import db
from app.models import InstanceViewState, WorkflowInstance


def _instance_updated_at(inst: WorkflowInstance) -> datetime | None:
    return inst.updated_at or inst.finished_at or inst.started_at


def get_last_seen_at(user_id: int, instance_id: int) -> datetime | None:
    row = InstanceViewState.query.filter_by(user_id=user_id, instance_id=instance_id).first()
    return row.last_seen_at if row else None


def mark_instance_seen(user_id: int, instance: WorkflowInstance, seen_at: datetime | None = None) -> None:
    """记录用户已查看该实例当前进度（仅更新发起人自己的已读水位）。"""
    if instance.initiator_id != user_id:
        return
    now = seen_at or datetime.now()
    updated = _instance_updated_at(instance) or now
    seen = updated if updated > now else now
    row = InstanceViewState.query.filter_by(user_id=user_id, instance_id=instance.id).first()
    if row:
        if seen > row.last_seen_at:
            row.last_seen_at = seen
    else:
        db.session.add(
            InstanceViewState(
                user_id=user_id,
                instance_id=instance.id,
                last_seen_at=seen,
            ),
        )


def instance_has_unread_progress(inst: WorkflowInstance, user_id: int) -> bool:
    if inst.initiator_id != user_id or inst.status == 'draft':
        return False
    updated = _instance_updated_at(inst)
    if not updated:
        return False
    last_seen = get_last_seen_at(user_id, inst.id)
    baseline = last_seen or inst.started_at or updated
    return updated > baseline


def count_mine_unread_progress(user_id: int) -> int:
    seen_subq = (
        db.session.query(
            InstanceViewState.instance_id.label('instance_id'),
            InstanceViewState.last_seen_at.label('last_seen_at'),
        )
        .filter(InstanceViewState.user_id == user_id)
        .subquery()
    )
    updated_expr = func.coalesce(
        WorkflowInstance.updated_at,
        WorkflowInstance.finished_at,
        WorkflowInstance.started_at,
    )
    baseline_expr = func.coalesce(seen_subq.c.last_seen_at, WorkflowInstance.started_at)
    return (
        WorkflowInstance.query.outerjoin(
            seen_subq,
            seen_subq.c.instance_id == WorkflowInstance.id,
        )
        .filter(
            WorkflowInstance.initiator_id == user_id,
            WorkflowInstance.status != 'draft',
            updated_expr > baseline_expr,
        )
        .count()
    )
