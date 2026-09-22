# -*- coding: utf-8 -*-
"""系统管理员：运行日志查询与删除。"""
from datetime import datetime, timedelta

from flask import Blueprint, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.models import (
    InstanceTimeline,
    LoginAccessLog,
    NotificationLog,
    User,
    WorkflowDefinition,
    WorkflowInstance,
)
from app.services.admin_logs_service import (
    build_login_access_query,
    build_notification_log_query,
    build_workflow_log_query,
    delete_login_access_logs,
    delete_notification_logs,
    delete_workflow_logs,
)
from app.services.instance_access import ensure_instance_public_uuid
from app.utils.datetime_fmt import format_display_datetime
from app.utils.response import fail, ok

admin_logs_api = Blueprint('admin_logs_api', __name__)

_EVENT_LABELS = {
    'login_success': '登录成功',
    'login_failed': '登录失败',
    'logout': '退出登录',
    'verify_email_sent': '发送邮箱验证码',
    'verify_sms_sent': '发送短信验证码',
    'api_access': '接口访问',
    'page_view': '打开页面',
    'add_sign': '加签',
}

_MAIL_TYPE_LABELS = {
    'login_code': '验证类 · 登录邮箱验证码',
    'sms_login': '验证类 · 登录短信验证码',
    'approval_notify': '通知类 · 审批待办提醒',
    'node_extra_email': '通知类 · 节点到达额外邮件',
    'node_extra_email_complete': '通知类 · 节点完成额外邮件',
    'instance_result': '通知类 · 审批结果通知申请人',
    'applicant_handler_prep': '通知类 · 办理前通知申请人交材料',
    'document_delivery': '通知类 · 单据投递（客户邮件）',
    'test': '测试类 · SMTP 测试邮件',
    'admin_confirm_code': '验证类 · 管理操作确认码',
}


def _require_admin():
    if not current_user.is_system_admin:
        return fail('无权限', status=403)
    return None


def _parse_page() -> tuple[int, int]:
    page = max(1, int(request.args.get('page', 1) or 1))
    page_size = min(100, max(10, int(request.args.get('page_size', 20) or 20)))
    return page, page_size


def _list_filters_from_request() -> dict:
    return {
        'category': request.args.get('category'),
        'event_type': request.args.get('event_type'),
        'status': request.args.get('status'),
        'keyword': request.args.get('keyword'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'action': request.args.get('action'),
        'mail_type': request.args.get('mail_type'),
        'channel': request.args.get('channel'),
    }


def _delete_body() -> tuple[dict, list[int], bool]:
    data = request.get_json(silent=True) or {}
    filters = data.get('filters') if isinstance(data.get('filters'), dict) else data
    ids = data.get('ids') or []
    delete_all = bool(data.get('delete_all_filtered'))
    return filters, ids, delete_all


@admin_logs_api.route('/logs/summary', methods=['GET'])
@login_required
def logs_summary():
    err = _require_admin()
    if err:
        return err
    since = datetime.now() - timedelta(hours=24)

    auth_success = LoginAccessLog.query.filter(
        LoginAccessLog.created_at >= since,
        LoginAccessLog.log_category == 'auth',
        LoginAccessLog.event_type == 'login_success',
    ).count()
    auth_failed = LoginAccessLog.query.filter(
        LoginAccessLog.created_at >= since,
        LoginAccessLog.log_category == 'auth',
        LoginAccessLog.event_type == 'login_failed',
    ).count()
    access_count = LoginAccessLog.query.filter(
        LoginAccessLog.created_at >= since,
        LoginAccessLog.event_type == 'page_view',
    ).count()
    workflow_count = InstanceTimeline.query.filter(InstanceTimeline.created_at >= since).count()

    email_sent = NotificationLog.query.filter(
        NotificationLog.created_at >= since,
        NotificationLog.status.in_(('sent', 'dev_log')),
    ).count()
    email_failed = NotificationLog.query.filter(
        NotificationLog.created_at >= since,
        NotificationLog.status == 'failed',
    ).count()

    recent_failures = (
        NotificationLog.query.filter(NotificationLog.status == 'failed')
        .order_by(NotificationLog.id.desc())
        .limit(5)
        .all()
    )

    return ok({
        'since': format_display_datetime(since),
        'auth_24h': {'success': auth_success, 'failed': auth_failed},
        'access_24h': access_count,
        'workflow_24h': workflow_count,
        'email_24h': {'sent': email_sent, 'failed': email_failed},
        'recent_email_failures': [
            {
                'id': r.id,
                'mail_type': r.mail_type,
                'mail_type_label': _MAIL_TYPE_LABELS.get(r.mail_type or '', r.mail_type or '—'),
                'recipient': r.recipient,
                'subject': r.subject,
                'error_message': r.error_message,
                'created_at': format_display_datetime(r.created_at),
            }
            for r in recent_failures
        ],
    })


@admin_logs_api.route('/logs/login-access', methods=['GET'])
@login_required
def list_login_access_logs():
    err = _require_admin()
    if err:
        return err
    page, page_size = _parse_page()
    q = build_login_access_query(_list_filters_from_request())

    total = q.count()
    rows = q.order_by(LoginAccessLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    user_ids = {r.user_id for r in rows if r.user_id}
    users = {u.id: u.display_label() for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

    items = []
    for r in rows:
        items.append({
            'id': r.id,
            'log_category': r.log_category,
            'event_type': r.event_type,
            'event_label': _EVENT_LABELS.get(r.event_type, r.event_type),
            'user_id': r.user_id,
            'user_name': users.get(r.user_id) if r.user_id else None,
            'subject': r.subject,
            'ip_address': r.ip_address,
            'user_agent': r.user_agent,
            'request_method': r.request_method,
            'request_path': r.request_path,
            'status': r.status,
            'message': r.message,
            'created_at': format_display_datetime(r.created_at),
        })

    return ok({'items': items, 'total': total, 'page': page, 'page_size': page_size})


@admin_logs_api.route('/logs/login-access/delete', methods=['POST'])
@login_required
def delete_login_access_logs_api():
    err = _require_admin()
    if err:
        return err
    filters, ids, delete_all = _delete_body()
    if not delete_all and not ids:
        return fail('请选择要删除的记录')
    deleted = delete_login_access_logs(ids=ids, delete_all_filtered=delete_all, filters=filters)
    db.session.commit()
    return ok({'deleted': deleted}, f'已删除 {deleted} 条登录/访问日志')


@admin_logs_api.route('/logs/workflow', methods=['GET'])
@login_required
def list_workflow_logs():
    err = _require_admin()
    if err:
        return err
    page, page_size = _parse_page()
    q = build_workflow_log_query(_list_filters_from_request())

    total = q.count()
    rows = (
        q.order_by(InstanceTimeline.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for tl, inst, defn, actor in rows:
        items.append({
            'id': tl.id,
            'instance_id': inst.id,
            'public_uuid': ensure_instance_public_uuid(inst),
            'display_no': inst.display_no or str(inst.id),
            'definition_name': defn.name,
            'instance_status': inst.status,
            'actor_id': tl.actor_id,
            'actor_name': actor.display_label() if actor else '系统',
            'action': tl.action,
            'node_id': tl.node_id,
            'comment': tl.comment,
            'created_at': format_display_datetime(tl.created_at),
        })

    return ok({'items': items, 'total': total, 'page': page, 'page_size': page_size})


@admin_logs_api.route('/logs/workflow/delete', methods=['POST'])
@login_required
def delete_workflow_logs_api():
    err = _require_admin()
    if err:
        return err
    filters, ids, delete_all = _delete_body()
    if not delete_all and not ids:
        return fail('请选择要删除的记录')
    deleted = delete_workflow_logs(ids=ids, delete_all_filtered=delete_all, filters=filters)
    db.session.commit()
    return ok({'deleted': deleted}, f'已删除 {deleted} 条审批环节记录')


@admin_logs_api.route('/logs/notifications', methods=['GET'])
@login_required
def list_notification_logs():
    err = _require_admin()
    if err:
        return err
    page, page_size = _parse_page()
    q = build_notification_log_query(_list_filters_from_request())

    total = q.count()
    rows = q.order_by(NotificationLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    user_ids = {r.user_id for r in rows if r.user_id}
    users = {u.id: u.display_label() for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

    items = []
    for r in rows:
        mt = r.mail_type or ''
        items.append({
            'id': r.id,
            'channel': r.channel,
            'mail_type': mt,
            'mail_type_label': _MAIL_TYPE_LABELS.get(mt, mt or '—'),
            'recipient': r.recipient,
            'user_id': r.user_id,
            'user_name': users.get(r.user_id) if r.user_id else None,
            'task_id': r.task_id,
            'instance_id': r.instance_id,
            'subject': r.subject,
            'body': r.body,
            'status': r.status,
            'error_message': r.error_message,
            'created_at': format_display_datetime(r.created_at),
        })

    return ok({'items': items, 'total': total, 'page': page, 'page_size': page_size})


@admin_logs_api.route('/logs/notifications/delete', methods=['POST'])
@login_required
def delete_notification_logs_api():
    err = _require_admin()
    if err:
        return err
    filters, ids, delete_all = _delete_body()
    if not delete_all and not ids:
        return fail('请选择要删除的记录')
    deleted = delete_notification_logs(ids=ids, delete_all_filtered=delete_all, filters=filters)
    db.session.commit()
    return ok({'deleted': deleted}, f'已删除 {deleted} 条邮件日志')


@admin_logs_api.route('/logs/notifications/stats', methods=['GET'])
@login_required
def notification_stats():
    err = _require_admin()
    if err:
        return err
    rows = (
        db.session.query(
            NotificationLog.mail_type,
            NotificationLog.status,
            func.count(NotificationLog.id),
        )
        .group_by(NotificationLog.mail_type, NotificationLog.status)
        .all()
    )
    return ok([
        {
            'mail_type': mt or 'unknown',
            'mail_type_label': _MAIL_TYPE_LABELS.get(mt or '', mt or '未分类'),
            'status': st,
            'count': cnt,
        }
        for mt, st, cnt in rows
    ])
