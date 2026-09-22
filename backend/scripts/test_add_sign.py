# -*- coding: utf-8 -*-
"""加签全流程测试：前加签、后加签、驳回、或签节点、未开启加签。"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from app.extensions import db
from app.models import TaskInstance, User, WorkflowDefinition, WorkflowInstance
from app.services.workflow_engine import WorkflowEngine
from app.services.workflow_settings import merge_settings
from scripts.bootstrap import ensure_bootstrap
from scripts.upgrade_db import _ensure_columns


def _simple_graph(assignee_ids: list[int], apv_rel: str = 'or') -> dict:
    return {
        'nodes': [
            {'id': 'start', 'type': 'start'},
            {
                'id': 'ap1',
                'type': 'approver',
                'config': {
                    'assignee_type': 'fixed_users',
                    'user_ids': assignee_ids,
                    'apv_rel': apv_rel,
                },
            },
            {'id': 'end', 'type': 'end'},
        ],
        'edges': [
            {'source': 'start', 'target': 'ap1'},
            {'source': 'ap1', 'target': 'end'},
        ],
    }


def _create_def(key: str, graph: dict, settings: dict | None = None) -> WorkflowDefinition:
    key = f'{key}_{int(time.time() * 1000)}'
    s = merge_settings(json.dumps(settings or {}))
    d = WorkflowDefinition(
        key=key,
        name=key,
        version=1,
        status='published',
        scope_type='global',
        process_graph=json.dumps(graph, ensure_ascii=False),
        settings=json.dumps(s, ensure_ascii=False),
        form_schema=json.dumps({'fields': []}, ensure_ascii=False),
    )
    db.session.add(d)
    db.session.flush()
    return d


def _users() -> tuple[User, User, User, int, int | None]:
    ensure_bootstrap()
    u1 = User.query.filter_by(username='admin').first() or User.query.first()
    others = User.query.filter(User.id != u1.id, User.is_active.is_(True)).limit(2).all()
    if len(others) < 2:
        raise RuntimeError('需要至少 3 个活跃用户')
    m = u1.org_memberships[0] if u1.org_memberships else None
    company_id = m.company_id if m else 1
    dept_id = m.department_id if m else None
    return u1, others[0], others[1], company_id, dept_id


def _pending_for(inst: WorkflowInstance, uid: int) -> TaskInstance | None:
    return inst.tasks.filter_by(assignee_id=uid, status='pending').first()


def test_before_add_sign():
    engine = WorkflowEngine()
    a, b, c, cid, did = _users()
    d = _create_def(
        'test_add_sign_before',
        _simple_graph([a.id]),
        {'allow_add_sign': True, 'require_comment': False, 'require_handwritten_sign': False},
    )
    inst = engine.start(d, a.id, company_id=cid, department_id=did)
    task_a = _pending_for(inst, a.id)
    assert task_a and task_a.status == 'pending'

    engine.complete_task(
        task_a,
        'add_sign',
        a.id,
        comment='请协助前加签',
        action_meta={'mode': 'before', 'target_user_ids': [b.id]},
    )
    task_a = TaskInstance.query.get(task_a.id)
    assert task_a.status == 'on_hold'
    task_b = _pending_for(inst, b.id)
    assert task_b and task_b.action_meta and 'add_sign' in task_b.action_meta
    assert _pending_for(inst, a.id) is None

    engine.complete_task(task_b, 'approve', b.id, comment='加签同意')
    task_a = TaskInstance.query.get(task_a.id)
    assert task_a.status == 'pending'
    engine.complete_task(task_a, 'approve', a.id, comment='本人同意')
    inst = WorkflowInstance.query.get(inst.id)
    assert inst.status == 'approved', inst.status
    print('OK test_before_add_sign')


def test_after_add_sign():
    engine = WorkflowEngine()
    a, b, c, cid, did = _users()
    d = _create_def(
        'test_add_sign_after',
        _simple_graph([a.id]),
        {'allow_add_sign': True, 'require_comment': False},
    )
    inst = engine.start(d, a.id, company_id=cid, department_id=did)
    task_a = _pending_for(inst, a.id)
    engine.complete_task(
        task_a,
        'approve',
        a.id,
        comment='同意后加签',
        action_meta={'add_sign_mode': 'after', 'target_user_ids': [c.id]},
    )
    inst = WorkflowInstance.query.get(inst.id)
    assert inst.status == 'running'
    task_c = _pending_for(inst, c.id)
    assert task_c
    engine.complete_task(task_c, 'approve', c.id, comment='后加签同意')
    inst = WorkflowInstance.query.get(inst.id)
    assert inst.status == 'approved'
    print('OK test_after_add_sign')


def test_add_sign_reject():
    engine = WorkflowEngine()
    a, b, _, cid, did = _users()
    d = _create_def(
        'test_add_sign_reject',
        _simple_graph([a.id]),
        {'allow_add_sign': True, 'require_comment': False},
    )
    inst = engine.start(d, a.id, company_id=cid, department_id=did)
    task_a = _pending_for(inst, a.id)
    engine.complete_task(
        task_a,
        'add_sign',
        a.id,
        action_meta={'mode': 'before', 'target_user_ids': [b.id]},
    )
    task_b = _pending_for(inst, b.id)
    engine.complete_task(task_b, 'reject', b.id, comment='不同意')
    inst = WorkflowInstance.query.get(inst.id)
    assert inst.status == 'rejected'
    print('OK test_add_sign_reject')


def test_or_sign_with_after():
    engine = WorkflowEngine()
    a, b, c, cid, did = _users()
    d = _create_def(
        'test_add_sign_or',
        _simple_graph([a.id, b.id], apv_rel='or'),
        {'allow_add_sign': True, 'require_comment': False},
    )
    inst = engine.start(d, a.id, company_id=cid, department_id=did)
    task_a = _pending_for(inst, a.id)
    engine.complete_task(
        task_a,
        'approve',
        a.id,
        action_meta={'add_sign_mode': 'after', 'target_user_ids': [c.id]},
    )
    inst = WorkflowInstance.query.get(inst.id)
    assert inst.status == 'running'
    assert _pending_for(inst, c.id)
    engine.complete_task(_pending_for(inst, c.id), 'approve', c.id)
    inst = WorkflowInstance.query.get(inst.id)
    assert inst.status == 'approved'
    print('OK test_or_sign_with_after')


def test_disabled_add_sign():
    engine = WorkflowEngine()
    a, b, _, cid, did = _users()
    d = _create_def(
        'test_add_sign_off',
        _simple_graph([a.id]),
        {'allow_add_sign': False},
    )
    inst = engine.start(d, a.id, company_id=cid, department_id=did)
    task_a = _pending_for(inst, a.id)
    try:
        engine.complete_task(
            task_a,
            'add_sign',
            a.id,
            action_meta={'mode': 'before', 'target_user_ids': [b.id]},
        )
        raise AssertionError('应拒绝未开启加签')
    except ValueError as e:
        assert '加签' in str(e)
    print('OK test_disabled_add_sign')


def main():
    app = create_app()
    with app.app_context():
        _ensure_columns()
        test_disabled_add_sign()
        test_before_add_sign()
        test_after_add_sign()
        test_add_sign_reject()
        test_or_sign_with_after()
        print('ALL ADD_SIGN TESTS PASSED')


if __name__ == '__main__':
    main()
