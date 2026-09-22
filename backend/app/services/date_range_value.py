# -*- coding: utf-8 -*-
"""日期区间：上午/下午精度与 0.5 天计算。"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Callable

HALF_LABELS_ZH = {'am': '上午', 'pm': '下午'}


def to_date_only(raw: Any) -> str:
    if raw is None or raw == '':
        return ''
    if isinstance(raw, datetime):
        return raw.date().isoformat()
    if isinstance(raw, date):
        return raw.isoformat()
    text = str(raw).strip()
    if not text:
        return ''
    if 'T' in text:
        text = text.split('T', 1)[0]
    if ' ' in text:
        text = text.split(' ', 1)[0]
    text = text.replace('/', '-')
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return ''


def normalize_half(raw: Any, fallback: str = 'am') -> str:
    text = str(raw or '').strip().lower()
    if text in ('pm', 'afternoon', '下午'):
        return 'pm'
    if text in ('am', 'morning', '上午'):
        return 'am'
    return fallback if fallback in ('am', 'pm') else 'am'


def parse_date_range(raw: Any) -> dict | None:
    if raw is None or raw == '':
        return None
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        start = to_date_only(raw[0])
        end = to_date_only(raw[1])
        if not start or not end:
            return None
        return {'start': start, 'end': end}
    if isinstance(raw, dict):
        start = to_date_only(raw.get('start') or raw.get('from') or raw.get('begin'))
        end = to_date_only(raw.get('end') or raw.get('to'))
        if not start or not end:
            return None
        out = {'start': start, 'end': end}
        if raw.get('startHalf') is not None or raw.get('start_half') is not None:
            out['startHalf'] = normalize_half(raw.get('startHalf', raw.get('start_half')), 'am')
        if raw.get('endHalf') is not None or raw.get('end_half') is not None:
            out['endHalf'] = normalize_half(raw.get('endHalf', raw.get('end_half')), 'pm')
        days = raw.get('days')
        try:
            if days not in (None, ''):
                out['days'] = float(days)
        except (TypeError, ValueError):
            pass
        return out
    single = to_date_only(raw)
    if not single:
        return None
    return {'start': single, 'end': single}


def calc_range_days(
    start: str,
    end: str,
    start_half: str | None = None,
    end_half: str | None = None,
    half_day: bool = False,
    is_workday: Callable[[date], bool] | None = None,
) -> float | None:
    try:
        a = date.fromisoformat(start)
        b = date.fromisoformat(end)
    except ValueError:
        return None
    if b < a:
        return None
    sh = start_half or 'am'
    eh = end_half or 'pm'
    if half_day and a == b and sh == 'pm' and eh == 'am':
        return None

    def _weight(d: date) -> float:
        if is_workday and not is_workday(d):
            return 0.0
        if not half_day:
            return 1.0
        if d == a == b:
            return 0.5 if sh == eh else 1.0
        if d == a and sh == 'pm':
            return 0.5
        if d == b and eh == 'am':
            return 0.5
        return 1.0

    total = 0.0
    d = a
    while d <= b:
        total += _weight(d)
        d += timedelta(days=1)
    return round(total * 2) / 2


def count_skipped_days(
    start: str,
    end: str,
    is_workday: Callable[[date], bool] | None = None,
) -> int:
    if not is_workday:
        return 0
    try:
        a = date.fromisoformat(start)
        b = date.fromisoformat(end)
    except ValueError:
        return 0
    n = 0
    d = a
    while d <= b:
        if not is_workday(d):
            n += 1
        d += timedelta(days=1)
    return n


def _number_keys(schema: dict | None) -> list[str]:
    keys: list[str] = []
    for sec in (schema or {}).get('sections') or []:
        for field in sec.get('fields') or []:
            if field.get('type') == 'number' and field.get('key'):
                keys.append(str(field.get('key')))
    return keys


def auto_days_key_of(field: dict, schema: dict | None = None) -> str:
    props = field.get('props') or {}
    explicit = str(props.get('autoDaysKey') or '').strip()
    if explicit:
        return explicit
    number_keys = _number_keys(schema)
    if 'leave_days' in number_keys:
        return 'leave_days'
    key = str(field.get('key') or '')
    if key in ('leave_period', 'date_range') and 'days' in number_keys:
        return 'days'
    return ''


def uses_half_day(field: dict, schema: dict | None = None) -> bool:
    props = field.get('props') or {}
    if props.get('halfDay') is True:
        return True
    if props.get('halfDay') is False:
        return False
    key = str(field.get('key') or '')
    if key == 'leave_period':
        return True
    if key == 'date_range' and auto_days_key_of(field, schema):
        return True
    return False


def uses_count_workdays(field: dict, schema: dict | None = None) -> bool:
    props = field.get('props') or {}
    if props.get('countWorkdays') is True:
        return True
    if props.get('countWorkdays') is False:
        return False
    return uses_half_day(field, schema)


def build_date_range_value(
    field: dict,
    raw: Any,
    schema: dict | None = None,
    *,
    company_id: int | None = None,
    user_id: int | None = None,
) -> dict | None:
    parsed = parse_date_range(raw)
    if not parsed:
        return None
    half = uses_half_day(field, schema)
    start_half = parsed.get('startHalf') or ('am' if half else None)
    end_half = parsed.get('endHalf') or ('pm' if half else None)
    checker = None
    if uses_count_workdays(field, schema):
        from app.services.holiday_calendar import is_workday_for, resolve_regions

        regions = tuple(resolve_regions(company_id=company_id, user_id=user_id))
        checker = lambda d, _r=regions: is_workday_for(d, _r)
    days = calc_range_days(
        parsed['start'],
        parsed['end'],
        start_half,
        end_half,
        half_day=half,
        is_workday=checker,
    )
    if days is None:
        return None
    out = {'start': parsed['start'], 'end': parsed['end'], 'days': days}
    if half:
        out['startHalf'] = start_half
        out['endHalf'] = end_half
    if checker:
        out['skipped'] = count_skipped_days(parsed['start'], parsed['end'], checker)
        out['count_workdays'] = True
    return out


def format_date_range_value(val: Any, *, half_day: bool = False) -> str:
    parsed = parse_date_range(val)
    if not parsed:
        return ''
    start = parsed['start']
    end = parsed['end']
    sh = parsed.get('startHalf')
    eh = parsed.get('endHalf')
    if half_day or sh or eh:
        left = f"{start} {HALF_LABELS_ZH.get(sh or 'am', '')}".strip()
        right = f"{end} {HALF_LABELS_ZH.get(eh or 'pm', '')}".strip()
        text = f'{left} ~ {right}'
    else:
        text = f'{start} ~ {end}'
    days = parsed.get('days')
    if days is None:
        days = calc_range_days(start, end, sh, eh, half_day=bool(half_day or sh or eh))
    if days is not None:
        days_text = str(int(days)) if float(days).is_integer() else str(days)
        text += f'（{days_text} 天）'
    return text


def apply_date_range_auto_days(
    schema: dict,
    data: dict | None,
    company_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    """规范化区间值，并把自动天数写回目标数字字段。"""
    form = data if isinstance(data, dict) else {}
    for sec in (schema or {}).get('sections') or []:
        for field in sec.get('fields') or []:
            if field.get('type') != 'date_range':
                continue
            key = field.get('key')
            if not key:
                continue
            built = build_date_range_value(
                field, form.get(key), schema, company_id=company_id, user_id=user_id,
            )
            if not built:
                continue
            form[key] = built
            days_key = auto_days_key_of(field, schema)
            if days_key:
                form[days_key] = built['days']
    return form
