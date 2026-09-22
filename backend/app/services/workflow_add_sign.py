# -*- coding: utf-8 -*-
"""审批加签：前加签（加签人先审，再回到原办理人）、后加签（原办理人先同意，再加签人审）。"""
from __future__ import annotations

import json
from datetime import datetime

from app.extensions import db
from app.models import TaskInstance, User
from app.services.graph_utils import find_node
from app.services.notify import notify_pending_tasks


def parse_task_meta(task: TaskInstance) -> dict:
    if not task.action_meta:
        return {}
    try:
        data = json.loads(task.action_meta)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def is_add_sign_task(meta: dict) -> bool:
    return bool(meta.get('add_sign'))


def user_display_names(user_ids: list[int]) -> str:
    names = []
    for uid in user_ids:
        u = User.query.get(uid)
        if u:
            names.append(u.display_label())
    return '、'.join(names) if names else '—'


def normalize_target_user_ids_for_node(
    actor_id: int,
    raw_ids: list,
    inst,
    node_id: str,
) -> list[int]:
    if not raw_ids:
        raise ValueError('请选择加签人')
    seen: set[int] = set()
    out: list[int] = []
    for x in raw_ids:
        try:
            uid = int(x)
        except (TypeError, ValueError):
            continue
        if uid in seen:
            continue
        seen.add(uid)
        if uid == actor_id:
            raise ValueError('不能加签给自己')
        u = User.query.get(uid)
        if not u or not u.is_active:
            raise ValueError(f'用户 #{uid} 不存在或已停用')
        exists = inst.tasks.filter_by(
            node_id=node_id,
            assignee_id=uid,
            status='pending',
        ).count()
        if exists:
            raise ValueError(f'{u.display_label()} 在本节点已有待办，无需重复加签')
        out.append(uid)
    if not out:
        raise ValueError('请选择有效的加签人')
    if len(out) > 20:
        raise ValueError('单次加签人数不能超过 20 人')
    return out


def create_add_sign_tasks(
    inst,
    node_id: str,
    node_type: str,
    mode: str,
    parent_task_id: int,
    requested_by: int,
    target_ids: list[int],
) -> list[int]:
    created: list[int] = []
    for uid in target_ids:
        t = TaskInstance(
            instance_id=inst.id,
            node_id=node_id,
            node_type=node_type,
            assignee_id=uid,
            status='pending',
            action_meta=json.dumps(
                {
                    'add_sign': True,
                    'add_sign_mode': mode,
                    'parent_task_id': parent_task_id,
                    'requested_by': requested_by,
                },
                ensure_ascii=False,
            ),
        )
        db.session.add(t)
        db.session.flush()
        created.append(t.id)
    return created


def all_add_sign_siblings_done(parent_task_id: int, mode: str) -> bool:
    for t in TaskInstance.query.filter_by(status='pending').all():
        meta = parse_task_meta(t)
        if (
            is_add_sign_task(meta)
            and meta.get('add_sign_mode') == mode
            and meta.get('parent_task_id') == parent_task_id
        ):
            return False
    return True


def pending_add_sign_child_ids(parent_task_id: int, mode: str) -> list[int]:
    ids: list[int] = []
    for t in TaskInstance.query.filter_by(status='pending').all():
        meta = parse_task_meta(t)
        if (
            is_add_sign_task(meta)
            and meta.get('parent_task_id') == parent_task_id
            and meta.get('add_sign_mode') == mode
        ):
            ids.append(t.id)
    return ids


def release_parent_after_before_sign(parent: TaskInstance) -> None:
    parent.status = 'pending'
    hold_meta = parse_task_meta(parent)
    hold_meta.pop('add_sign_hold', None)
    hold_meta.pop('add_sign_mode', None)
    hold_meta.pop('add_sign_child_ids', None)
    parent.action_meta = json.dumps(hold_meta, ensure_ascii=False) if hold_meta else None
    parent.completed_at = None


def mark_parent_after_sign_created(parent: TaskInstance, child_ids: list[int]) -> None:
    meta = parse_task_meta(parent)
    meta['add_sign_after_child_ids'] = child_ids
    parent.action_meta = json.dumps(meta, ensure_ascii=False)


def start_before_add_sign(
    task: TaskInstance,
    actor_id: int,
    target_ids: list[int],
    comment: str,
    append_timeline,
) -> list[int]:
    inst = task.instance
    names = user_display_names(target_ids)
    child_ids = create_add_sign_tasks(
        inst,
        task.node_id,
        task.node_type,
        'before',
        task.id,
        actor_id,
        target_ids,
    )
    task.status = 'on_hold'
    task.action_meta = json.dumps(
        {
            'add_sign_hold': True,
            'add_sign_mode': 'before',
            'add_sign_child_ids': child_ids,
            'original_assignee_id': actor_id,
        },
        ensure_ascii=False,
    )
    append_timeline(
        inst.id,
        actor_id,
        'add_sign',
        task.node_id,
        comment or f'前加签：{names}',
        payload={'mode': 'before', 'target_user_ids': target_ids, 'child_task_ids': child_ids},
    )
    db.session.flush()
    return child_ids


def cancel_other_or_sign_tasks(inst, graph: dict, node_id: str, keep_task_id: int) -> None:
    """或签节点：一人已同意并后加签时，取消同节点其他未处理的或签待办。"""
    node = find_node(graph, node_id)
    if not node:
        return
    apv_rel = (node.get('config') or {}).get('apv_rel') or node.get('apv_rel') or 'or'
    if apv_rel != 'or':
        return
    now = datetime.now()
    for t in inst.tasks.filter_by(node_id=node_id, status='pending').all():
        if t.id == keep_task_id:
            continue
        meta = parse_task_meta(t)
        if is_add_sign_task(meta):
            continue
        t.status = 'cancelled'
        t.completed_at = now


def start_after_add_sign(
    task: TaskInstance,
    actor_id: int,
    target_ids: list[int],
    comment: str,
    append_timeline,
    graph: dict | None = None,
) -> list[int]:
    inst = task.instance
    names = user_display_names(target_ids)
    if graph:
        cancel_other_or_sign_tasks(inst, graph, task.node_id, task.id)
    child_ids = create_add_sign_tasks(
        inst,
        task.node_id,
        task.node_type,
        'after',
        task.id,
        actor_id,
        target_ids,
    )
    mark_parent_after_sign_created(task, child_ids)
    append_timeline(
        inst.id,
        actor_id,
        'add_sign',
        task.node_id,
        comment or f'后加签：{names}',
        payload={'mode': 'after', 'target_user_ids': target_ids, 'child_task_ids': child_ids},
    )
    db.session.flush()
    return child_ids


def notify_task_ids(app, task_ids: list[int]) -> None:
    if task_ids:
        notify_pending_tasks(app, task_ids)
        try:
            from app.services.client_events import on_tasks_notified

            on_tasks_notified(task_ids)
        except Exception:
            pass
