# -*- coding: utf-8 -*-
"""内置表单模板注册表。"""
from __future__ import annotations

from app.services.form_templates import debit_note, expense_reimbursement
from app.services.form_templates.ship_management import SHIP_MANAGEMENT_TEMPLATES


def _register_debit_note():
    return {
        debit_note.TEMPLATE_KEY: {
            'key': debit_note.TEMPLATE_KEY,
            'name': debit_note.TEMPLATE_NAME,
            'description': debit_note.TEMPLATE_DESCRIPTION,
            'icon': 'invoice',
            'build': debit_note.build_debit_note_template_payload,
        },
    }


def _register_expense():
    return {
        expense_reimbursement.TEMPLATE_KEY: {
            'key': expense_reimbursement.TEMPLATE_KEY,
            'name': expense_reimbursement.TEMPLATE_NAME,
            'description': expense_reimbursement.TEMPLATE_DESCRIPTION,
            'icon': 'reimburse',
            'build': expense_reimbursement.build_expense_reimbursement_template_payload,
        },
    }


def _register_ship_templates() -> dict:
    out = {}
    for meta in SHIP_MANAGEMENT_TEMPLATES:
        out[meta['key']] = {
            'key': meta['key'],
            'name': meta['name'],
            'description': meta['description'],
            'icon': meta.get('icon') or 'general',
            'build': meta['build'],
        }
    return out


BUILTIN_FORM_TEMPLATES: dict[str, dict] = {
    **_register_expense(),
    **_register_debit_note(),
    **_register_ship_templates(),
}


def list_builtin_templates() -> list[dict]:
    return [
        {
            'key': meta['key'],
            'name': meta['name'],
            'description': meta['description'],
            'icon': meta.get('icon') or 'general',
        }
        for meta in BUILTIN_FORM_TEMPLATES.values()
    ]


def get_builtin_template(key: str, *, admin_user_id: int | None = None) -> dict | None:
    meta = BUILTIN_FORM_TEMPLATES.get(key)
    if not meta:
        return None
    build_fn = meta['build']
    if key == expense_reimbursement.TEMPLATE_KEY:
        payload = build_fn()
        if admin_user_id and payload.get('workflow', {}).get('process_graph'):
            payload['workflow']['process_graph'] = (
                expense_reimbursement.build_expense_reimbursement_process_graph(admin_user_id)
            )
        return payload
    return build_fn(admin_user_id=admin_user_id)
