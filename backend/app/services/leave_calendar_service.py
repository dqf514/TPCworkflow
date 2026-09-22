# -*- coding: utf-8 -*-
"""公共日历：聚合「同步到日历」的日期字段（含请假等兼容逻辑）。"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, exists, or_
from sqlalchemy.orm import joinedload

from app.models import Department, InstanceTimeline, TaskInstance, User, WorkflowDefinition, WorkflowInstance
from app.services.form_schema import parse_schema, resolve_definition_schema
from app.services.graph_utils import parse_variables
from app.services.instance_access import RELATED_APPROVAL_TASK_STATUSES, ensure_instance_public_uuid
from app.services.permissions import (
    admin_capabilities,
    get_user_sector_ids,
    is_global_admin,
)

DEFAULT_FORM_KEYS = ('auto',)
DEFAULT_PERIOD_KEYS = ('leave_period', 'date_range')
DEFAULT_LEAVE_TYPE_KEY = 'leave_type'
DEFAULT_STATUSES = ('approved',)

# 按流程主题稳定上色（循环使用）
CALENDAR_PALETTE = (
    '#0f9d58',  # 绿
    '#3b82f6',  # 蓝
    '#f59e0b',  # 橙
    '#8b5cf6',  # 紫
    '#ec4899',  # 粉
    '#14b8a6',  # 青
    '#ef4444',  # 红
    '#64748b',  # 灰蓝
    '#06b6d4',  # 天蓝
    '#84cc16',  # 黄绿
)

LEAVE_TYPE_COLORS = {
    'annual': '#0f9d58',
    'personal': '#3b82f6',
    'sick': '#f59e0b',
    'comp_off': '#8b5cf6',
    'marriage': '#ec4899',
    'maternity': '#14b8a6',
    'other': '#64748b',
}

LEAVE_TYPE_FALLBACK_LABELS = {
    'annual': '年假',
    'personal': '事假',
    'sick': '病假',
    'comp_off': '调休',
    'marriage': '婚假',
    'maternity': '产假/陪产假',
    'other': '其他',
}

DATE_FIELD_TYPES = frozenset({'date', 'datetime', 'date_range', 'time'})


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    if 'T' in text:
        text = text.split('T', 1)[0]
    if ' ' in text:
        text = text.split(' ', 1)[0]
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _form_data(variables: dict) -> dict:
    if not isinstance(variables, dict):
        return {}
    nested = variables.get('form')
    if isinstance(nested, dict):
        return nested
    return variables


def _period_from_raw(raw: Any) -> tuple[date, date] | None:
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        start = _parse_date(raw[0])
        end = _parse_date(raw[1])
    elif isinstance(raw, dict):
        start = _parse_date(raw.get('start') or raw.get('from') or raw.get('begin'))
        end = _parse_date(raw.get('end') or raw.get('to'))
    else:
        start = _parse_date(raw)
        end = start
    if start and end:
        if end < start:
            start, end = end, start
        return start, end
    return None


def _ranges_overlap(start: date, end: date, window_start: date, window_end: date) -> bool:
    return start <= window_end and end >= window_start


def _flatten_fields(schema: dict) -> list[dict]:
    out: list[dict] = []
    for sec in schema.get('sections') or []:
        for field in sec.get('fields') or []:
            out.append(field)
    return out


def _option_label_map(schema: dict, field_key: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for field in _flatten_fields(schema):
        if field.get('key') != field_key:
            continue
        props = field.get('props') or {}
        for opt in props.get('options') or []:
            if not isinstance(opt, dict):
                continue
            value = opt.get('value')
            if value is None:
                value = opt.get('code')
            if value is None:
                continue
            label = opt.get('label') or opt.get('name') or str(value)
            out[str(value)] = str(label)
    return out


def _color_for_key(seed: str) -> str:
    if not seed:
        return CALENDAR_PALETTE[-1]
    h = 0
    for ch in seed:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return CALENDAR_PALETTE[h % len(CALENDAR_PALETTE)]


def _split_csv(raw: str | None, defaults: tuple[str, ...]) -> list[str]:
    if raw is None or not str(raw).strip():
        return list(defaults)
    items = [x.strip() for x in str(raw).split(',') if x.strip()]
    return items or list(defaults)


def _is_auto_form_keys(form_keys: list[str] | None) -> bool:
    if not form_keys:
        return True
    normalized = [k.strip().lower() for k in form_keys if k and str(k).strip()]
    if not normalized or set(normalized) == {'auto'}:
        return True
    if set(normalized) <= {'std_leave', 'demo_leave'}:
        return True
    return False


def _field_sync_enabled(field: dict) -> bool:
    props = field.get('props') or {}
    return props.get('syncToCalendar') is True


def _collect_sync_fields(schema: dict) -> list[dict]:
    """仅收集显式勾选「同步到日历」的日期类字段。"""
    return [
        f for f in _flatten_fields(schema)
        if f.get('type') in DATE_FIELD_TYPES and _field_sync_enabled(f) and f.get('key')
    ]


def _resolve_definitions(form_keys: list[str] | None) -> list[WorkflowDefinition]:
    q = WorkflowDefinition.query.order_by(
        WorkflowDefinition.key,
        WorkflowDefinition.version.desc(),
    )
    if _is_auto_form_keys(form_keys):
        return q.all()
    return q.filter(WorkflowDefinition.key.in_(form_keys)).all()


def _viewer_can_see_all(user) -> bool:
    """系统管理员或具备「查看流程实例」能力的分级管理员。"""
    if is_global_admin(user):
        return True
    caps = admin_capabilities(user)
    return bool(caps.get('can_view_instances'))


def _apply_visibility_filter(q, user, company_id: int | None):
    """有权限看板块/全公司；否则仅本人相关。"""
    if is_global_admin(user):
        return q

    caps = admin_capabilities(user)
    sector_ids = get_user_sector_ids(user)

    if caps.get('can_view_instances') and sector_ids:
        related = or_(
            WorkflowInstance.initiator_id == user.id,
            exists().where(
                and_(
                    TaskInstance.instance_id == WorkflowInstance.id,
                    TaskInstance.assignee_id == user.id,
                    TaskInstance.status.in_(RELATED_APPROVAL_TASK_STATUSES),
                ),
            ),
            exists().where(
                and_(
                    InstanceTimeline.instance_id == WorkflowInstance.id,
                    InstanceTimeline.actor_id == user.id,
                ),
            ),
            WorkflowInstance.business_sector_id.in_(sector_ids),
        )
        return q.filter(related)

    # 普通用户：仅自己发起或参与过的
    related_only = or_(
        WorkflowInstance.initiator_id == user.id,
        exists().where(
            and_(
                TaskInstance.instance_id == WorkflowInstance.id,
                TaskInstance.assignee_id == user.id,
                TaskInstance.status.in_(RELATED_APPROVAL_TASK_STATUSES),
            ),
        ),
        exists().where(
            and_(
                InstanceTimeline.instance_id == WorkflowInstance.id,
                InstanceTimeline.actor_id == user.id,
            ),
        ),
    )
    return q.filter(related_only)


def query_leave_events(
    *,
    viewer,
    window_start: date,
    window_end: date,
    company_id: int | None = None,
    department_id: int | None = None,
    form_keys: list[str] | None = None,
    period_keys: list[str] | None = None,
    leave_type_key: str = DEFAULT_LEAVE_TYPE_KEY,
    statuses: list[str] | None = None,
    show_reason: bool = False,
) -> list[dict]:
    period_keys = period_keys or list(DEFAULT_PERIOD_KEYS)
    statuses = statuses or list(DEFAULT_STATUSES)
    leave_type_key = (leave_type_key or DEFAULT_LEAVE_TYPE_KEY).strip() or DEFAULT_LEAVE_TYPE_KEY

    defs = _resolve_definitions(form_keys)
    if not defs:
        return []

    sync_fields_by_def: dict[int, list[dict]] = {}
    option_map_by_def: dict[int, dict[str, str]] = {}
    schema_by_def: dict[int, dict] = {}
    for d in defs:
        schema = resolve_definition_schema(d) if d else parse_schema(None)
        schema_by_def[d.id] = schema
        fields = _collect_sync_fields(schema)
        if fields:
            sync_fields_by_def[d.id] = fields
            option_map_by_def[d.id] = _option_label_map(schema, leave_type_key)

    def_ids = list(sync_fields_by_def.keys())
    if not def_ids:
        return []

    q = WorkflowInstance.query.options(
        joinedload(WorkflowInstance.definition),
    ).filter(
        WorkflowInstance.definition_id.in_(def_ids),
        WorkflowInstance.status.in_(statuses),
    )
    if company_id:
        q = q.filter(WorkflowInstance.company_id == company_id)
    if department_id:
        q = q.filter(WorkflowInstance.department_id == department_id)

    q = _apply_visibility_filter(q, viewer, company_id)

    pad = timedelta(days=60)
    rough_start = datetime.combine(window_start - pad, datetime.min.time())
    rough_end = datetime.combine(window_end + pad, datetime.max.time())
    q = q.filter(
        WorkflowInstance.started_at.isnot(None),
        WorkflowInstance.started_at <= rough_end,
    )
    q = q.filter(
        (WorkflowInstance.finished_at.is_(None))
        | (WorkflowInstance.finished_at >= rough_start)
        | (WorkflowInstance.started_at >= rough_start)
    )

    instances = q.order_by(WorkflowInstance.id.desc()).limit(3000).all()
    if not instances:
        return []

    user_ids = {i.initiator_id for i in instances if i.initiator_id}
    users = {
        u.id: u
        for u in User.query.filter(User.id.in_(user_ids)).all()
    } if user_ids else {}

    dept_ids = {i.department_id for i in instances if i.department_id}
    depts = {
        d.id: d
        for d in Department.query.filter(Department.id.in_(dept_ids)).all()
    } if dept_ids else {}

    events: list[dict] = []
    for inst in instances:
        fields = sync_fields_by_def.get(inst.definition_id) or []
        if not fields:
            continue
        variables = parse_variables(inst.variables)
        form = _form_data(variables)
        user = users.get(inst.initiator_id)
        user_name = user.display_label() if user else f'用户#{inst.initiator_id}'
        dept = depts.get(inst.department_id) if inst.department_id else None
        public_uuid = ensure_instance_public_uuid(inst)
        def_name = inst.definition.name if inst.definition else ''
        form_key = inst.definition.key if inst.definition else ''
        option_map = option_map_by_def.get(inst.definition_id) or {}
        leave_type = str(form.get(leave_type_key) or '').strip()
        leave_type_label = ''
        if leave_type:
            leave_type_label = option_map.get(leave_type) or LEAVE_TYPE_FALLBACK_LABELS.get(leave_type, leave_type)

        reason = ''
        if show_reason:
            reason = str(form.get('reason') or form.get('title') or '').strip()

        for field in fields:
            fkey = str(field.get('key') or '')
            flabel = str(field.get('label') or fkey)
            period = _period_from_raw(form.get(fkey))
            if not period:
                continue
            start, end = period
            if not _ranges_overlap(start, end, window_start, window_end):
                continue

            # 颜色：请假假别优先，否则按流程+字段稳定分色
            if leave_type and leave_type in LEAVE_TYPE_COLORS and (
                fkey in ('leave_period', 'date_range') or '假' in (def_name or '')
            ):
                color = LEAVE_TYPE_COLORS[leave_type]
            else:
                color = _color_for_key(f'{form_key}:{fkey}')

            topic_parts = [user_name, def_name or form_key, flabel]
            if leave_type_label and fkey in ('leave_period', 'date_range'):
                topic_parts = [user_name, leave_type_label, def_name or flabel]
            title = ' · '.join([p for p in topic_parts if p])
            tooltip = title
            if reason:
                tooltip = f'{title}\n{reason}'
            if inst.display_no:
                tooltip = f'{tooltip}\n单号：{inst.display_no}'

            exclusive_end = end + timedelta(days=1)
            events.append({
                'id': f'cal-{inst.id}-{fkey}',
                'instance_id': inst.id,
                'public_uuid': public_uuid,
                'title': title,
                'tooltip': tooltip,
                'start': start.isoformat(),
                'end': exclusive_end.isoformat(),
                'all_day': True,
                'color': color,
                'user_id': inst.initiator_id,
                'user_name': user_name,
                'department_id': inst.department_id,
                'department_name': dept.name if dept else '',
                'leave_type': leave_type,
                'leave_type_label': leave_type_label,
                'field_key': fkey,
                'field_label': flabel,
                'status': inst.status,
                'form_key': form_key,
                'form_name': def_name,
                'reason': reason if show_reason else '',
                'display_no': inst.display_no or '',
                'can_view_all': _viewer_can_see_all(viewer),
            })

    events.sort(key=lambda e: (e['start'], e['form_key'], e['title']))
    return events
