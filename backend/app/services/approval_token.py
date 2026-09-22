# -*- coding: utf-8 -*-
"""邮件审批链接：签名令牌，用于快速同意/驳回（无需先登录）。"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from app.extensions import db
from app.models import TaskEmailToken, TaskInstance
from app.services.workflow_settings import merge_settings


TOKEN_TTL_DAYS = 7


def can_quick_action(task: TaskInstance, action: str) -> bool:
    """流程要求意见或签名时，邮件内不提供快速操作按钮。"""
    if task.status != 'pending':
        return False
    definition = task.instance.definition if task.instance else None
    if not definition:
        return action == 'view'
    settings = merge_settings(definition.settings)
    if settings.get('require_comment'):
        return False
    if action == 'approve' and settings.get('require_handwritten_sign'):
        return False
    if (
        action == 'approve'
        and task.node_type == 'handler'
        and settings.get('require_handler_comment')
    ):
        return False
    return action in ('approve', 'reject')


def create_task_email_token(task: TaskInstance, action: str) -> str | None:
    if not can_quick_action(task, action):
        return None
    token = secrets.token_urlsafe(32)
    row = TaskEmailToken(
        token=token,
        task_id=task.id,
        assignee_id=task.assignee_id,
        action=action,
        expires_at=datetime.now() + timedelta(days=TOKEN_TTL_DAYS),
    )
    db.session.add(row)
    db.session.flush()
    return token


def get_valid_token(token_str: str, *, action: str | None = None) -> TaskEmailToken | None:
    raw = (token_str or '').strip()
    if not raw:
        return None
    row = TaskEmailToken.query.filter_by(token=raw).first()
    if not row or row.used_at or row.expires_at < datetime.now():
        return None
    if action and row.action != action:
        return None
    task = TaskInstance.query.get(row.task_id)
    if not task or task.status != 'pending' or task.assignee_id != row.assignee_id:
        return None
    if not can_quick_action(task, row.action):
        return None
    return row


def mark_token_used(row: TaskEmailToken) -> None:
    row.used_at = datetime.now()
