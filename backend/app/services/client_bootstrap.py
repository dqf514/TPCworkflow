# -*- coding: utf-8 -*-
"""客户端启动聚合数据。"""
from __future__ import annotations

from datetime import datetime

from app.models import User
from app.services.company_branding import get_company_logo_url, get_company_name
from app.services.permissions import admin_capabilities
from app.services.task_list_meta import query_user_tasks, task_list_row
from app.utils.branding import APP_DISPLAY_NAME


def _nav_menu_for_user(user: User) -> list[dict]:
    caps = admin_capabilities(user)
    items = [
        {'key': 'dashboard', 'path': '/', 'label': '工作台'},
        {'key': 'apply', 'path': '/apply', 'label': '发起申请'},
        {'key': 'leave-calendar', 'path': '/leave-calendar', 'label': '日历'},
        {'key': 'my-instances', 'path': '/instances', 'label': '我的申请'},
        {'key': 'tasks', 'path': '/tasks', 'label': '待办审批'},
    ]
    if caps.get('is_global_admin'):
        items.append({'key': 'admin-org', 'path': '/admin/org', 'label': '组织架构'})
    if caps.get('can_design_workflow'):
        items.append({'key': 'admin-form-studio', 'path': '/admin/form-studio', 'label': '表单设计'})
    if caps.get('is_global_admin') or (
        caps.get('is_sector_admin') and caps.get('can_view_instances')
    ):
        items.append({
            'key': 'admin-sector-monitor',
            'path': '/admin/sector-monitor',
            'label': '板块监管',
        })
    if caps.get('is_global_admin') or caps.get('can_export_instances'):
        items.append({
            'key': 'admin-finance-export',
            'path': '/admin/finance-export',
            'label': '财务导出',
        })
    if caps.get('is_global_admin'):
        items.extend([
            {'key': 'admin-settings', 'path': '/admin/settings', 'label': '系统设置'},
            {'key': 'admin-logs', 'path': '/admin/logs', 'label': '审计日志'},
        ])
    return items


def build_client_bootstrap(user: User) -> dict:
    from app.api.auth import _user_payload
    from app.services.instance_progress import count_mine_unread_progress
    from app.models import TaskInstance, WorkflowInstance

    uid = user.id
    todo_count = TaskInstance.query.filter_by(assignee_id=uid, status='pending').count()
    participated_pending_count = (
        TaskInstance.query.join(
            WorkflowInstance,
            TaskInstance.instance_id == WorkflowInstance.id,
        )
        .filter(
            TaskInstance.assignee_id == uid,
            TaskInstance.status == 'pending',
            WorkflowInstance.initiator_id != uid,
        )
        .count()
    )
    badges = {
        'todo_count': todo_count,
        'participated_pending_count': participated_pending_count,
        'mine_unread_count': count_mine_unread_progress(uid),
    }
    q = query_user_tasks(uid, mode='todo')
    total = q.count()
    rows = q.limit(20).all()
    return {
        'user': _user_payload(user),
        'badges': badges,
        'todo_preview': {
            'items': [task_list_row(t) for t in rows],
            'total': total,
        },
        'nav_menu': _nav_menu_for_user(user),
        'branding': {
            'app_name': APP_DISPLAY_NAME,
            'company_name': get_company_name(),
            'company_logo_url': get_company_logo_url(),
        },
        'server_time': datetime.now().isoformat(timespec='seconds'),
    }
