# -*- coding: utf-8 -*-
"""法定假期 / 工作日：中国大陆含调休，其他地区为周末+公共假日。"""
from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache
from typing import Any, Sequence

DEFAULT_REGION = 'CN'

HOLIDAY_REGIONS: list[tuple[str, str, str]] = [
    ('CN', '中国大陆', 'Chinese Mainland'),
    ('HK', '中国香港', 'Hong Kong SAR'),
    ('MO', '中国澳门', 'Macao SAR'),
    ('TW', '中国台湾', 'Taiwan'),
    ('SG', '新加坡', 'Singapore'),
    ('MY', '马来西亚', 'Malaysia'),
    ('US', '美国', 'United States'),
    ('GB', '英国', 'United Kingdom'),
    ('JP', '日本', 'Japan'),
    ('KR', '韩国', 'South Korea'),
    ('AU', '澳大利亚', 'Australia'),
    ('NONE', '仅跳过周末', 'Weekends only'),
]

_VALID_CODES = {c for c, _, _ in HOLIDAY_REGIONS}

# holidays 库国家码（中国大陆不走此库，用 chinese_calendar 含调休）
_HOLIDAYS_COUNTRY = {
    'HK': 'HK',
    'MO': 'MO',
    'TW': 'TW',
    'SG': 'SG',
    'MY': 'MY',
    'US': 'US',
    'GB': 'GB',
    'JP': 'JP',
    'KR': 'KR',
    'AU': 'AU',
}


def coerce_region(code: Any) -> str | None:
    text = str(code or '').strip().upper().replace('_', '-')
    if not text:
        return None
    if text in ('CN', 'CN-CN', 'ZH-CN', 'CHINA', 'PRC'):
        return 'CN'
    if text in ('HK', 'CN-HK', 'ZH-HK'):
        return 'HK'
    if text in ('MO', 'CN-MO', 'ZH-MO'):
        return 'MO'
    if text in ('TW', 'CN-TW', 'ZH-TW'):
        return 'TW'
    if text in _VALID_CODES:
        return text
    return None


def normalize_region(code: Any) -> str:
    return coerce_region(code) or DEFAULT_REGION


def parse_region_list(raw: Any) -> list[str]:
    """解析多选地区；空表示未单独设置。"""
    items: list[Any] = []
    if raw is None or raw == '':
        items = []
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        text = str(raw).strip()
        if text.startswith('['):
            try:
                parsed = json.loads(text)
                items = parsed if isinstance(parsed, list) else [text]
            except (TypeError, ValueError, json.JSONDecodeError):
                items = [p.strip() for p in text.replace(';', ',').split(',') if p.strip()]
        else:
            items = [p.strip() for p in text.replace(';', ',').split(',') if p.strip()]
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        code = coerce_region(item)
        if not code or code in seen:
            continue
        seen.add(code)
        out.append(code)
    return out


def serialize_region_list(raw: Any) -> str:
    return ','.join(parse_region_list(raw))


def region_options() -> list[dict]:
    return [{'code': c, 'name': zh, 'name_en': en} for c, zh, en in HOLIDAY_REGIONS]


def region_names(codes: Sequence[str], *, english: bool = False) -> str:
    labels: list[str] = []
    for code in codes:
        for c, zh, en in HOLIDAY_REGIONS:
            if c == code:
                labels.append(en if english else zh)
                break
    return '、'.join(labels)


def resolve_company_region(company_id: int | None) -> str:
    if not company_id:
        return DEFAULT_REGION
    from app.models import Company

    row = Company.query.get(company_id)
    return normalize_region(getattr(row, 'holiday_region', None) if row else None)


def resolve_user_regions(user_id: int | None) -> list[str]:
    if not user_id:
        return []
    from app.models import User
    from app.extensions import db

    try:
        row = User.query.get(user_id)
        return parse_region_list(getattr(row, 'holiday_regions', None) if row else None)
    except Exception:
        db.session.rollback()
        return []


def resolve_regions(
    company_id: int | None = None,
    user_id: int | None = None,
) -> list[str]:
    own = resolve_user_regions(user_id)
    if own:
        return own
    return [resolve_company_region(company_id)]


def _cn_is_workday(d: date) -> bool:
    try:
        import chinese_calendar
        return bool(chinese_calendar.is_workday(d))
    except NotImplementedError:
        pass
    except Exception:
        pass
    if d in _country_holiday_set('CN', d.year):
        return False
    return d.weekday() < 5


@lru_cache(maxsize=32)
def _country_holiday_set(country: str, year: int) -> frozenset[date]:
    try:
        import holidays
    except ImportError:
        return frozenset()
    try:
        cal = holidays.country_holidays(country, years=year)
        return frozenset(cal.keys())
    except Exception:
        return frozenset()


def is_workday(d: date, region: str | None = None) -> bool:
    code = normalize_region(region)
    if code == 'NONE':
        return d.weekday() < 5
    if code == 'CN':
        return _cn_is_workday(d)
    country = _HOLIDAYS_COUNTRY.get(code)
    if country and d in _country_holiday_set(country, d.year):
        return False
    return d.weekday() < 5


def classify_day(d: date, region: str | None = None) -> str:
    """workday | holiday | weekend | makeup"""
    code = normalize_region(region)
    weekend = d.weekday() >= 5
    work = is_workday(d, code)
    if work and weekend:
        return 'makeup'
    if work:
        return 'workday'
    if weekend:
        return 'weekend'
    return 'holiday'


def is_workday_for(d: date, regions: Sequence[str] | None = None) -> bool:
    codes = [c for c in (regions or []) if c]
    if not codes:
        return is_workday(d, DEFAULT_REGION)
    if any(classify_day(d, c) == 'makeup' for c in codes):
        return True
    return all(is_workday(d, c) for c in codes)


_CN_EN_TO_ZH = {
    "New Year's Day": '元旦',
    'Spring Festival': '春节',
    'Tomb-sweeping Day': '清明节',
    'Labour Day': '劳动节',
    'Dragon Boat Festival': '端午节',
    'Mid-autumn Festival': '中秋节',
    'National Day': '国庆节',
}


def _short_zh(name: str) -> str:
    text = str(name or '').split('（')[0].split('(')[0].strip()
    if not text or text.startswith('休息日'):
        return ''
    return text


def _unique_join(parts: Sequence[str]) -> str:
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        text = str(part or '').strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return ' · '.join(out)


@lru_cache(maxsize=64)
def _holiday_name_pairs(country: str, year: int, language: str) -> tuple[tuple[str, str], ...]:
    try:
        import holidays
    except ImportError:
        return ()
    kwargs: dict[str, Any] = {'years': year}
    if language:
        kwargs['language'] = language
    try:
        cal = holidays.country_holidays(country, **kwargs)
        return tuple((k.isoformat(), str(v)) for k, v in cal.items())
    except Exception:
        if language:
            return _holiday_name_pairs(country, year, '')
        return ()


def _lookup_holiday_name(country: str, d: date, language: str) -> str:
    return dict(_holiday_name_pairs(country, d.year, language)).get(d.isoformat(), '')


def _cn_festival_en(d: date) -> str:
    try:
        import chinese_calendar
        _on, name = chinese_calendar.get_holiday_detail(d)
        return str(name or '').strip()
    except Exception:
        return ''


def region_day_title(d: date, region: str) -> tuple[str, str]:
    """返回 (中文名, 英文名)，无节日则为空。"""
    code = normalize_region(region)
    if code == 'NONE':
        return '', ''
    if code == 'CN':
        en = _cn_festival_en(d)
        zh = _short_zh(_lookup_holiday_name('CN', d, 'zh_CN')) or _CN_EN_TO_ZH.get(en, '')
        en_out = en or _lookup_holiday_name('CN', d, 'en_US') or _lookup_holiday_name('CN', d, '')
        return zh, en_out
    country = _HOLIDAYS_COUNTRY.get(code)
    if not country:
        return '', ''
    zh = _short_zh(_lookup_holiday_name(country, d, 'zh_CN'))
    en = _lookup_holiday_name(country, d, 'en_US') or _lookup_holiday_name(country, d, '')
    return zh or en, en


def build_calendar_marks(regions: Sequence[str], start: date, end: date) -> list[dict]:
    codes = [c for c in regions if c] or [DEFAULT_REGION]
    marks: list[dict] = []
    d = start
    while d <= end:
        work = is_workday_for(d, codes)
        weekend = d.weekday() >= 5
        zh_names: list[str] = []
        en_names: list[str] = []
        for code in codes:
            zh, en = region_day_title(d, code)
            if zh:
                zh_names.append(zh)
            if en:
                en_names.append(en)
        name_zh = _unique_join(zh_names)
        name_en = _unique_join(en_names)
        if work and weekend:
            kind = 'makeup'
            name_zh = f'调休·{name_zh}' if name_zh else '调休上班'
            name_en = f'Makeup · {name_en}' if name_en else 'Makeup workday'
        elif work:
            d += timedelta(days=1)
            continue
        elif name_zh or name_en:
            kind = 'holiday'
            name_zh = name_zh or '法定假'
            name_en = name_en or 'Public holiday'
        elif weekend:
            kind = 'weekend'
            name_zh = '周六' if d.weekday() == 5 else '周日'
            name_en = 'Saturday' if d.weekday() == 5 else 'Sunday'
        else:
            kind = 'holiday'
            name_zh = '法定假'
            name_en = 'Public holiday'
        marks.append({
            'date': d.isoformat(),
            'kind': kind,
            'name': name_zh,
            'name_en': name_en,
        })
        d += timedelta(days=1)
    return marks


def calendar_payload_for(regions: Sequence[str], start: date, end: date) -> dict:
    codes = [c for c in regions if c] or [DEFAULT_REGION]
    marks = build_calendar_marks(codes, start, end)
    holidays = [m['date'] for m in marks if m['kind'] == 'holiday']
    weekends = [m['date'] for m in marks if m['kind'] == 'weekend']
    makeup = [m['date'] for m in marks if m['kind'] == 'makeup']
    return {
        'region': ','.join(codes),
        'regions': codes,
        'region_name': region_names(codes),
        'region_name_en': region_names(codes, english=True),
        'off_days': sorted(set(holidays + weekends)),
        'holidays': holidays,
        'weekends': weekends,
        'makeup_workdays': makeup,
        'marks': marks,
    }


def calendar_payload(region: str, start: date, end: date) -> dict:
    return calendar_payload_for([normalize_region(region)], start, end)
