# -*- coding: utf-8 -*-
"""流程通过后向客户发送单据邮件（独立 SMTP，不影响审批通知）。"""
from __future__ import annotations

import re
from html import escape

from app.extensions import db
from app.models import WorkflowInstance
from app.services.company_branding import get_company_name
from app.services.form_schema import parse_variables, resolve_definition_schema
from app.services.notify import _log_notify, send_email
from app.services.print_template_service import get_template_schema, resolve_print_schema
from app.services.workflow_settings import merge_settings

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_PLACEHOLDER_RE = re.compile(r'\{\{(\w+)\}\}')


def _form_val(form: dict, key: str):
    if not key:
        return None
    return form.get(key)


def _format_money(val) -> str:
    if val is None or val == '':
        return '0.00'
    if isinstance(val, dict):
        for k in ('amount', 'rmb_amount'):
            if val.get(k) not in (None, ''):
                val = val[k]
                break
    try:
        return f'{float(val):,.2f}'
    except (TypeError, ValueError):
        return str(val)


def _format_date_slash(val) -> str:
    if not val:
        return '—'
    s = str(val).strip()
    if len(s) >= 10 and s[4] == '-' and s[7] == '-':
        return f'{s[0:4]}/{int(s[5:7])}/{int(s[8:10])}'
    return s


def _build_context(form: dict, company_name: str) -> dict:
    currency = form.get('currency') or 'USD'
    total = _format_money(form.get('total_amount'))
    return {
        'recipient_name': (form.get('recipient_name') or form.get('attn_name') or 'Sir/Madam').strip(),
        'debit_note_no': str(form.get('debit_note_no') or '—'),
        're_subject': str(form.get('re_subject') or '—'),
        'issue_date': _format_date_slash(form.get('issue_date')),
        'currency': str(currency),
        'total_amount': total,
        'company_name': company_name or 'IMC Ship Management',
    }


def _render_template(text: str, ctx: dict) -> str:
    if not text:
        return ''

    def repl(m):
        key = m.group(1)
        return str(ctx.get(key, ''))

    return _PLACEHOLDER_RE.sub(repl, text)


def _resolve_email_templates(print_schema: dict, lang: str) -> dict:
    templates = (print_schema or {}).get('emailTemplates') or {}
    if lang in templates:
        return templates[lang]
    if 'en' in templates:
        return templates['en']
    return {
        'subject': 'Debit Note {{debit_note_no}}',
        'greeting': 'Dear {{recipient_name}},',
        'body': (
            'Please find the Debit Note {{debit_note_no}} dated {{issue_date}}.\n'
            'Total amount: {{currency}} {{total_amount}}.\n\n'
            'Best regards,\n{{company_name}}'
        ),
    }


def _split_emails(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r'[;,，；\s]+', str(raw).strip())
    out: list[str] = []
    for p in parts:
        e = p.strip()
        if e and _EMAIL_RE.match(e):
            out.append(e)
    return out


def maybe_deliver_document(app, inst: WorkflowInstance) -> None:
    """流程通过后按流程设置发送客户邮件；失败不阻断流程。"""
    if not inst or inst.status != 'approved' or not inst.finished_at:
        return
    definition = inst.definition
    if not definition:
        return

    settings = merge_settings(definition.settings)
    delivery = settings.get('document_delivery') or {}
    if not delivery.get('enabled'):
        return

    schema = resolve_definition_schema(definition)
    print_cfg = schema.get('print') or {}
    print_schema = resolve_print_schema(print_cfg)
    if not print_schema:
        code = (delivery.get('template_code') or print_cfg.get('templateCode') or '').strip()
        if code:
            print_schema = get_template_schema(code)
    if not print_schema:
        return

    variables = parse_variables(inst.variables)
    form = variables.get('form') or {}
    if not isinstance(form, dict):
        return

    email_field = (delivery.get('recipient_email_field') or 'recipient_email').strip()
    to_raw = _form_val(form, email_field)
    recipients = _split_emails(str(to_raw or ''))
    if not recipients:
        return

    lang_field = (delivery.get('email_language_field') or 'email_language').strip()
    lang = str(_form_val(form, lang_field) or 'en').strip().lower()
    if lang not in ('en', 'zh'):
        lang = 'en'

    name_field = (delivery.get('recipient_name_field') or 'recipient_name').strip()
    if name_field and not form.get('recipient_name'):
        form = {**form, 'recipient_name': _form_val(form, name_field)}

    cc_field = (delivery.get('cc_email_field') or 'recipient_email_cc').strip()
    cc_list = _split_emails(str(_form_val(form, cc_field) or ''))

    tpl = _resolve_email_templates(print_schema, lang)
    company_name = get_company_name()
    ctx = _build_context(form, company_name)

    subject = _render_template(tpl.get('subject') or 'Debit Note {{debit_note_no}}', ctx)
    greeting = _render_template(tpl.get('greeting') or 'Dear {{recipient_name}},', ctx)
    body = _render_template(tpl.get('body') or '', ctx)
    text_body = f'{greeting}\n\n{body}'.strip()

    html_greeting = escape(greeting)
    html_body = escape(body).replace('\n', '<br/>')
    html = (
        f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.6;color:#222;">'
        f'<p>{html_greeting}</p><p>{html_body}</p></div>'
    )

    for to_addr in recipients:
        ok, err = send_email(app, to_addr, subject, text_body, html_body=html)
        _log_notify(
            inst.initiator_id,
            'email',
            subject,
            text_body,
            'sent' if ok else 'failed',
            error=err if not ok else None,
            mail_type='document_delivery',
            recipient=to_addr,
            instance_id=inst.id,
            commit=False,
        )

    for cc in cc_list:
        if cc in recipients:
            continue
        ok, err = send_email(app, cc, subject, text_body, html_body=html)
        _log_notify(
            inst.initiator_id,
            'email',
            subject,
            text_body,
            'sent' if ok else 'failed',
            error=err if not ok else None,
            mail_type='document_delivery',
            recipient=cc,
            instance_id=inst.id,
            commit=False,
        )

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
