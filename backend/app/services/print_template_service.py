# -*- coding: utf-8 -*-
"""打印模板库服务。"""
from __future__ import annotations

import copy
import json
import re

from app.extensions import db
from app.models import PrintTemplate
from app.services.print_templates.builtin_debit_note import (
    BUILTIN_DEBIT_NOTE_CODE,
    DEFAULT_DEBIT_NOTE_SCHEMA,
    build_builtin_debit_note_row,
)

_CODE_RE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')


def _parse_schema(raw: str | dict | None) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def template_dict(row: PrintTemplate, *, include_schema: bool = True) -> dict:
    out = {
        'id': row.id,
        'code': row.code,
        'name': row.name,
        'description': row.description or '',
        'category': row.category or 'custom',
        'is_builtin': bool(row.is_builtin),
        'is_active': bool(row.is_active),
        'created_at': row.created_at.isoformat() if row.created_at else None,
        'updated_at': row.updated_at.isoformat() if row.updated_at else None,
    }
    if include_schema:
        out['schema'] = _parse_schema(row.schema_json)
    return out


def list_templates(*, active_only: bool = False) -> list[dict]:
    q = PrintTemplate.query.order_by(PrintTemplate.is_builtin.desc(), PrintTemplate.id)
    if active_only:
        q = q.filter_by(is_active=True)
    return [template_dict(r, include_schema=False) for r in q.all()]


def get_template_by_code(code: str, *, active_only: bool = False) -> PrintTemplate | None:
    code = (code or '').strip()
    if not code:
        return None
    q = PrintTemplate.query.filter_by(code=code)
    if active_only:
        q = q.filter_by(is_active=True)
    return q.first()


def get_template_schema(code: str) -> dict | None:
    row = get_template_by_code(code, active_only=True)
    if not row:
        return None
    return _parse_schema(row.schema_json)


def merge_template_schema(base: dict, overrides: dict | None) -> dict:
    if not overrides:
        return copy.deepcopy(base)
    merged = copy.deepcopy(base)

    def deep_merge(dst: dict, src: dict) -> None:
        for key, val in src.items():
            if isinstance(val, dict) and isinstance(dst.get(key), dict):
                deep_merge(dst[key], val)
            else:
                dst[key] = copy.deepcopy(val)

    deep_merge(merged, overrides)
    return merged


def resolve_print_schema(print_config: dict | None) -> dict | None:
    cfg = print_config or {}
    if cfg.get('templateMode') != 'custom':
        return None
    code = (cfg.get('templateCode') or '').strip()
    if not code:
        return None
    schema = get_template_schema(code)
    if not schema:
        return None
    overrides = cfg.get('templateOverrides') or {}
    return merge_template_schema(schema, overrides)


def validate_template_payload(data: dict, *, existing_id: int | None = None) -> list[str]:
    errors: list[str] = []
    code = (data.get('code') or '').strip()
    name = (data.get('name') or '').strip()
    if not code:
        errors.append('模板编码不能为空')
    elif not _CODE_RE.match(code):
        errors.append('模板编码须以小写字母开头，仅含字母、数字、下划线')
    else:
        q = PrintTemplate.query.filter_by(code=code)
        if existing_id:
            q = q.filter(PrintTemplate.id != existing_id)
        if q.first():
            errors.append(f'模板编码已存在: {code}')
    if not name:
        errors.append('模板名称不能为空')
    schema = data.get('schema')
    if schema is not None and not isinstance(schema, dict):
        errors.append('模板 schema 须为 JSON 对象')
    return errors


def create_template(data: dict) -> tuple[PrintTemplate | None, list[str]]:
    errors = validate_template_payload(data)
    if errors:
        return None, errors
    schema = data.get('schema') or {}
    row = PrintTemplate(
        code=(data.get('code') or '').strip(),
        name=(data.get('name') or '').strip(),
        description=(data.get('description') or '').strip(),
        category=(data.get('category') or 'custom').strip(),
        is_builtin=bool(data.get('is_builtin')),
        is_active=data.get('is_active', True) is not False,
        schema_json=json.dumps(schema, ensure_ascii=False),
    )
    db.session.add(row)
    db.session.commit()
    return row, []


def update_template(row: PrintTemplate, data: dict) -> list[str]:
    errors = validate_template_payload({**data, 'code': data.get('code', row.code)}, existing_id=row.id)
    if errors:
        return errors
    if not row.is_builtin and 'code' in data:
        row.code = (data.get('code') or row.code).strip()
    if 'name' in data:
        row.name = (data.get('name') or row.name).strip()
    if 'description' in data:
        row.description = (data.get('description') or '').strip()
    if 'category' in data:
        row.category = (data.get('category') or row.category or 'custom').strip()
    if 'is_active' in data:
        row.is_active = bool(data.get('is_active'))
    if 'schema' in data and isinstance(data.get('schema'), dict):
        row.schema_json = json.dumps(data['schema'], ensure_ascii=False)
    db.session.commit()
    return []


def clone_template(row: PrintTemplate, *, new_code: str, new_name: str) -> tuple[PrintTemplate | None, list[str]]:
    payload = {
        'code': new_code,
        'name': new_name,
        'description': row.description or '',
        'category': row.category or 'custom',
        'is_builtin': False,
        'is_active': True,
        'schema': _parse_schema(row.schema_json),
    }
    return create_template(payload)


def delete_template(row: PrintTemplate) -> str | None:
    if row.is_builtin:
        return '内置模板不可删除，可克隆后修改'
    db.session.delete(row)
    db.session.commit()
    return None


def ensure_builtin_templates() -> int:
    """确保内置打印模板存在；不覆盖已有自定义修改。"""
    added = 0
    payload = build_builtin_debit_note_row()
    row = PrintTemplate.query.filter_by(code=payload['code']).first()
    if not row:
        db.session.add(
            PrintTemplate(
                code=payload['code'],
                name=payload['name'],
                description=payload['description'],
                category=payload['category'],
                is_builtin=True,
                is_active=True,
                schema_json=payload['schema_json'],
            ),
        )
        added += 1
    db.session.commit()
    return added


def sample_form_values() -> dict:
    return {
        'recipient_company': 'LAUREL GOLD SHIPPING LIMITED.',
        'recipient_role': 'The Owner of Selo',
        'recipient_name': 'Mr. Paul Lee',
        'recipient_email': 'paul.lee@example.com',
        'email_language': 'en',
        'attn_name': 'Mr. Paul Lee',
        're_subject': 'Selo',
        'debit_note_no': 'R-CS-202606',
        'issue_date': '2026-06-30',
        'currency': 'USD',
        'particulars': [
            {
                'description': 'Management fee',
                'period_month': 'Jun-26',
                'account_code': '51040000',
                'amount': 9700.0,
            },
            {
                'description': 'Manning fee',
                'period_month': 'May-26',
                'account_code': '54000902',
                'amount': 1158.2,
            },
        ],
        'total_amount': 10858.2,
    }


def default_schema_for_editor() -> dict:
    return copy.deepcopy(DEFAULT_DEBIT_NOTE_SCHEMA)
