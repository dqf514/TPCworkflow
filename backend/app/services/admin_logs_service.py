# -*- coding: utf-8 -*-
"""系统日志查询与删除（登录/访问、审批环节、邮件通知）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Query

from app.extensions import db
from app.models import InstanceTimeline, LoginAccessLog, NotificationLog, User, WorkflowDefinition, WorkflowInstance


def parse_log_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(val).strip()[:19], fmt)
        except ValueError:
            continue
    return None


def _param(params: dict | None, key: str, default: str = '') -> str:
    if params is None:
        return default
    return (params.get(key) or default).strip()


def build_login_access_query(params: dict | None = None) -> Query:
    category = _param(params, 'category')
    event_type = _param(params, 'event_type')
    status = _param(params, 'status')
    keyword = _param(params, 'keyword')
    date_from = parse_log_dt(_param(params, 'date_from') or None)
    date_to = parse_log_dt(_param(params, 'date_to') or None)

    q = LoginAccessLog.query
    if category == 'auth':
        q = q.filter(LoginAccessLog.log_category == 'auth')
    elif category == 'access':
        q = q.filter(
            LoginAccessLog.log_category == 'access',
            LoginAccessLog.event_type == 'page_view',
        )
    else:
        q = q.filter(
            db.or_(
                LoginAccessLog.log_category == 'auth',
                db.and_(
                    LoginAccessLog.log_category == 'access',
                    LoginAccessLog.event_type == 'page_view',
                ),
            ),
        )
    if event_type:
        q = q.filter(LoginAccessLog.event_type == event_type)
    if status in ('success', 'fail'):
        q = q.filter(LoginAccessLog.status == status)
    if date_from:
        q = q.filter(LoginAccessLog.created_at >= date_from)
    if date_to:
        q = q.filter(LoginAccessLog.created_at <= date_to)
    if keyword:
        like = f'%{keyword}%'
        q = q.filter(
            db.or_(
                LoginAccessLog.subject.ilike(like),
                LoginAccessLog.message.ilike(like),
                LoginAccessLog.request_path.ilike(like),
                LoginAccessLog.ip_address.ilike(like),
            ),
        )
    return q


def build_workflow_log_query(params: dict | None = None):
    action = _param(params, 'action')
    keyword = _param(params, 'keyword')
    date_from = parse_log_dt(_param(params, 'date_from') or None)
    date_to = parse_log_dt(_param(params, 'date_to') or None)

    q = (
        db.session.query(InstanceTimeline, WorkflowInstance, WorkflowDefinition, User)
        .join(WorkflowInstance, InstanceTimeline.instance_id == WorkflowInstance.id)
        .join(WorkflowDefinition, WorkflowInstance.definition_id == WorkflowDefinition.id)
        .outerjoin(User, InstanceTimeline.actor_id == User.id)
    )
    if action:
        q = q.filter(InstanceTimeline.action == action)
    if date_from:
        q = q.filter(InstanceTimeline.created_at >= date_from)
    if date_to:
        q = q.filter(InstanceTimeline.created_at <= date_to)
    if keyword:
        like = f'%{keyword}%'
        q = q.filter(
            db.or_(
                WorkflowInstance.display_no.ilike(like),
                WorkflowDefinition.name.ilike(like),
                User.display_name.ilike(like),
                User.username.ilike(like),
                InstanceTimeline.comment.ilike(like),
                InstanceTimeline.node_id.ilike(like),
            ),
        )
    return q


def build_notification_log_query(params: dict | None = None) -> Query:
    mail_type = _param(params, 'mail_type')
    channel = _param(params, 'channel')
    status = _param(params, 'status')
    keyword = _param(params, 'keyword')
    date_from = parse_log_dt(_param(params, 'date_from') or None)
    date_to = parse_log_dt(_param(params, 'date_to') or None)

    q = NotificationLog.query
    if mail_type:
        q = q.filter(NotificationLog.mail_type == mail_type)
    if channel:
        q = q.filter(NotificationLog.channel == channel)
    if status:
        q = q.filter(NotificationLog.status == status)
    if date_from:
        q = q.filter(NotificationLog.created_at >= date_from)
    if date_to:
        q = q.filter(NotificationLog.created_at <= date_to)
    if keyword:
        like = f'%{keyword}%'
        q = q.filter(
            db.or_(
                NotificationLog.recipient.ilike(like),
                NotificationLog.subject.ilike(like),
                NotificationLog.error_message.ilike(like),
            ),
        )
    return q


def _normalize_ids(raw) -> list[int]:
    if not raw:
        return []
    out: list[int] = []
    for item in raw:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out


def delete_login_access_logs(*, ids: list[int] | None = None, delete_all_filtered: bool = False, filters: dict | None = None) -> int:
    if delete_all_filtered:
        return build_login_access_query(filters).delete(synchronize_session=False)
    id_list = _normalize_ids(ids)
    if not id_list:
        return 0
    return LoginAccessLog.query.filter(LoginAccessLog.id.in_(id_list)).delete(synchronize_session=False)


def delete_workflow_logs(*, ids: list[int] | None = None, delete_all_filtered: bool = False, filters: dict | None = None) -> int:
    if delete_all_filtered:
        subq = build_workflow_log_query(filters).with_entities(InstanceTimeline.id).subquery()
        return InstanceTimeline.query.filter(InstanceTimeline.id.in_(subq)).delete(synchronize_session=False)
    id_list = _normalize_ids(ids)
    if not id_list:
        return 0
    return InstanceTimeline.query.filter(InstanceTimeline.id.in_(id_list)).delete(synchronize_session=False)


def delete_notification_logs(*, ids: list[int] | None = None, delete_all_filtered: bool = False, filters: dict | None = None) -> int:
    if delete_all_filtered:
        return build_notification_log_query(filters).delete(synchronize_session=False)
    id_list = _normalize_ids(ids)
    if not id_list:
        return 0
    return NotificationLog.query.filter(NotificationLog.id.in_(id_list)).delete(synchronize_session=False)
