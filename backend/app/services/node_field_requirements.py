# -*- coding: utf-8 -*-
"""审批节点：可编辑字段的本节点必填 / 须修改校验。"""
from __future__ import annotations

import json

from app.services.form_schema import _validate_field_value
from app.services.form_visibility import _build_linkage_index, field_is_visible, section_is_visible


def _norm_compare_value(val) -> str:
    if val is None:
        return ''
    if isinstance(val, (dict, list)):
        return json.dumps(val, sort_keys=True, ensure_ascii=False)
    return str(val).strip()


def _detail_column_parents(schema: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for sec in schema.get('sections') or []:
        for field in sec.get('fields') or []:
            if field.get('type') != 'detail':
                continue
            parent_key = field.get('key')
            if not parent_key:
                continue
            for col in (field.get('props') or {}).get('columns') or []:
                ck = col.get('key')
                if ck:
                    out[ck] = {'parent_key': parent_key, 'column': col, 'detail': field}
    return out


def _field_def_by_key(schema: dict, key: str) -> dict | None:
    for sec in schema.get('sections') or []:
        for field in sec.get('fields') or []:
            if field.get('key') == key:
                return field
            if field.get('type') == 'detail':
                for col in (field.get('props') or {}).get('columns') or []:
                    if col.get('key') == key:
                        return col
    return None


def _value_empty_for_field(field: dict, val) -> bool:
    errs: list[str] = []
    label = field.get('label') or field.get('key') or '字段'
    ftype = field.get('type')
    if ftype in ('attachment', 'image', 'smart_receipt'):
        items = val if isinstance(val, list) else []
        return len(items) == 0
    if ftype == 'money' and isinstance(val, dict):
        amt = val.get('amount')
        rmb = val.get('rmb_amount')
        return (amt is None or amt == '') and (rmb is None or rmb == '')
    if ftype == 'plain_amount':
        return val is None or val == ''
    if val is None or val == '' or val == []:
        return True
    _validate_field_value({**field, 'required': True}, val, label, errs)
    return len(errs) > 0


def _find_section_for_field_key(schema: dict, field_key: str) -> dict | None:
    for sec in schema.get('sections') or []:
        for field in sec.get('fields') or []:
            if field.get('key') == field_key:
                return sec
    return None


def validate_node_field_requirements(
    schema: dict,
    form_data: dict,
    node_config: dict,
    *,
    original_form: dict | None = None,
) -> list[str]:
    """校验节点上对可编辑字段的本节点必填 / 须修改设置。"""
    perms = node_config.get('field_permissions') or {}
    required_map = node_config.get('field_node_required') or {}
    must_modify_map = node_config.get('field_must_modify') or {}
    if not required_map and not must_modify_map:
        return []

    form_data = form_data or {}
    original_form = original_form or {}
    errors: list[str] = []
    index = _build_linkage_index(schema)
    detail_parents = _detail_column_parents(schema)

    keys = set(required_map.keys()) | set(must_modify_map.keys())
    for key in keys:
        if perms.get(key) != 'edit':
            continue
        need_required = bool(required_map.get(key))
        need_modify = bool(must_modify_map.get(key))
        if not need_required and not need_modify:
            continue

        if key in detail_parents:
            meta = detail_parents[key]
            parent_key = meta['parent_key']
            col = meta['column']
            detail_field = meta['detail']
            sec = _find_section_for_field_key(schema, parent_key)
            if sec and not section_is_visible(sec, schema, form_data, index):
                continue
            if not field_is_visible(detail_field, schema, form_data, index):
                continue
            rows = form_data.get(parent_key)
            col_label = col.get('label') or key
            detail_label = detail_field.get('label') or parent_key
            if not isinstance(rows, list) or not rows:
                if need_required:
                    errors.append(f'「{detail_label}」至少填写一行，且「{col_label}」为必填')
                continue
            for ri, row in enumerate(rows):
                if not isinstance(row, dict):
                    if need_required:
                        errors.append(f'「{detail_label}」第 {ri + 1} 行·{col_label} 为必填项')
                    continue
                val = row.get(key)
                orig = None
                orig_rows = original_form.get(parent_key)
                if isinstance(orig_rows, list) and ri < len(orig_rows) and isinstance(orig_rows[ri], dict):
                    orig = orig_rows[ri].get(key)
                if need_required and _value_empty_for_field(col, val):
                    errors.append(f'「{detail_label}」第 {ri + 1} 行·{col_label} 为必填项')
                    continue
                if need_modify and _norm_compare_value(val) == _norm_compare_value(orig):
                    errors.append(f'「{detail_label}」第 {ri + 1} 行·{col_label} 须修改后方可同意')
            continue

        field = _field_def_by_key(schema, key)
        if not field:
            continue
        sec = _find_section_for_field_key(schema, key)
        if sec and not section_is_visible(sec, schema, form_data, index):
            continue
        if not field_is_visible(field, schema, form_data, index):
            continue

        label = field.get('label') or key
        val = form_data.get(key)
        orig = original_form.get(key)
        if need_required and _value_empty_for_field(field, val):
            errors.append(f'「{label}」为必填项，请在本节点填写')
            continue
        if need_modify and _norm_compare_value(val) == _norm_compare_value(orig):
            errors.append(f'「{label}」须修改后方可同意')

    return errors


def node_has_field_requirements(node_config: dict | None) -> bool:
    if not node_config:
        return False
    perms = node_config.get('field_permissions') or {}
    required_map = node_config.get('field_node_required') or {}
    must_modify_map = node_config.get('field_must_modify') or {}
    for key, flag in {**required_map, **must_modify_map}.items():
        if flag and perms.get(key) == 'edit':
            return True
    return False
