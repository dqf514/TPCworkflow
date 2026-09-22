# -*- coding: utf-8 -*-
"""审批单列表：金额提取与排序。"""
from __future__ import annotations

import json

from sqlalchemy import asc, desc
from sqlalchemy.orm import Query

from app.models import BusinessSector, Department, User, WorkflowDefinition, WorkflowInstance
from app.services.form_schema import flatten_fields, resolve_definition_schema
from app.services.form_value_format import money_numeric
from app.services.graph_utils import find_node, parse_graph, parse_variables, resolve_node_display_name

_AMOUNT_KEYS = (
    'total_amount',
    'payment_amount',
    'amount',
    'reimbursement_amount',
    'pay_amount',
    'invoice_amount',
    'grand_total',
    'expense_total',
    'sum_amount',
)

_TOTAL_LABEL_HINTS = ('总金额', '合计', '总计', '报销金额', '付款金额')
_AMOUNT_FIELD_TYPES = frozenset({'money', 'plain_amount', 'formula'})

_SORTABLE_FIELDS = {
    'display_no': WorkflowInstance.display_no,
    'status': WorkflowInstance.status,
    'started_at': WorkflowInstance.started_at,
    'updated_at': WorkflowInstance.updated_at,
    'finished_at': WorkflowInstance.finished_at,
    'definition_name': WorkflowDefinition.name,
    'initiator_name': User.display_name,
    'department_name': Department.name,
    'business_sector_name': BusinessSector.name,
}


def _currency_of(val) -> str:
    if isinstance(val, dict) and val.get('currency') not in (None, ''):
        return str(val.get('currency')).upper()
    return 'CNY'


def _pick_named_amount(form: dict) -> tuple[float | None, str | None]:
    for key in _AMOUNT_KEYS:
        val = form.get(key)
        amount = money_numeric(val)
        if amount is not None:
            return amount, _currency_of(val)
    return None, None


def _pick_schema_total(form: dict, schema: dict) -> tuple[float | None, str | None]:
    """优先取标签像总金额/合计的主表金额、公式字段。"""
    fallback: tuple[float | None, str | None] = (None, None)
    for field in flatten_fields(schema):
        ftype = field.get('type')
        key = field.get('key')
        if not key or ftype not in _AMOUNT_FIELD_TYPES:
            continue
        val = form.get(key)
        amount = money_numeric(val)
        if amount is None:
            continue
        label = str(field.get('label') or '')
        if any(h in label for h in _TOTAL_LABEL_HINTS) or key in _AMOUNT_KEYS:
            return amount, _currency_of(val)
        if fallback[0] is None:
            fallback = (amount, _currency_of(val))
    return fallback


def _sum_detail_amounts(form: dict, schema: dict) -> tuple[float | None, str | None]:
    """报销等：把明细表金额列加总（与表单底部「合计」一致）。"""
    total = 0.0
    found = False
    currency = 'CNY'
    for field in flatten_fields(schema):
        if field.get('type') != 'detail':
            continue
        key = field.get('key')
        rows = form.get(key) if key else None
        if not isinstance(rows, list) or not rows:
            continue
        cols = (field.get('props') or {}).get('columns') or []
        money_cols = [
            c.get('key')
            for c in cols
            if c.get('type') in _AMOUNT_FIELD_TYPES and c.get('key')
        ]
        if not money_cols:
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            for ck in money_cols:
                raw = row.get(ck)
                n = money_numeric(raw)
                if n is None:
                    continue
                total += n
                found = True
                if isinstance(raw, dict) and raw.get('currency'):
                    currency = str(raw.get('currency')).upper()
    if found:
        return round(total, 2), currency
    return None, None


def extract_instance_total_amount(inst: WorkflowInstance) -> tuple[float | None, str | None]:
    variables = parse_variables(inst.variables)
    form = variables.get('form') if isinstance(variables, dict) else None
    if not isinstance(form, dict):
        return None, None

    named = _pick_named_amount(form)
    if named[0] is not None:
        return named

    schema = resolve_definition_schema(inst.definition) if inst.definition else {}
    schema_hit = _pick_schema_total(form, schema)
    if schema_hit[0] is not None:
        return schema_hit

    detail_hit = _sum_detail_amounts(form, schema)
    if detail_hit[0] is not None:
        return detail_hit

    for val in form.values():
        if isinstance(val, dict) and ('rmb_amount' in val or 'amount' in val):
            amount = money_numeric(val)
            if amount is not None:
                return amount, _currency_of(val)
    return None, None


def resolve_instance_current_node_ids(inst: WorkflowInstance) -> list[str]:
    """运行中实例的当前节点 id（与详情流程图逻辑一致）。"""
    if inst.status != 'running':
        return []
    try:
        current_ids = json.loads(inst.current_node_ids or '[]')
    except (json.JSONDecodeError, TypeError):
        current_ids = []
    if not isinstance(current_ids, list):
        current_ids = []
    current_ids = [str(x) for x in current_ids if x]
    if not current_ids:
        current_ids = [
            str(t.node_id)
            for t in inst.tasks.filter_by(status='pending').all()
            if t.node_id
        ]
    seen: set[str] = set()
    ordered: list[str] = []
    for nid in current_ids:
        if nid not in seen:
            seen.add(nid)
            ordered.append(nid)
    return ordered


def _instance_is_stuck_on_gateway(inst: WorkflowInstance) -> bool:
    """运行中、无待办，且当前停在条件/结束/开始节点 → 实际已走完。"""
    if inst.status != 'running':
        return False
    if inst.tasks.filter_by(status='pending').first():
        return False
    node_ids = resolve_instance_current_node_ids(inst)
    if not node_ids:
        return True
    graph = (
        parse_graph(inst.definition.process_graph)
        if inst.definition
        else {'nodes': [], 'edges': []}
    )
    types = set()
    for nid in node_ids:
        node = find_node(graph, nid)
        types.add((node or {}).get('type') or '')
    return types <= {'condition', 'end', 'start', ''}


def resolve_instance_current_node_label(inst: WorkflowInstance) -> str | None:
    """运行中时返回当前节点在设计器中的自定义名称，用于列表状态展示。"""
    if _instance_is_stuck_on_gateway(inst):
        return None
    node_ids = resolve_instance_current_node_ids(inst)
    if not node_ids:
        return None
    graph = (
        parse_graph(inst.definition.process_graph)
        if inst.definition
        else {'nodes': [], 'edges': []}
    )
    names: list[str] = []
    seen_names: set[str] = set()
    for nid in node_ids:
        name = resolve_node_display_name(find_node(graph, nid), nid)
        if name and name not in seen_names:
            seen_names.add(name)
            names.append(name)
    return '、'.join(names) if names else None


def attach_instance_status_meta(inst: WorkflowInstance, row: dict) -> dict:
    if _instance_is_stuck_on_gateway(inst):
        row['status'] = 'approved'
        row['current_node_label'] = None
        return row
    row['current_node_label'] = resolve_instance_current_node_label(inst)
    return row


def enrich_instance_list_row(inst: WorkflowInstance, row: dict) -> dict:
    amount, currency = extract_instance_total_amount(inst)
    row['total_amount'] = amount
    row['amount_currency'] = currency if amount is not None else None
    if 'display_no' not in row:
        row['display_no'] = inst.display_no or str(inst.id)
    return attach_instance_status_meta(inst, row)


def apply_instance_list_sort(
    q: Query,
    *,
    sort_field: str | None = None,
    sort_order: str | None = None,
    default_field: str = 'started_at',
) -> Query:
    field_key = (sort_field or '').strip() or default_field
    if field_key not in _SORTABLE_FIELDS:
        field_key = default_field
    direction = desc if (sort_order or 'desc').lower() != 'asc' else asc
    col = _SORTABLE_FIELDS[field_key]

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
        return q.order_by(direction(col), direction(WorkflowInstance.id))
    return q.order_by(direction(col), direction(WorkflowInstance.id))
