# -*- coding: utf-8 -*-
"""控件配置表：公司级与个人级数据读写、表单提交后沉淀个人数据。"""
from __future__ import annotations

import json
import uuid

from app.extensions import db
from app.models import OptionSet, OptionSetColumn, OptionSetRecord
from app.models.option_set import SET_TYPE_RECORD, SCOPE_COMPANY, SCOPE_MIXED, SCOPE_PERSONAL


def iter_form_fields(schema: dict):
    """遍历表单字段（含明细列）。"""
    for sec in schema.get('sections') or []:
        for field in sec.get('fields') or []:
            yield field
            if field.get('type') == 'detail':
                for col in (field.get('props') or {}).get('columns') or []:
                    yield col


def _column_keys(option_set: OptionSet) -> set[str]:
    return {
        c.field_key
        for c in option_set.columns.order_by(OptionSetColumn.sort_order, OptionSetColumn.id).all()
    }


def normalize_record_data(data: dict | None, col_keys: set[str]) -> dict[str, str]:
    raw = data if isinstance(data, dict) else {}
    return {k: str(raw.get(k) or '').strip() for k in col_keys}


def data_signature(data: dict[str, str]) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False)


def record_source(rec: OptionSetRecord) -> str:
    return 'personal' if rec.owner_user_id else 'company'


def normalize_column_span(raw) -> int:
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return 24
    v = max(6, min(24, v))
    if v % 2:
        v -= 1
    return max(6, v)


def column_dict(col: OptionSetColumn) -> dict:
    return {
        'id': col.id,
        'field_key': col.field_key,
        'label': col.label,
        'sort_order': col.sort_order,
        'span': normalize_column_span(getattr(col, 'span', None)),
    }


def build_record_dict(rec: OptionSetRecord, columns: list[OptionSetColumn] | None = None) -> dict:
    data = rec.get_data()
    label = rec.row_code
    if columns:
        for c in columns:
            v = data.get(c.field_key)
            if v not in (None, ''):
                label = str(v)
                break
    out = {
        'id': rec.id,
        'row_code': rec.row_code,
        'data': data,
        'label': label,
        'value': rec.row_code,
        'sort_order': rec.sort_order,
        'is_active': rec.is_active,
        'source': record_source(rec),
    }
    if rec.owner_user_id:
        out['owner_user_id'] = rec.owner_user_id
    return out


def record_set_data_scope(option_set: OptionSet) -> str:
    scope = (getattr(option_set, 'data_scope', None) or SCOPE_MIXED).strip()
    if scope in (SCOPE_COMPANY, SCOPE_PERSONAL):
        return scope
    return SCOPE_MIXED


def resolve_record_load_flags(
    option_set: OptionSet,
    include_company: bool,
    include_personal: bool,
) -> tuple[bool, bool]:
    """按配置表数据范围强制隔离：个人表仅返回当前用户个人行。"""
    scope = record_set_data_scope(option_set)
    if scope == SCOPE_COMPANY:
        return True, False
    if scope == SCOPE_PERSONAL:
        return False, True
    return include_company, include_personal


def query_scope_records(
    option_set: OptionSet,
    user_id: int,
    *,
    include_company: bool,
    include_personal: bool,
    personal_user_id: int | None = None,
):
    """查询公司级和/或指定用户的个人行。"""
    q = option_set.records.filter_by(is_active=True)
    clauses = []
    if include_company:
        clauses.append(OptionSetRecord.owner_user_id.is_(None))
    uid = personal_user_id if personal_user_id is not None else user_id
    if include_personal and uid:
        clauses.append(OptionSetRecord.owner_user_id == uid)
    if not clauses:
        return []
    if len(clauses) == 1:
        q = q.filter(clauses[0])
    else:
        from sqlalchemy import or_

        q = q.filter(or_(*clauses))
    return q.order_by(OptionSetRecord.sort_order, OptionSetRecord.id).all()


def list_records_payload(
    option_set: OptionSet,
    user_id: int,
    *,
    include_company: bool = True,
    include_personal: bool = True,
    personal_user_id: int | None = None,
) -> dict:
    include_company, include_personal = resolve_record_load_flags(
        option_set,
        include_company,
        include_personal,
    )
    cols = option_set.columns.order_by(OptionSetColumn.sort_order, OptionSetColumn.id).all()
    rows = query_scope_records(
        option_set,
        user_id,
        include_company=include_company,
        include_personal=include_personal,
        personal_user_id=personal_user_id,
    )
    out_records = [build_record_dict(r, cols) for r in rows]
    return {
        'code': option_set.code,
        'name': option_set.name,
        'data_scope': record_set_data_scope(option_set),
        'columns': [column_dict(c) for c in cols],
        'records': out_records,
    }


def find_company_record_by_data(option_set: OptionSet, data: dict[str, str]) -> OptionSetRecord | None:
    sig = data_signature(data)
    if not any(data.values()):
        return None
    rows = option_set.records.filter(
        OptionSetRecord.owner_user_id.is_(None),
        OptionSetRecord.is_active.is_(True),
    ).all()
    for r in rows:
        keys = _column_keys(option_set)
        if data_signature(normalize_record_data(r.get_data(), keys)) == sig:
            return r
    return None


def upsert_personal_record(
    option_set: OptionSet,
    user_id: int,
    value: dict,
) -> OptionSetRecord | None:
    """将表单中的控件配置表值沉淀为个人数据（与公司级完全相同时跳过）。"""
    if not user_id:
        return None
    col_keys = _column_keys(option_set)
    if not col_keys:
        return None
    data = normalize_record_data(value.get('data') if isinstance(value, dict) else None, col_keys)
    if not any(data.values()):
        return None
    if find_company_record_by_data(option_set, data):
        return None

    sig = data_signature(data)
    personal_rows = option_set.records.filter_by(owner_user_id=user_id, is_active=True).all()
    for r in personal_rows:
        if data_signature(normalize_record_data(r.get_data(), col_keys)) == sig:
            r.set_data(data)
            return r

    row_code = (value.get('row_code') or '').strip() if isinstance(value, dict) else ''
    existing = None
    if row_code:
        existing = option_set.records.filter_by(
            owner_user_id=user_id,
            row_code=row_code,
        ).first()
    if existing:
        existing.set_data(data)
        existing.is_active = True
        return existing

    # 新个人行：避免与公司行 row_code 冲突
    if not row_code or option_set.records.filter_by(row_code=row_code, owner_user_id=None).first():
        row_code = f'u{user_id}_{uuid.uuid4().hex[:10]}'
    while option_set.records.filter_by(owner_user_id=user_id, row_code=row_code).first():
        row_code = f'u{user_id}_{uuid.uuid4().hex[:10]}'

    rec = OptionSetRecord(
        option_set_id=option_set.id,
        owner_user_id=user_id,
        row_code=row_code,
        sort_order=len(personal_rows),
        is_active=True,
    )
    rec.set_data(data)
    db.session.add(rec)
    return rec


def sync_record_sets_from_form(schema: dict, form_data: dict | None, user_id: int) -> None:
    """流程提交后，将自定义控件配置表数据写入个人库。"""
    if not user_id or not isinstance(form_data, dict):
        return

    def handle(field: dict, val) -> None:
        if field.get('type') != 'record_set':
            return
        if not isinstance(val, dict):
            return
        code = ((field.get('props') or {}).get('recordSetCode') or '').strip()
        if not code:
            return
        option_set = OptionSet.query.filter_by(
            code=code,
            is_active=True,
            set_type=SET_TYPE_RECORD,
        ).first()
        if not option_set:
            return
        if record_set_data_scope(option_set) == SCOPE_COMPANY:
            return
        upsert_personal_record(option_set, user_id, val)

    for field in iter_form_fields(schema):
        ftype = field.get('type')
        key = field.get('key')
        if not key:
            continue
        if ftype == 'record_set':
            handle(field, form_data.get(key))
        elif ftype == 'detail':
            for row in form_data.get(key) or []:
                if not isinstance(row, dict):
                    continue
                for col in (field.get('props') or {}).get('columns') or []:
                    ck = col.get('key')
                    if ck and col.get('type') == 'record_set':
                        handle(col, row.get(ck))

    db.session.commit()


def get_record_set_by_code(code: str) -> OptionSet | None:
    code = (code or '').strip()
    if not code:
        return None
    s = OptionSet.query.filter_by(code=code, is_active=True).first()
    if not s or (s.set_type or '') != SET_TYPE_RECORD:
        return None
    return s
