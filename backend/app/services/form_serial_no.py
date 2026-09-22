# -*- coding: utf-8 -*-
"""表单流水号：解析 pattern、原子递增、写入 form。"""
from __future__ import annotations

import re
from datetime import datetime

from app.extensions import db
from app.models.form_serial import FormSerialCounter
from app.services.form_schema import flatten_fields

_SEQ_RE = re.compile(r'\{SEQ(?::(\d+))?\}', re.IGNORECASE)
_VALID_RESET = frozenset({'never', 'day', 'month', 'year'})
_VALID_SCOPE = frozenset({'global', 'company', 'definition'})
_VALID_DATE_PART = frozenset({'none', 'YYYY', 'YYYYMM', 'YYYYMMDD'})


def normalize_serial_config(field: dict) -> dict:
    props = field.get('props') or {}
    serial = props.get('serial') if isinstance(props.get('serial'), dict) else {}

    pattern = str(props.get('pattern') or serial.get('pattern') or '').strip()
    prefix = str(serial.get('prefix') or props.get('prefix') or '').strip()
    suffix = str(serial.get('suffix') or props.get('suffix') or '').strip()

    try:
        seq_digits = int(serial.get('seqDigits') if serial.get('seqDigits') is not None else props.get('seqDigits', 4))
    except (TypeError, ValueError):
        seq_digits = 4
    seq_digits = max(1, min(10, seq_digits))

    reset_cycle = str(serial.get('resetCycle') or props.get('resetCycle') or 'day').strip().lower()
    if reset_cycle not in _VALID_RESET:
        reset_cycle = 'day'

    scope = str(serial.get('scope') or props.get('scope') or 'company').strip().lower()
    if scope not in _VALID_SCOPE:
        scope = 'company'

    date_part = str(serial.get('datePart') or props.get('datePart') or 'YYYYMMDD').strip()
    if date_part.lower() == 'none':
        date_part = 'none'
    elif date_part.upper() in _VALID_DATE_PART:
        date_part = date_part.upper()
    else:
        date_part = 'YYYYMMDD'

    separator = serial.get('separator')
    if separator is None:
        separator = props.get('separator')
    if separator is None:
        separator = '-'
    separator = str(separator)

    return {
        'pattern': pattern,
        'prefix': prefix,
        'suffix': suffix,
        'seqDigits': seq_digits,
        'resetCycle': reset_cycle,
        'scope': scope,
        'datePart': date_part,
        'separator': separator,
    }


def build_serial_pattern(cfg: dict) -> str:
    explicit = (cfg.get('pattern') or '').strip()
    if explicit:
        return explicit

    prefix = cfg.get('prefix') or ''
    suffix = cfg.get('suffix') or ''
    sep = cfg.get('separator')
    if sep is None:
        sep = '-'
    seq_digits = cfg.get('seqDigits', 4)
    date_part = cfg.get('datePart') or 'YYYYMMDD'

    date_token = ''
    if date_part == 'YYYY':
        date_token = '{YYYY}'
    elif date_part == 'YYYYMM':
        date_token = '{YYYYMM}'
    elif date_part != 'none':
        date_token = '{YYYYMMDD}'

    seq_token = f'{{SEQ:{seq_digits}}}'

    if date_token:
        if sep:
            return f'{prefix}{date_token}{sep}{seq_token}{suffix}'
        return f'{prefix}{date_token}{seq_token}{suffix}'

    if prefix and sep:
        return f'{prefix}{sep}{seq_token}{suffix}'
    return f'{prefix}{seq_token}{suffix}'


def _cycle_bucket(reset_cycle: str, now: datetime) -> str:
    if reset_cycle == 'never':
        return 'all'
    if reset_cycle == 'month':
        return now.strftime('%Y%m')
    if reset_cycle == 'year':
        return now.strftime('%Y')
    return now.strftime('%Y%m%d')


def _counter_key(
    scope: str,
    form_definition_id: int | None,
    definition_id: int | None,
    company_id: int | None,
    field_key: str,
    cycle_bucket: str,
) -> str:
    fd = form_definition_id or definition_id or 0
    if scope == 'global':
        return f'serial:g:{field_key}:{cycle_bucket}'
    if scope == 'company':
        return f'serial:c:{company_id or 0}:{fd}:{field_key}:{cycle_bucket}'
    return f'serial:f:{fd}:{field_key}:{cycle_bucket}'


def _default_seq_digits(pattern: str) -> int:
    m = _SEQ_RE.search(pattern)
    if m and m.group(1):
        try:
            return max(1, min(10, int(m.group(1))))
        except ValueError:
            pass
    return 4


def render_serial_pattern(pattern: str, seq: int, now: datetime | None = None) -> str:
    now = now or datetime.now()
    digits = _default_seq_digits(pattern)

    def repl_seq(m: re.Match) -> str:
        n = int(m.group(1)) if m.group(1) else digits
        return str(seq).zfill(max(1, min(10, n)))

    text = _SEQ_RE.sub(repl_seq, pattern)
    text = text.replace('{YYYY}', now.strftime('%Y'))
    text = text.replace('{YY}', now.strftime('%y'))
    text = text.replace('{MM}', now.strftime('%m'))
    text = text.replace('{DD}', now.strftime('%d'))
    text = text.replace('{YYYYMMDD}', now.strftime('%Y%m%d'))
    text = text.replace('{YYYYMM}', now.strftime('%Y%m'))
    return text


def preview_serial_pattern(field: dict, seq: int = 1, now: datetime | None = None) -> str:
    cfg = normalize_serial_config(field)
    pattern = build_serial_pattern(cfg)
    return render_serial_pattern(pattern, seq, now)


def allocate_next_serial_value(counter_key: str) -> int:
    row = (
        FormSerialCounter.query.filter_by(counter_key=counter_key)
        .with_for_update()
        .first()
    )
    if not row:
        row = FormSerialCounter(counter_key=counter_key, last_value=0)
        db.session.add(row)
        db.session.flush()
    row.last_value = int(row.last_value or 0) + 1
    row.updated_at = datetime.now()
    return row.last_value


def strip_client_serial_values(schema: dict, form: dict | None) -> None:
    if not isinstance(form, dict):
        return
    for field in flatten_fields(schema):
        if field.get('type') != 'serial_no':
            continue
        key = field.get('key')
        if key:
            form.pop(key, None)


def apply_form_serial_numbers(
    schema: dict,
    form: dict,
    *,
    form_definition_id: int | None,
    definition_id: int | None,
    company_id: int | None,
    now: datetime | None = None,
) -> None:
    """正式提交前为所有流水号字段分配编号（忽略客户端传入值）。"""
    if not isinstance(form, dict):
        return
    now = now or datetime.now()
    for field in flatten_fields(schema):
        if field.get('type') != 'serial_no':
            continue
        key = field.get('key')
        if not key:
            continue
        cfg = normalize_serial_config(field)
        pattern = build_serial_pattern(cfg)
        cycle = _cycle_bucket(cfg['resetCycle'], now)
        counter_key = _counter_key(
            cfg['scope'],
            form_definition_id,
            definition_id,
            company_id,
            key,
            cycle,
        )
        seq = allocate_next_serial_value(counter_key)
        form[key] = render_serial_pattern(pattern, seq, now)
