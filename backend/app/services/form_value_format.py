# -*- coding: utf-8 -*-
"""表单字段值导出/展示格式化。"""
from __future__ import annotations

import json
from typing import Any

from app.models import Department, OptionSetColumn, User
from app.services.form_schema import flatten_fields
from app.services.record_set_service import column_dict, get_record_set_by_code


def extract_dept_ids(val: Any) -> list[int]:
    if val is None or val == '':
        return []
    if isinstance(val, list):
        ids: list[int] = []
        for item in val:
            ids.extend(extract_dept_ids(item))
        return ids
    if isinstance(val, dict):
        for key in ('id', 'department_id', 'value', 'dept_id'):
            raw = val.get(key)
            if raw not in (None, ''):
                try:
                    return [int(raw)]
                except (TypeError, ValueError):
                    continue
        return []
    try:
        return [int(val)]
    except (TypeError, ValueError):
        return []


def extract_user_ids(val: Any) -> list[int]:
    if val is None or val == '':
        return []
    if isinstance(val, list):
        ids: list[int] = []
        for item in val:
            ids.extend(extract_user_ids(item))
        return ids
    if isinstance(val, dict):
        for key in ('id', 'user_id', 'value'):
            raw = val.get(key)
            if raw not in (None, ''):
                try:
                    return [int(raw)]
                except (TypeError, ValueError):
                    continue
        return []
    try:
        return [int(val)]
    except (TypeError, ValueError):
        return []


def money_numeric(val: Any) -> float | None:
    if val is None or val == '':
        return None
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    if isinstance(val, str):
        text = val.strip().replace(',', '').replace('￥', '').replace('¥', '')
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    if isinstance(val, dict):
        for key in ('rmb_amount', 'amount'):
            n = val.get(key)
            if n not in (None, ''):
                try:
                    return float(n)
                except (TypeError, ValueError):
                    continue
    return None


def format_money_total(total: float, currency: str = 'CNY') -> str:
    if currency in ('CNY', 'RMB'):
        return f'￥{total:,.2f}'
    return f'{total:,.2f} {currency}'


def format_money_value(val: Any) -> str:
    if not isinstance(val, dict):
        n = money_numeric(val)
        return format_money_total(n) if n is not None else ''
    amt = val.get('amount')
    if amt in (None, ''):
        return ''
    cur = str(val.get('currency') or val.get('unit') or 'CNY').upper()
    try:
        amount = float(amt)
    except (TypeError, ValueError):
        return str(amt)
    if cur in ('CNY', 'RMB'):
        rmb = val.get('rmb_amount')
        if rmb not in (None, ''):
            try:
                return format_money_total(float(rmb))
            except (TypeError, ValueError):
                pass
        return format_money_total(amount)
    rmb = val.get('rmb_amount')
    parts = [f'{cur} {amount:,.2f}']
    if rmb not in (None, ''):
        try:
            parts.append(f'折合 {format_money_total(float(rmb))}')
        except (TypeError, ValueError):
            pass
    return ' '.join(parts)


def format_dept_value(val: Any, dept_cache: dict[int, Department | None]) -> str:
    if val is None or val == '':
        return ''
    if isinstance(val, dict):
        label = val.get('label') or val.get('name') or val.get('display_name')
        dept_ids = extract_dept_ids(val)
        if dept_ids:
            return format_dept_value(dept_ids[0], dept_cache)
        if label:
            return str(label)
    dept_ids = extract_dept_ids(val)
    if not dept_ids:
        return str(val)
    parts: list[str] = []
    for dept_id in dept_ids:
        if dept_id not in dept_cache:
            dept_cache[dept_id] = Department.query.get(dept_id)
        dept = dept_cache.get(dept_id)
        name = dept.name if dept else str(dept_id)
        parts.append(f'{name}（{dept_id}）')
    return '、'.join(parts)


def format_user_value(val: Any, user_cache: dict[int, User | None]) -> str:
    if val is None or val == '':
        return ''
    if isinstance(val, dict):
        label = val.get('label') or val.get('name') or val.get('display_name')
        user_ids = extract_user_ids(val)
        if user_ids:
            return format_user_value(user_ids[0], user_cache)
        if label:
            return str(label)
    user_ids = extract_user_ids(val)
    if not user_ids:
        return str(val)
    parts: list[str] = []
    for user_id in user_ids:
        if user_id not in user_cache:
            user_cache[user_id] = User.query.get(user_id)
        user = user_cache.get(user_id)
        name = user.display_label() if user else str(user_id)
        parts.append(f'{name}（{user_id}）')
    return '、'.join(parts)


def format_record_set_value(
    field: dict,
    val: Any,
    record_set_columns: dict[str, list[dict]],
) -> str:
    if not isinstance(val, dict):
        return ''
    data = val.get('data') or {}
    if not isinstance(data, dict):
        return ''
    code = ((field.get('props') or {}).get('recordSetCode') or '').strip()
    columns = record_set_columns.get(code) or []
    if columns:
        parts: list[str] = []
        for col in columns:
            text = data.get(col.get('field_key'))
            if text not in (None, ''):
                parts.append(f'{col.get("label") or col.get("field_key")}: {text}')
        return '；'.join(parts)
    parts = [str(v) for v in data.values() if str(v or '').strip()]
    return '；'.join(parts)


_AMOUNT_SUMMARY_TYPES = frozenset({'money', 'plain_amount'})


def format_detail_total(field: dict, val: Any) -> str:
    if not isinstance(val, list) or not val:
        return ''
    columns = (field.get('props') or {}).get('columns') or []
    amount_cols = [c for c in columns if c.get('type') in _AMOUNT_SUMMARY_TYPES and c.get('key')]
    if amount_cols:
        total = 0.0
        has_any = False
        for row in val:
            if not isinstance(row, dict):
                continue
            for col in amount_cols:
                n = money_numeric(row.get(col['key']))
                if n is not None:
                    total += n
                    has_any = True
        if has_any:
            return format_money_total(total)
    return f'共 {len(val)} 行'


def format_option_value(field: dict, val: Any) -> str:
    if val is None or val == '':
        return ''
    options = (field.get('props') or {}).get('options') or []
    if isinstance(val, list):
        labels: list[str] = []
        for item in val:
            text = format_option_value(field, item)
            if text:
                labels.append(text)
        return '、'.join(labels)
    val_str = str(val)
    for opt in options:
        code = str(opt.get('code') if opt.get('code') is not None else opt.get('value') or '')
        if code == val_str:
            return str(opt.get('name') or opt.get('label') or code)
    return val_str


def format_form_value_for_export(
    field: dict,
    val: Any,
    *,
    dept_cache: dict[int, Department | None],
    user_cache: dict[int, User | None],
    record_set_columns: dict[str, list[dict]],
) -> str:
    if val is None or val == '':
        return ''
    ftype = field.get('type')
    if ftype == 'dept_picker':
        return format_dept_value(val, dept_cache)
    if ftype == 'user_picker':
        return format_user_value(val, user_cache)
    if ftype == 'money':
        return format_money_value(val)
    if ftype == 'plain_amount':
        n = money_numeric(val)
        return format_money_total(n) if n is not None else ''
    if ftype == 'record_set':
        return format_record_set_value(field, val, record_set_columns)
    if ftype == 'detail':
        return format_detail_total(field, val)
    if ftype == 'switch':
        return '是' if val else '否'
    if ftype == 'date_range':
        from app.services.date_range_value import format_date_range_value, uses_half_day
        return format_date_range_value(val, half_day=uses_half_day(field))
    if ftype in ('select', 'radio', 'multi_select', 'checkbox_group'):
        return format_option_value(field, val)
    if ftype == 'related_form':
        if isinstance(val, list):
            parts: list[str] = []
            for item in val:
                if isinstance(item, dict):
                    parts.append(str(item.get('title') or item.get('instance_id') or item.get('id') or ''))
                else:
                    parts.append(str(item))
            return '；'.join([p for p in parts if p])
        if isinstance(val, dict):
            return str(val.get('title') or val.get('instance_id') or val.get('id') or '')
    if isinstance(val, list):
        return '、'.join(str(x) for x in val)
    if isinstance(val, dict):
        label = val.get('label') or val.get('name') or val.get('display_name')
        if label:
            return str(label)
        try:
            return json.dumps(val, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(val)
    return str(val)


def load_record_set_columns_map(codes: set[str]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for code in codes:
        option_set = get_record_set_by_code(code)
        if not option_set:
            out[code] = []
            continue
        cols = option_set.columns.order_by(
            OptionSetColumn.sort_order,
            OptionSetColumn.id,
        ).all()
        out[code] = [column_dict(c) for c in cols]
    return out


def collect_record_set_codes(schema: dict) -> set[str]:
    codes: set[str] = set()
    for field in flatten_fields(schema):
        if field.get('type') != 'record_set':
            continue
        code = ((field.get('props') or {}).get('recordSetCode') or '').strip()
        if code:
            codes.add(code)
    return codes


def collect_export_columns(schema: dict) -> tuple[list[str], dict[str, str], dict[str, dict]]:
    """返回 (列 key 列表, 列标题, 列字段定义或 detail 包装)。"""
    keys: list[str] = []
    labels: dict[str, str] = {}
    field_defs: dict[str, dict] = {}
    for field in flatten_fields(schema):
        ftype = field.get('type')
        if ftype in {
            'divider',
            'text_block',
            'section_title',
            'attachment',
            'image',
            'smart_receipt',
            'serial_no',
        }:
            continue
        fkey = field.get('key') or field.get('id')
        if not fkey:
            continue
        if ftype == 'detail':
            export_key = f'{fkey}__total'
            label = (field.get('label') or fkey).strip()
            keys.append(export_key)
            labels[export_key] = f'{label}总金额'
            field_defs[export_key] = {'type': 'detail_total', 'source_field': field}
            continue
        if fkey in field_defs:
            continue
        keys.append(fkey)
        labels[fkey] = field.get('label') or fkey
        field_defs[fkey] = field
    return keys, labels, field_defs
