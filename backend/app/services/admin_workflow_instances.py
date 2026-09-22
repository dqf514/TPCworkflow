# -*- coding: utf-8 -*-
"""系统管理员：审批单列表与物理删除。"""
from sqlalchemy import or_

from app.extensions import db
from app.models import (
    InstanceTimeline,
    NotificationLog,
    TaskEmailToken,
    TaskInstance,
    User,
    WorkflowDefinition,
    WorkflowInstance,
)
from app.services.instance_access import ensure_instance_public_uuid, resolve_instance_by_public_uuid


def resolve_admin_instance_ref(ref: str) -> WorkflowInstance | None:
    ref = (ref or '').strip()
    if not ref:
        return None
    inst = resolve_instance_by_public_uuid(ref)
    if inst:
        return inst
    if ref.isdigit():
        return WorkflowInstance.query.get(int(ref))
    return None


def purge_workflow_instance(inst: WorkflowInstance) -> None:
    """删除审批单及关联待办、邮件令牌、时间线、通知日志。"""
    task_ids = [t.id for t in TaskInstance.query.filter_by(instance_id=inst.id).all()]
    if task_ids:
        TaskEmailToken.query.filter(TaskEmailToken.task_id.in_(task_ids)).delete(
            synchronize_session=False
        )
    TaskInstance.query.filter_by(instance_id=inst.id).delete(synchronize_session=False)
    InstanceTimeline.query.filter_by(instance_id=inst.id).delete(synchronize_session=False)
    NotificationLog.query.filter_by(instance_id=inst.id).delete(synchronize_session=False)
    db.session.delete(inst)


def query_admin_workflow_instances(
    *,
    status: str | None = None,
    sector_id: int | None = None,
    keyword: str | None = None,
    sort_field: str | None = None,
    sort_order: str | None = None,
):
    from app.services.instance_list_meta import apply_instance_list_sort

    q = WorkflowInstance.query
    if status:
        q = q.filter(WorkflowInstance.status == status)
    if sector_id:
        q = q.filter(WorkflowInstance.business_sector_id == sector_id)
    kw = (keyword or '').strip()
    if kw:
        like = f'%{kw}%'
        q = q.outerjoin(
            WorkflowDefinition,
            WorkflowInstance.definition_id == WorkflowDefinition.id,
        ).outerjoin(User, WorkflowInstance.initiator_id == User.id)
        clauses = [
            WorkflowInstance.display_no.ilike(like),
            WorkflowDefinition.name.ilike(like),
            User.display_name.ilike(like),
            User.username.ilike(like),
        ]
        if kw.isdigit():
            clauses.append(WorkflowInstance.id == int(kw))
        q = q.filter(or_(*clauses))
    return apply_instance_list_sort(q, sort_field=sort_field, sort_order=sort_order).distinct()


def admin_instance_row(inst: WorkflowInstance) -> dict:
    from app.api.workflow import _instance_row

    d = _instance_row(inst)
    d['display_no'] = inst.display_no or str(inst.id)
    ensure_instance_public_uuid(inst)
    return d
