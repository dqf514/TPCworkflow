# -*- coding: utf-8 -*-
"""票据/发票重复使用校验（仅针对已通过的申请）。"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any

from app.extensions import db
from app.models import WorkflowInstance
from app.models.receipt_usage import ReceiptUsageRecord
from app.services.form_schema import parse_schema, resolve_definition_schema
from app.services.instance_access import resolve_instance_by_public_uuid

RECEIPT_NUMBER_KEYS = frozenset({
    'voucher_no',
    'invoice_no',
    'ticket_no',
    'document_number',
    'receipt_no',
    'bill_no',
    'fphm',
})

RECEIPT_NUMBER_LABEL_PATTERNS = (
    re.compile(r'票号'),
    re.compile(r'发票号'),
    re.compile(r'订单号'),
    re.compile(r'发票号码'),
)

ATTACHMENT_FIELD_TYPES = frozenset({'attachment', 'image', 'smart_receipt'})


def normalize_document_number(raw: Any) -> str | None:
    if raw is None or raw == '':
        return None
    s = re.sub(r'\s+', '', str(raw).strip().upper())
    s = re.sub(r'[-_/.:：]', '', s)
    if len(s) < 4:
        return None
    return s


def normalize_file_path(raw: Any) -> str | None:
    if raw is None or raw == '':
        return None
    path = str(raw).strip().replace('\\', '/').lstrip('/')
    if not path:
        return None
    if not path.startswith('uploads/'):
        path = f'uploads/{path}'
    return path


def _is_receipt_number_field(field: dict) -> bool:
    key = str(field.get('key') or '')
    if key in RECEIPT_NUMBER_KEYS:
        return True
    label = str(field.get('label') or '')
    return any(p.search(label) for p in RECEIPT_NUMBER_LABEL_PATTERNS)


def _money_amount(val: Any) -> Decimal | None:
    if val is None or val == '':
        return None
    if isinstance(val, dict):
        for k in ('rmb_amount', 'amount'):
            v = val.get(k)
            if v is not None and v != '':
                try:
                    return Decimal(str(v))
                except Exception:  # noqa: BLE001
                    continue
        return None
    try:
        return Decimal(str(val))
    except Exception:  # noqa: BLE001
        return None


def _append_attachment_paths(target: list[dict], files: Any, source_field: str) -> None:
    if not isinstance(files, list):
        return
    for raw in files:
        if not isinstance(raw, dict):
            continue
        path = normalize_file_path(raw.get('path') or raw.get('url'))
        if path:
            target.append({
                'file_path': path,
                'source_field': source_field,
                'document_number': None,
            })


def _append_scalar_entry(
    target: list[dict],
    *,
    source_field: str,
    document_number: str | None,
    merchant_name: str | None = None,
    transaction_date: str | None = None,
    total_amount: Decimal | None = None,
) -> None:
    doc = normalize_document_number(document_number)
    if not doc:
        return
    target.append({
        'document_number': doc,
        'source_field': source_field,
        'merchant_name': merchant_name,
        'transaction_date': transaction_date,
        'total_amount': total_amount,
        'file_path': None,
    })


def _deep_collect_from_form(
    data: Any,
    entries: list[dict],
    prefix: str,
    seen_docs: set[str],
    seen_paths: set[str],
) -> None:
    if isinstance(data, dict):
        if ('path' in data or 'url' in data) and (data.get('name') or data.get('filename')):
            path = normalize_file_path(data.get('path') or data.get('url'))
            if path and path not in seen_paths:
                seen_paths.add(path)
                entries.append({
                    'file_path': path,
                    'source_field': prefix or 'attachment',
                    'document_number': None,
                })
        for key, val in data.items():
            source = f'{prefix}.{key}' if prefix else key
            if key in RECEIPT_NUMBER_KEYS and val not in (None, ''):
                doc = normalize_document_number(val)
                if doc and doc not in seen_docs:
                    seen_docs.add(doc)
                    entries.append({
                        'document_number': doc,
                        'source_field': source,
                        'file_path': None,
                    })
            elif isinstance(val, (dict, list)):
                _deep_collect_from_form(val, entries, source, seen_docs, seen_paths)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            _deep_collect_from_form(item, entries, f'{prefix}[{idx}]', seen_docs, seen_paths)


def extract_receipt_entries(schema: dict | None, form_data: dict | None) -> list[dict]:
    """从表单 schema + 数据中收集票号与附件路径。"""
    if not isinstance(form_data, dict):
        return []
    schema = schema if isinstance(schema, dict) else {}
    entries: list[dict] = []

    def walk_fields(fields: list, prefix: str, row: dict) -> None:
        for field in fields or []:
            if not isinstance(field, dict):
                continue
            ftype = str(field.get('type') or '')
            key = str(field.get('key') or '')
            if not key:
                continue
            source = f'{prefix}.{key}' if prefix else key
            val = row.get(key)

            if ftype == 'detail':
                columns = (field.get('props') or {}).get('columns') or []
                if not isinstance(val, list):
                    continue
                for idx, item in enumerate(val):
                    if not isinstance(item, dict):
                        continue
                    row_prefix = f'{source}[{idx}]'
                    for col in columns:
                        if not isinstance(col, dict):
                            continue
                        col_key = str(col.get('key') or '')
                        if not col_key:
                            continue
                        col_source = f'{row_prefix}.{col_key}'
                        col_val = item.get(col_key)
                        col_type = str(col.get('type') or '')
                        if col_type in ATTACHMENT_FIELD_TYPES:
                            _append_attachment_paths(entries, col_val, col_source)
                        elif _is_receipt_number_field(col):
                            amount = None
                            for amt_key in ('amount', 'total_amount', 'money'):
                                if amt_key in item:
                                    amount = _money_amount(item.get(amt_key))
                                    if amount is not None:
                                        break
                            _append_scalar_entry(
                                entries,
                                source_field=col_source,
                                document_number=str(col_val) if col_val not in (None, '') else None,
                                merchant_name=str(item.get('remark') or item.get('merchant_name') or '') or None,
                                transaction_date=str(item.get('occur_date') or item.get('transaction_date') or '') or None,
                                total_amount=amount,
                            )
                continue

            if ftype in ATTACHMENT_FIELD_TYPES:
                _append_attachment_paths(entries, val, source)
            elif _is_receipt_number_field(field) and val not in (None, ''):
                _append_scalar_entry(
                    entries,
                    source_field=source,
                    document_number=str(val),
                )

    sections = schema.get('sections') or []
    for section in sections:
        if not isinstance(section, dict):
            continue
        walk_fields(section.get('fields') or [], '', form_data)

    if not sections:
        for key, val in form_data.items():
            if isinstance(val, str) and key in RECEIPT_NUMBER_KEYS:
                _append_scalar_entry(entries, source_field=key, document_number=val)

    seen_docs = {e['document_number'] for e in entries if e.get('document_number')}
    seen_paths = {e['file_path'] for e in entries if e.get('file_path')}
    _deep_collect_from_form(form_data, entries, '', seen_docs, seen_paths)

    return entries


def _resolve_exclude_instance_id(exclude_instance_ref: str | int | None) -> int | None:
    if exclude_instance_ref in (None, ''):
        return None
    if isinstance(exclude_instance_ref, int):
        return exclude_instance_ref
    ref = str(exclude_instance_ref).strip()
    if ref.isdigit():
        return int(ref)
    inst = resolve_instance_by_public_uuid(ref)
    return inst.id if inst else None


def _usage_dict(record: ReceiptUsageRecord, reason: str) -> dict[str, Any]:
    return {
        'used': True,
        'reason': reason,
        'document_number': record.document_number,
        'file_path': record.file_path,
        'instance_id': record.instance_id,
        'display_no': record.display_no,
        'source_field': record.source_field,
        'merchant_name': record.merchant_name,
        'transaction_date': record.transaction_date,
        'total_amount': float(record.total_amount) if record.total_amount is not None else None,
    }


def find_duplicate_usage(
    company_id: int,
    *,
    document_number: str | None = None,
    file_path: str | None = None,
    exclude_instance_id: int | None = None,
) -> dict[str, Any] | None:
    doc = normalize_document_number(document_number)
    path = normalize_file_path(file_path)

    if doc:
        q = ReceiptUsageRecord.query.filter_by(company_id=company_id, document_number=doc)
        if exclude_instance_id:
            q = q.filter(ReceiptUsageRecord.instance_id != exclude_instance_id)
        hit = q.order_by(ReceiptUsageRecord.id.desc()).first()
        if hit:
            return _usage_dict(hit, 'document_number')

    if path:
        q = ReceiptUsageRecord.query.filter_by(company_id=company_id, file_path=path)
        if exclude_instance_id:
            q = q.filter(ReceiptUsageRecord.instance_id != exclude_instance_id)
        hit = q.order_by(ReceiptUsageRecord.id.desc()).first()
        if hit:
            return _usage_dict(hit, 'file_path')

    return None


def check_extracted_duplicate(
    company_id: int | None,
    extracted: dict | None,
    file_path: str | None,
    exclude_instance_ref: str | int | None = None,
) -> dict[str, Any] | None:
    if not company_id:
        return None
    exclude_id = _resolve_exclude_instance_id(exclude_instance_ref)
    doc = None
    if isinstance(extracted, dict):
        doc = extracted.get('document_number') or extracted.get('invoice_no') or extracted.get('voucher_no')
    return find_duplicate_usage(
        int(company_id),
        document_number=str(doc) if doc not in (None, '') else None,
        file_path=file_path,
        exclude_instance_id=exclude_id,
    )


def validate_form_receipt_duplicates(
    schema: dict | None,
    form_data: dict | None,
    company_id: int | None,
    exclude_instance_ref: str | int | None = None,
) -> list[str]:
    if not company_id:
        return []
    exclude_id = _resolve_exclude_instance_id(exclude_instance_ref)
    entries = extract_receipt_entries(schema, form_data)
    errors: list[str] = []
    seen_docs: set[str] = set()
    seen_paths: set[str] = set()

    for entry in entries:
        doc = entry.get('document_number')
        path = entry.get('file_path')
        source = entry.get('source_field') or '表单'

        if doc:
            if doc in seen_docs:
                errors.append(f'当前表单内票号 {doc} 重复（{source}）')
                continue
            seen_docs.add(doc)
            hit = find_duplicate_usage(
                int(company_id),
                document_number=doc,
                exclude_instance_id=exclude_id,
            )
            if hit:
                label = hit.get('display_no') or hit.get('instance_id')
                errors.append(f'票号 {doc} 已在已通过申请 {label} 中使用，不可重复报销')

        if path:
            if path in seen_paths:
                continue
            seen_paths.add(path)
            hit = find_duplicate_usage(
                int(company_id),
                file_path=path,
                exclude_instance_id=exclude_id,
            )
            if hit:
                label = hit.get('display_no') or hit.get('instance_id')
                name = path.rsplit('/', 1)[-1]
                errors.append(f'票据附件 {name} 已在已通过申请 {label} 中使用，不可重复上传')

    return errors


def clear_receipt_usage_for_instance(instance_id: int) -> None:
    ReceiptUsageRecord.query.filter_by(instance_id=instance_id).delete(synchronize_session=False)


def sync_receipt_usage_for_instance(inst: WorkflowInstance) -> None:
    """审批通过后登记表单中的票号与附件；非已通过状态则清空登记。"""
    clear_receipt_usage_for_instance(inst.id)
    if inst.status != 'approved':
        return

    definition = inst.definition
    schema = resolve_definition_schema(definition) if definition else parse_schema(None)
    vars_payload = {}
    try:
        vars_payload = json.loads(inst.variables or '{}')
    except json.JSONDecodeError:
        vars_payload = {}
    form_data = vars_payload.get('form') or {}
    entries = extract_receipt_entries(schema, form_data)
    if not entries:
        return

    display_no = inst.display_no or str(inst.id)
    seen_docs: set[str] = set()
    seen_paths: set[str] = set()

    for entry in entries:
        doc = entry.get('document_number')
        path = entry.get('file_path')
        if doc and doc in seen_docs:
            continue
        if path and path in seen_paths:
            continue
        if doc:
            seen_docs.add(doc)
        if path:
            seen_paths.add(path)

        db.session.add(
            ReceiptUsageRecord(
                company_id=inst.company_id,
                instance_id=inst.id,
                display_no=display_no,
                document_number=doc,
                file_path=path,
                merchant_name=entry.get('merchant_name'),
                transaction_date=entry.get('transaction_date'),
                total_amount=entry.get('total_amount'),
                source_field=entry.get('source_field'),
            ),
        )


def backfill_receipt_usage_from_approved() -> int:
    """为历史已通过申请补登记票据使用记录。"""
    count = 0
    insts = WorkflowInstance.query.filter_by(status='approved').all()
    for inst in insts:
        sync_receipt_usage_for_instance(inst)
        count += 1
    db.session.commit()
    return count
