# -*- coding: utf-8 -*-
"""流程实例导出 Excel。"""
from __future__ import annotations

import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from app.models import BusinessSector, Department, FormDefinition, User, WorkflowInstance
from app.services.form_schema import parse_schema
from app.services.form_value_format import (
    collect_export_columns,
    collect_record_set_codes,
    format_dept_value,
    format_form_value_for_export,
    load_record_set_columns_map,
)
from app.services.graph_utils import parse_variables

_STATUS_LABELS = {
    'running': '审批中',
    'approved': '已通过',
    'rejected': '已驳回',
    'cancelled': '已撤销',
    'draft': '草稿',
}


def _fmt_dt(val) -> str:
    if not val:
        return ''
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%d %H:%M')
    return str(val)


def _last_updated(inst: WorkflowInstance) -> datetime | None:
    if getattr(inst, 'updated_at', None):
        return inst.updated_at
    if inst.finished_at:
        return inst.finished_at
    return inst.started_at


def _resolve_definition_schema(definition, form_def_cache: dict[int, dict]) -> dict:
    if not definition:
        return {}
    if definition.id in form_def_cache:
        return form_def_cache[definition.id]
    schema = parse_schema(definition.form_schema)
    sections = schema.get('sections') or []
    if not sections and definition.form_definition_id:
        cached = form_def_cache.get(-definition.form_definition_id)
        if cached is not None:
            form_def_cache[definition.id] = cached
            return cached
        form_row = FormDefinition.query.get(definition.form_definition_id)
        if form_row:
            schema = parse_schema(form_row.schema_json)
            form_def_cache[-definition.form_definition_id] = schema
    form_def_cache[definition.id] = schema
    return schema


def _merge_export_columns(
    schema: dict,
    form_field_keys: list[str],
    form_labels: dict[str, str],
    field_defs: dict[str, dict],
) -> None:
    keys, labels, defs = collect_export_columns(schema)
    for key in keys:
        if key not in form_field_keys:
            form_field_keys.append(key)
            form_labels[key] = labels[key]
            field_defs[key] = defs[key]


def _format_export_cell(
    export_key: str,
    field_defs: dict[str, dict],
    form_vals: dict,
    *,
    dept_cache: dict[int, Department | None],
    user_cache: dict[int, User | None],
    record_set_columns: dict[str, list[dict]],
) -> str:
    meta = field_defs.get(export_key) or {}
    if meta.get('type') == 'detail_total':
        source = meta.get('source_field') or {}
        raw = form_vals.get(source.get('key') or '')
        return format_form_value_for_export(
            source,
            raw,
            dept_cache=dept_cache,
            user_cache=user_cache,
            record_set_columns=record_set_columns,
        )
    field = meta
    raw = form_vals.get(export_key, '')
    return format_form_value_for_export(
        field,
        raw,
        dept_cache=dept_cache,
        user_cache=user_cache,
        record_set_columns=record_set_columns,
    )


def build_instances_workbook(instances: list[WorkflowInstance]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = '流程清单'

    base_headers = ['流程名称', '业务板块', '状态', '申请人', '申请部门', '提交时间', '最后更新']
    form_field_keys: list[str] = []
    form_labels: dict[str, str] = {}
    field_defs: dict[str, dict] = {}
    schema_cache: dict[int, dict] = {}
    record_set_columns: dict[str, list[dict]] = {}

    if not instances:
        ws.append(base_headers)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    user_ids = {i.initiator_id for i in instances if i.initiator_id}
    dept_ids = {i.department_id for i in instances if i.department_id}
    sector_ids = {i.business_sector_id for i in instances if i.business_sector_id}

    users = {
        u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()
    } if user_ids else {}
    depts = {
        d.id: d for d in Department.query.filter(Department.id.in_(dept_ids)).all()
    } if dept_ids else {}
    sectors = {
        s.id: s for s in BusinessSector.query.filter(BusinessSector.id.in_(sector_ids)).all()
    } if sector_ids else {}

    dept_cache: dict[int, Department | None] = dict(depts)
    user_cache: dict[int, User | None] = dict(users)
    record_set_codes: set[str] = set()

    seen_definitions: set[int] = set()
    for inst in instances:
        definition = inst.definition
        if not definition or definition.id in seen_definitions:
            continue
        seen_definitions.add(definition.id)
        schema = _resolve_definition_schema(definition, schema_cache)
        _merge_export_columns(schema, form_field_keys, form_labels, field_defs)
        record_set_codes |= collect_record_set_codes(schema)

    if record_set_codes:
        record_set_columns = load_record_set_columns_map(record_set_codes)

    rows_data = []
    for inst in instances:
        definition = inst.definition
        initiator = users.get(inst.initiator_id) if inst.initiator_id else None
        sector = sectors.get(inst.business_sector_id) if inst.business_sector_id else None
        variables = parse_variables(inst.variables)
        form_vals = variables.get('form') or {}

        rows_data.append({
            'base': [
                definition.name if definition else '',
                sector.name if sector else '',
                _STATUS_LABELS.get(inst.status, inst.status or ''),
                initiator.display_label() if initiator else '',
                format_dept_value(inst.department_id, dept_cache),
                _fmt_dt(inst.started_at),
                _fmt_dt(_last_updated(inst)),
            ],
            'form': {
                k: _format_export_cell(
                    k,
                    field_defs,
                    form_vals,
                    dept_cache=dept_cache,
                    user_cache=user_cache,
                    record_set_columns=record_set_columns,
                )
                for k in form_field_keys
            },
        })

    headers = base_headers + [form_labels.get(k, k) for k in form_field_keys]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in rows_data:
        ws.append(row['base'] + [row['form'].get(k, '') for k in form_field_keys])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
