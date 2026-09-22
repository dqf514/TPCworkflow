# -*- coding: utf-8 -*-
"""法定假期日历 API。"""
from datetime import date

from flask import Blueprint, request
from flask_login import login_required

from app.services.holiday_calendar import (
    calendar_payload_for,
    parse_region_list,
    region_options,
    resolve_regions,
    resolve_user_regions,
)
from app.utils.response import fail, ok

holidays_api = Blueprint('holidays_api', __name__)


def _parse_iso(raw: str | None, fallback: date) -> date:
    text = str(raw or '').strip()[:10]
    if not text:
        return fallback
    try:
        return date.fromisoformat(text)
    except ValueError:
        return fallback


@holidays_api.route('/holidays/regions', methods=['GET'])
@login_required
def list_holiday_regions():
    return ok({'regions': region_options()})


@holidays_api.route('/holidays/calendar', methods=['GET'])
@login_required
def get_holiday_calendar():
    today = date.today()
    window_start = _parse_iso(request.args.get('from'), date(today.year, 1, 1))
    window_end = _parse_iso(request.args.get('to'), date(today.year + 1, 12, 31))
    if window_end < window_start:
        return fail('to 不能早于 from')
    if (window_end - window_start).days > 1200:
        return fail('查询跨度不能超过 1200 天')
    company_id = request.args.get('company_id', type=int)
    user_id = request.args.get('user_id', type=int)
    explicit = parse_region_list(request.args.get('regions') or request.args.get('region'))
    if explicit:
        regions = explicit
        source = 'explicit'
    else:
        regions = resolve_regions(company_id=company_id, user_id=user_id)
        source = 'user' if resolve_user_regions(user_id) else 'company'
    payload = calendar_payload_for(regions, window_start, window_end)
    payload['from'] = window_start.isoformat()
    payload['to'] = window_end.isoformat()
    payload['company_id'] = company_id
    payload['user_id'] = user_id
    payload['source'] = source
    return ok(payload)
