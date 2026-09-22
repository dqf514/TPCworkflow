# -*- coding: utf-8 -*-
"""待办/已办任务列表：查询、排序与行数据。"""
from __future__ import annotations

import json

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Query

from app.models import (
    BusinessSector,
    Department,
    TaskInstance,
    User,
    WorkflowDefinition,
    WorkflowInstance,
)
from app.services.graph_utils import find_node, parse_graph, parse_variables, resolve_node_display_name
from app.services.instance_list_meta import enrich_instance_list_row
from app.services.workflow_settings import merge_settings
from app.services.workflow_add_sign import is_add_sign_task

_DONE_STATUSES = ('approved', 'rejected', 'reject', 'transfer', 'completed', 'cancelled')

_TASK_SORTABLE_FIELDS = {
    'display_no': WorkflowInstance.display_no,
    'definition_name': WorkflowDefinition.name,
    'initiator_name': User.display_name,
    'department_name': Department.name,
    'business_sector_name': BusinessSector.name,
    'started_at': WorkflowInstance.started_at,
    'task_created_at': TaskInstance.created_at,
    'completed_at': TaskInstance.completed_at,
    'task_status': TaskInstance.status,
    'node_name': TaskInstance.node_id,
}


def _parse_task_meta(raw) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw) if isinstance(raw, str) else (raw or {})
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _task_field_requirement_errors(task: TaskInstance, node: dict | None = None) -> list[str]:
    """当前表单相对节点「本节点必填 / 须修改」的校验错误。"""
    inst = task.instance
    if not inst or not inst.definition:
        return []
    if node is None:
        graph = parse_graph(inst.definition.process_graph)
        node = find_node(graph, task.node_id) or {}
    node_config = (node.get('config') or {}) if node else {}
    from app.services.node_field_requirements import node_has_field_requirements, validate_node_field_requirements

    if not node_has_field_requirements(node_config):
        return []
    from app.services.form_schema import resolve_definition_schema

    schema = resolve_definition_schema(inst.definition)
    form_data = dict(parse_variables(inst.variables).get('form') or {})
    return validate_node_field_requirements(
        schema,
        form_data,
        node_config,
        original_form=form_data,
    )


def task_can_quick_approve(
    task: TaskInstance,
    settings: dict | None = None,
    node: dict | None = None,
    *,
    field_errors: list[str] | None = None,
) -> bool:
    """是否可在列表中一键同意（无需打开详情填表/签名）。"""
    if task.status != 'pending':
        return False
    meta = _parse_task_meta(task.action_meta)
    if is_add_sign_task(meta):
        return False
    inst = task.instance
    if not inst or not inst.definition:
        return False
    settings = settings if settings is not None else merge_settings(inst.definition.settings)
    if settings.get('require_handwritten_sign'):
        return False
    if node is None:
        graph = parse_graph(inst.definition.process_graph)
        node = find_node(graph, task.node_id) or {}
    node_config = (node.get('config') or {}) if node else {}
    perms = node_config.get('field_permissions') or {}

    if field_errors is None:
        field_errors = _task_field_requirement_errors(task, node)
    if field_errors:
        return False

    from app.services.node_field_requirements import node_has_field_requirements

    if node_has_field_requirements(node_config):
        return True
    if any(v == 'edit' for v in perms.values()):
        return False
    return True


def query_user_tasks(
    user_id: int,
    *,
    mode: str = 'todo',
    task_status: str | None = None,
    sector_id: int | None = None,
    keyword: str | None = None,
    sort_field: str | None = None,
    sort_order: str | None = None,
) -> Query:
    q = (
        TaskInstance.query.join(
            WorkflowInstance,
            TaskInstance.instance_id == WorkflowInstance.id,
        )
        .filter(TaskInstance.assignee_id == user_id)
    )
    if mode == 'todo':
        q = q.filter(TaskInstance.status == 'pending')
    else:
        q = q.filter(TaskInstance.status.in_(_DONE_STATUSES))
        ts = (task_status or '').strip()
        if ts:
            if ts == 'rejected':
                q = q.filter(TaskInstance.status.in_(('rejected', 'reject')))
            else:
                q = q.filter(TaskInstance.status == ts)
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
            clauses.append(TaskInstance.id == int(kw))
        q = q.filter(or_(*clauses))
    return apply_task_list_sort(
        q,
        sort_field=sort_field,
        sort_order=sort_order,
        default_field='task_created_at' if mode == 'todo' else 'completed_at',
    ).distinct()


def apply_task_list_sort(
    q: Query,
    *,
    sort_field: str | None = None,
    sort_order: str | None = None,
    default_field: str = 'task_created_at',
) -> Query:
    field_key = (sort_field or '').strip() or default_field
    if field_key not in _TASK_SORTABLE_FIELDS:
        field_key = default_field
    direction = desc if (sort_order or 'desc').lower() != 'asc' else asc
    col = _TASK_SORTABLE_FIELDS[field_key]

    if field_key == 'definition_name':
        q = q.outerjoin(
            WorkflowDefinition,
            WorkflowInstance.definition_id == WorkflowDefinition.id,
        )
    elif field_key == 'initiator_name':
        q = q.outerjoin(User, WorkflowInstance.initiator_id == User.id)
    elif field_key == 'department_name':
        q = q.outerjoin(Department, WorkflowInstance.department_id == Department.id)
    elif field_key == 'business_sector_name':
        q = q.outerjoin(
            BusinessSector,
            WorkflowInstance.business_sector_id == BusinessSector.id,
        )

    if field_key == 'display_no':
        return q.order_by(direction(col), direction(TaskInstance.id))
    return q.order_by(direction(col), direction(TaskInstance.id))


def task_list_row(task: TaskInstance) -> dict:
    from app.models import BusinessSector, Department, User
    from app.services.instance_access import ensure_instance_public_uuid
    from app.services.instance_list_meta import enrich_instance_list_row
    from app.utils.datetime_fmt import format_display_datetime

    inst = task.instance
    if not inst:
        return {
            'task_id': task.id,
            'id': task.id,
            'node_id': task.node_id,
            'node_type': task.node_type,
            'task_status': task.status,
        }

    graph = parse_graph(inst.definition.process_graph) if inst.definition else {'nodes': [], 'edges': []}
    node = find_node(graph, task.node_id) or {}
    node_name = resolve_node_display_name(node, task.node_id)
    settings = merge_settings(inst.definition.settings) if inst.definition else {}
    field_errors = _task_field_requirement_errors(task, node)

    initiator = User.query.get(inst.initiator_id) if inst.initiator_id else None
    dept = Department.query.get(inst.department_id) if inst.department_id else None
    sector_name = ''
    if inst.business_sector_id:
        sector = BusinessSector.query.get(inst.business_sector_id)
        sector_name = sector.name if sector else ''
    updated = getattr(inst, 'updated_at', None) or inst.finished_at or inst.started_at

    row = {
        'id': inst.id,
        'public_uuid': ensure_instance_public_uuid(inst),
        'display_no': inst.display_no or str(inst.id),
        'definition_name': inst.definition.name if inst.definition else None,
        'business_sector_name': sector_name,
        'status': inst.status,
        'initiator_name': initiator.display_label() if initiator else '',
        'department_name': dept.name if dept else '',
        'started_at': format_display_datetime(inst.started_at),
        'updated_at': format_display_datetime(updated),
        'finished_at': format_display_datetime(inst.finished_at),
        'task_id': task.id,
        'instance_id': inst.id,
        'node_id': task.node_id,
        'node_name': node_name,
        'node_type': task.node_type,
        'task_status': task.status,
        'task_created_at': format_display_datetime(task.created_at),
        'task_completed_at': format_display_datetime(task.completed_at),
        'is_handler': task.node_type == 'handler',
        'field_requirement_errors': field_errors,
        'can_quick_approve': task_can_quick_approve(task, settings, node, field_errors=field_errors),
        'can_reject': task.status == 'pending' and task.node_type != 'handler',
    }
    return enrich_instance_list_row(inst, row)
