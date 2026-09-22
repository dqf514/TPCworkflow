# -*- coding: utf-8 -*-
"""公共日历 API。"""
from datetime import date

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import UserOrgMembership
from app.services.leave_calendar_service import (
    DEFAULT_FORM_KEYS,
    DEFAULT_LEAVE_TYPE_KEY,
    DEFAULT_PERIOD_KEYS,
    DEFAULT_STATUSES,
    query_leave_events,
    _split_csv,
    _viewer_can_see_all,
)
from app.utils.response import fail, ok

leave_calendar_api = Blueprint('leave_calendar_api', __name__)


def _parse_iso_date(raw: str | None, field_name: str) -> date | None:
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f'{field_name} 格式无效，请使用 YYYY-MM-DD')


def _resolve_company_id(explicit: int | None) -> int | None:
    if explicit:
        return explicit
    m = (
        UserOrgMembership.query.filter_by(user_id=current_user.id)
        .order_by(UserOrgMembership.is_primary.desc(), UserOrgMembership.id)
        .first()
    )
    return m.company_id if m else None


@leave_calendar_api.route('/leave-calendar/events', methods=['GET'])
@login_required
def list_leave_calendar_events():
    """聚合已通过流程中「同步到日历」的日期字段。"""
    try:
        window_start = _parse_iso_date(request.args.get('from'), 'from')
        window_end = _parse_iso_date(request.args.get('to'), 'to')
    except ValueError as exc:
        return fail(str(exc))

    if not window_start or not window_end:
        return fail('请提供 from / to 日期（YYYY-MM-DD）')
    if window_end < window_start:
        return fail('to 不能早于 from')
    if (window_end - window_start).days > 400:
        return fail('查询跨度不能超过 400 天')

    company_id = _resolve_company_id(request.args.get('company_id', type=int))
    department_id = request.args.get('department_id', type=int)
    form_keys = _split_csv(request.args.get('form_keys'), DEFAULT_FORM_KEYS)
    period_keys = _split_csv(request.args.get('period_field_keys'), DEFAULT_PERIOD_KEYS)
    leave_type_key = (request.args.get('leave_type_field_key') or DEFAULT_LEAVE_TYPE_KEY).strip()
    statuses = _split_csv(request.args.get('statuses'), DEFAULT_STATUSES)
    show_reason = str(request.args.get('show_reason') or '').lower() in ('1', 'true', 'yes')

    include_running = str(request.args.get('include_running') or '').lower() in ('1', 'true', 'yes')
    if include_running and 'running' not in statuses:
        statuses = list(statuses) + ['running']

    events = query_leave_events(
        viewer=current_user,
        window_start=window_start,
        window_end=window_end,
        company_id=company_id,
        department_id=department_id,
        form_keys=form_keys,
        period_keys=period_keys,
        leave_type_key=leave_type_key or DEFAULT_LEAVE_TYPE_KEY,
        statuses=statuses,
        show_reason=show_reason,
    )
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return ok({
        'events': events,
        'from': window_start.isoformat(),
        'to': window_end.isoformat(),
        'company_id': company_id,
        'count': len(events),
        'can_view_all': _viewer_can_see_all(current_user),
    })
