# -*- coding: utf-8 -*-
"""流程实例对外标识与查看权限。"""
from __future__ import annotations

import re
import uuid

from sqlalchemy import and_, exists

from app.extensions import db
from app.models import InstanceTimeline, TaskInstance, WorkflowInstance

# 用户已处理过的任务状态
PARTICIPATED_TASK_STATUSES = ('approved', 'rejected', 'reject', 'transfer', 'completed')
# 「与我相关的审批」列表：含待办、前加签挂起、已处理，及或签被他人处理后取消的待办
RELATED_APPROVAL_TASK_STATUSES = PARTICIPATED_TASK_STATUSES + ('pending', 'on_hold', 'cancelled')
from app.services.permissions import is_global_admin, user_can_view_sector_instances

UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.I,
)


def is_valid_public_uuid(value: str | None) -> bool:
    return bool(value and UUID_RE.match(str(value).strip()))


def ensure_instance_public_uuid(inst: WorkflowInstance) -> str:
    if inst.public_uuid and is_valid_public_uuid(inst.public_uuid):
        return inst.public_uuid
    inst.public_uuid = str(uuid.uuid4())
    db.session.flush()
    return inst.public_uuid


def resolve_instance_by_public_uuid(ref: str | None) -> WorkflowInstance | None:
    if not is_valid_public_uuid(ref):
        return None
    return WorkflowInstance.query.filter_by(public_uuid=str(ref).strip()).first()


def user_participated_in_instance(user_id: int, instance_id: int) -> bool:
    """用户在该实例上已有完成的审批/办理任务（流程曾到达本人节点且已处理）。"""
    return (
        TaskInstance.query.filter(
            TaskInstance.instance_id == instance_id,
            TaskInstance.assignee_id == user_id,
            TaskInstance.status.in_(PARTICIPATED_TASK_STATUSES),
        )
        .limit(1)
        .first()
        is not None
    )


def participated_instances_filter(user_id: int):
    """非本人发起，且本人有待办、已处理或或签取消的节点任务。"""
    involved = exists().where(
        and_(
            TaskInstance.instance_id == WorkflowInstance.id,
            TaskInstance.assignee_id == user_id,
            TaskInstance.status.in_(RELATED_APPROVAL_TASK_STATUSES),
        ),
    )
    return and_(WorkflowInstance.initiator_id != user_id, involved)


def user_can_view_instance(user, inst: WorkflowInstance | None) -> bool:
    if not user or not inst:
        return False
    if is_global_admin(user):
        return True
    if inst.initiator_id == user.id:
        return True
    if (
        TaskInstance.query.filter_by(instance_id=inst.id, assignee_id=user.id)
        .limit(1)
        .first()
    ):
        return True
    if (
        InstanceTimeline.query.filter_by(instance_id=inst.id, actor_id=user.id)
        .limit(1)
        .first()
    ):
        return True
    if inst.business_sector_id and user_can_view_sector_instances(user, inst.business_sector_id):
        return True
    return False
