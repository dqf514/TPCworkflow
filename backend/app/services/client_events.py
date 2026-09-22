# -*- coding: utf-8 -*-
"""客户端 SSE 事件总线（内存队列，仅服务桌面客户端，不影响 Web）。"""
from __future__ import annotations

import json
import queue
import threading
from typing import Any

_lock = threading.Lock()
_subscribers: dict[int, list[queue.Queue]] = {}


def subscribe(user_id: int) -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=100)
    with _lock:
        _subscribers.setdefault(user_id, []).append(q)
    return q


def unsubscribe(user_id: int, q: queue.Queue) -> None:
    with _lock:
        rows = _subscribers.get(user_id) or []
        if q in rows:
            rows.remove(q)
        if not rows:
            _subscribers.pop(user_id, None)


def emit_event(user_id: int, event_type: str, data: dict[str, Any] | None = None) -> None:
    payload = {
        'type': event_type,
        'data': data or {},
    }
    with _lock:
        targets = list(_subscribers.get(user_id) or [])
    for q in targets:
        try:
            q.put_nowait(payload)
        except queue.Full:
            pass


def emit_badge_changed(user_ids: set[int] | list[int]) -> None:
    for uid in set(user_ids):
        if uid:
            emit_event(uid, 'badge.changed', {})


def on_tasks_notified(task_ids: list[int]) -> None:
    """待办邮件通知后，向相关用户推送客户端事件。"""
    if not task_ids:
        return
    from app.models import TaskInstance
    from app.services.task_list_meta import task_list_row

    user_ids: set[int] = set()
    for tid in task_ids:
        task = TaskInstance.query.get(tid)
        if not task or not task.assignee_id:
            continue
        user_ids.add(task.assignee_id)
        emit_event(
            task.assignee_id,
            'task.assigned',
            {'task': task_list_row(task)},
        )
    emit_badge_changed(user_ids)


def on_users_touched(user_ids: set[int] | list[int]) -> None:
    emit_badge_changed(user_ids)
