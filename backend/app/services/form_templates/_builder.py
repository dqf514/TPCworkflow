# -*- coding: utf-8 -*-
"""内置表单模板通用构建器。"""
from __future__ import annotations

import copy
import uuid

from app.services.form_schema import DEFAULT_SCHEMA, validate_schema
from app.services.workflow_settings import DEFAULT_WORKFLOW_SETTINGS

SPAN_HALF = {'desktop': 12, 'mobile': 24}
SPAN_FULL = {'desktop': 24, 'mobile': 24}


def _fid(prefix: str) -> str:
    return f'fld_{prefix}_{uuid.uuid4().hex[:6]}'


def f_input(key: str, label: str, *, required=False, placeholder='', span=SPAN_HALF, full_width=False):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'input',
        'label': label,
        'required': required,
        'visible': True,
        'printable': True,
        'placeholder': placeholder,
        'span': SPAN_FULL if full_width else span,
        'props': {},
    }


def f_textarea(key: str, label: str, *, required=False, placeholder='', rows=3):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'textarea',
        'label': label,
        'required': required,
        'visible': True,
        'printable': True,
        'placeholder': placeholder,
        'span': SPAN_FULL,
        'props': {'rows': rows},
    }


def f_select(key: str, label: str, options: list[dict], *, required=False):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'select',
        'label': label,
        'required': required,
        'visible': True,
        'printable': True,
        'span': SPAN_HALF,
        'props': {'options': options},
    }


def f_date(key: str, label: str, *, required=False, sync_to_calendar=False):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'date',
        'label': label,
        'required': required,
        'visible': True,
        'printable': True,
        'span': SPAN_HALF,
        'props': {'syncToCalendar': True} if sync_to_calendar else {},
    }


def f_date_range(
    key: str,
    label: str,
    *,
    required=False,
    sync_to_calendar=False,
    half_day=False,
    auto_days_key: str | None = None,
    count_workdays=False,
):
    props: dict = {}
    if sync_to_calendar:
        props['syncToCalendar'] = True
    if half_day:
        props['halfDay'] = True
    if count_workdays:
        props['countWorkdays'] = True
    if auto_days_key:
        props['autoDaysKey'] = auto_days_key
    return {
        'id': _fid(key),
        'key': key,
        'type': 'date_range',
        'label': label,
        'required': required,
        'visible': True,
        'printable': True,
        'span': SPAN_FULL,
        'props': props,
    }


def f_leave_calendar(
    label: str = '日历',
    *,
    form_keys: list[str] | None = None,
    period_field_keys: list[str] | None = None,
    leave_type_field_key: str = 'leave_type',
    include_running: bool = False,
    show_reason: bool = False,
    height: int = 520,
):
    """只读公共日历（不参与表单提交）。"""
    return {
        'id': _fid('leave_calendar'),
        'key': '',
        'type': 'leave_calendar',
        'label': label,
        'required': False,
        'visible': True,
        'printable': False,
        'readonly': True,
        'span': SPAN_FULL,
        'props': {
            'formKeys': form_keys or ['auto'],
            'periodFieldKeys': period_field_keys or ['leave_period', 'date_range'],
            'leaveTypeFieldKey': leave_type_field_key,
            'includeRunning': include_running,
            'showReason': show_reason,
            'height': height,
        },
    }


def f_money(key: str, label: str, *, required=False):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'money',
        'label': label,
        'required': required,
        'visible': True,
        'printable': True,
        'span': SPAN_HALF,
        'props': {'showExchange': True},
    }


def f_number(
    key: str,
    label: str,
    *,
    required=False,
    placeholder='',
    readonly=False,
    step=None,
    precision=None,
):
    props = {}
    if step is not None:
        props['step'] = step
    if precision is not None:
        props['precision'] = precision
    return {
        'id': _fid(key),
        'key': key,
        'type': 'number',
        'label': label,
        'required': required,
        'readonly': readonly,
        'visible': True,
        'printable': True,
        'placeholder': placeholder,
        'span': SPAN_HALF,
        'props': props,
    }


def f_dept(key: str, label: str, *, required=False):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'dept_picker',
        'label': label,
        'required': required,
        'visible': True,
        'printable': True,
        'span': SPAN_HALF,
        'props': {'multiple': False, 'defaultPrimaryDept': True, 'syncApplyOrg': True},
    }


def f_user(key: str, label: str, *, required=False):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'user_picker',
        'label': label,
        'required': required,
        'visible': True,
        'printable': True,
        'span': SPAN_HALF,
        'props': {'multiple': False},
    }


def f_attachment(key: str, label: str, *, required=False):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'attachment',
        'label': label,
        'required': required,
        'visible': True,
        'printable': True,
        'span': SPAN_FULL,
        'props': {'maxCount': 10},
    }


def f_switch(key: str, label: str):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'switch',
        'label': label,
        'required': False,
        'visible': True,
        'printable': True,
        'span': SPAN_HALF,
        'props': {},
    }


def opt(name: str, code: str) -> dict:
    return {'name': name, 'code': code, 'label': name, 'value': code}


def vessel_fields(*, required=True):
    """船舶管理公司常用：船名、航次。"""
    return [
        f_input('vessel_name', '船名', required=required, placeholder='如：MV OCEAN STAR'),
        f_input('voyage_no', '航次/航次号', required=False, placeholder='如：V2026-01'),
    ]


def build_schema(title: str, description: str, sections: list[dict]) -> dict:
    schema = copy.deepcopy(DEFAULT_SCHEMA)
    schema['title'] = title
    schema['description'] = description
    out_sections = []
    for sec in sections:
        out_sections.append({
            'id': sec.get('id') or f'sec_{uuid.uuid4().hex[:8]}',
            'title': sec.get('title') or '申请内容',
            'collapsed': False,
            'fields': sec.get('fields') or [],
        })
    schema['sections'] = out_sections
    errs = validate_schema(schema)
    if errs:
        raise ValueError(f'{title} schema 无效：' + '；'.join(errs))
    return schema


def build_standard_process_graph(admin_user_id: int | None = None) -> dict:
    """部门负责人 → 财务/管理员审批。"""
    return {
        'nodes': [
            {'id': 'start', 'type': 'start', 'x': 120, 'y': 280},
            {
                'id': 'approve_dept',
                'type': 'approver',
                'x': 360,
                'y': 280,
                'config': {
                    'assignee_type': 'flow_role',
                    'flow_role_code': 'dept_leader',
                    'apv_rel': 'or',
                },
            },
            {
                'id': 'approve_finance',
                'type': 'approver',
                'x': 600,
                'y': 280,
                'config': {
                    'assignee_type': 'fixed_users',
                    'user_ids': [admin_user_id] if admin_user_id else [],
                    'apv_rel': 'or',
                },
            },
            {'id': 'end', 'type': 'end', 'x': 840, 'y': 280},
        ],
        'edges': [
            {'source': 'start', 'target': 'approve_dept'},
            {'source': 'approve_dept', 'target': 'approve_finance'},
            {'source': 'approve_finance', 'target': 'end'},
        ],
    }


def build_workflow_settings(*, require_comment=True, require_sign=False) -> dict:
    settings = copy.deepcopy(DEFAULT_WORKFLOW_SETTINGS)
    settings['require_comment'] = require_comment
    settings['require_handwritten_sign'] = require_sign
    return settings


def build_template_payload(
    *,
    key: str,
    name: str,
    description: str,
    icon: str,
    sections: list[dict],
    admin_user_id: int | None = None,
    require_comment: bool = True,
    require_sign: bool = False,
) -> dict:
    schema = build_schema(name, description, sections)
    return {
        'key': key,
        'name': name,
        'description': description,
        'icon': icon,
        'schema': schema,
        'workflow': {
            'key': key,
            'name': name,
            'scope_type': 'global',
            'process_graph': build_standard_process_graph(admin_user_id),
            'settings': build_workflow_settings(
                require_comment=require_comment,
                require_sign=require_sign,
            ),
        },
    }
