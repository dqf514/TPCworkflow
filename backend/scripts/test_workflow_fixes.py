# -*- coding: utf-8 -*-
"""工作流引擎修复验证：会签人数统计 + 驳回作废同实例待办。

运行：python scripts/test_workflow_fixes.py
（使用独立临时库，不污染开发数据）
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_TMP_DB = os.path.join(tempfile.gettempdir(), 'tpc_test_workflow_fixes.db').replace('\\', '/')
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ['DATABASE_URI'] = f'sqlite:///{_TMP_DB}'

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import TaskInstance, User, WorkflowDefinition, WorkflowInstance  # noqa: E402
from app.services.workflow_engine import WorkflowEngine  # noqa: E402
from app.services.workflow_settings import merge_settings  # noqa: E402
from scripts.bootstrap import ensure_bootstrap  # noqa: E402


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
    while len(others) < 2:
        new_u = User(
            username=f'test_fix_{int(time.time() * 1000)}_{len(others)}',
            display_name=f'测试用户{len(others) + 1}',
            email=f'test_fix_{len(others)}@local',
            is_active=True,
        )
        new_u.password_hash = 'x'
        db.session.add(new_u)
        db.session.commit()
        others.append(new_u)
    m = u1.org_memberships[0] if u1.org_memberships else None
    company_id = m.company_id if m else 1
    dept_id = m.department_id if m else None
    return u1, others[0], others[1], company_id, dept_id


def test_and_relation_counts_actual_approvers():
    """会签：离职审批人不再计入人数，在职审批人通过后流程应正常结束。"""
    engine = WorkflowEngine()
    a, b, _c, cid, did = _users()
    resigned = User.query.filter(User.id.notin_([a.id, b.id])).first()
    assert resigned is not None, '需要一个额外的离职用户'
    resigned.is_active = False
    db.session.commit()

    d = _create_def(
        'test_and_resigned',
        _simple_graph([a.id, resigned.id], apv_rel='and'),
        {'approver_resigned_action': 'auto_transfer'},
    )
    inst = engine.start(d, a.id, company_id=cid, department_id=did)
    task_a = inst.tasks.filter_by(assignee_id=a.id, status='pending').first()
    assert task_a is not None, '在职审批人应有待办'
    assert inst.tasks.filter_by(status='pending').count() == 1, '离职审批人不应产生待办'

    engine.complete_task(task_a, 'approve', a.id, comment='同意')
    inst = WorkflowInstance.query.get(inst.id)
    assert inst.status == 'approved', f'会签应结束，实际 {inst.status}'
    print('OK test_and_relation_counts_actual_approvers')


def test_reject_cancels_sibling_tasks():
    """驳回后：同实例其余待办必须作废，不能再被同意。"""
    engine = WorkflowEngine()
    a, b, _c, cid, did = _users()
    d = _create_def('test_reject_cancels', _simple_graph([a.id, b.id], apv_rel='or'))
    inst = engine.start(d, a.id, company_id=cid, department_id=did)
    task_a = inst.tasks.filter_by(assignee_id=a.id, status='pending').first()
    task_b = inst.tasks.filter_by(assignee_id=b.id, status='pending').first()
    assert task_a and task_b

    engine.complete_task(task_a, 'reject', a.id, comment='不符合要求')
    inst = WorkflowInstance.query.get(inst.id)
    assert inst.status == 'rejected', inst.status
    task_b = TaskInstance.query.get(task_b.id)
    assert task_b.status == 'cancelled', f'同伴待办应作废，实际 {task_b.status}'

    # 已作废的待办不能再被处理
    try:
        engine.complete_task(task_b, 'approve', b.id, comment='同意')
    except ValueError as exc:
        assert '已处理' in str(exc) or '已结束' in str(exc), str(exc)
    else:
        raise AssertionError('已作废的待办不应能被同意')

    # 实例已结束，其它遗留待办也不能再处理
    print('OK test_reject_cancels_sibling_tasks')


def test_finished_instance_blocks_stale_task():
    """实例结束后，遗留待办不可再被同意。"""
    engine = WorkflowEngine()
    a, b, _c, cid, did = _users()
    d = _create_def('test_stale_task', _simple_graph([a.id], apv_rel='or'))
    inst = engine.start(d, a.id, company_id=cid, department_id=did)
    task_a = inst.tasks.filter_by(assignee_id=a.id, status='pending').first()
    # 手工把实例标记为已结束，模拟遗留脏数据
    inst.status = 'rejected'
    db.session.commit()
    try:
        engine.complete_task(task_a, 'approve', a.id, comment='同意')
    except ValueError as exc:
        assert '已结束' in str(exc), str(exc)
    else:
        raise AssertionError('已结束的实例不应还能处理待办')
    print('OK test_finished_instance_blocks_stale_task')


def test_field_permission_blocks_mass_assignment():
    """审批人不得改写本节点未授予「可编辑」的表单字段（越权改金额入口）。"""
    engine = WorkflowEngine()
    a, b, _c, cid, did = _users()
    d = _create_def(
        'test_field_perm',
        {
            'nodes': [
                {'id': 'start', 'type': 'start'},
                {
                    'id': 'ap1',
                    'type': 'approver',
                    'config': {
                        'assignee_type': 'fixed_users',
                        'user_ids': [a.id],
                        'apv_rel': 'or',
                        'field_permissions': {'amount': 'edit', 'bank': 'view'},
                    },
                },
                {'id': 'end', 'type': 'end'},
            ],
            'edges': [
                {'source': 'start', 'target': 'ap1'},
                {'source': 'ap1', 'target': 'end'},
            ],
        },
    )
    inst = engine.start(d, a.id, company_id=cid, department_id=did)
    variables = json.loads(inst.variables or '{}')
    variables['form'] = {'amount': '100.00', 'bank': '6222xxxx'}
    inst.variables = json.dumps(variables, ensure_ascii=False)
    db.session.commit()

    task = inst.tasks.filter_by(assignee_id=a.id, status='pending').first()
    assert task is not None

    # 试图同时改金额与收款账号
    engine.complete_task(
        task, 'approve', a.id, comment='同意',
        form_update={'amount': '999.00', 'bank': 'HACKED'},
    )
    inst = WorkflowInstance.query.get(inst.id)
    form = (json.loads(inst.variables or '{}') or {}).get('form') or {}
    assert form.get('bank') == '6222xxxx', f'只读字段被改写：{form.get("bank")}'
    assert str(form.get('amount')) == '999.00', f'可编辑字段未生效：{form.get("amount")}'
    print('OK test_field_permission_blocks_mass_assignment')


def test_forbidden_editable_fields_reports_names():
    """显式只读的字段出现在提交里时，应能报出字段名。"""
    from app.services.node_field_requirements import forbidden_editable_fields

    cfg = {'field_permissions': {'amount': 'edit', 'bank': 'view'}}
    schema = {'sections': [{'fields': [
        {'key': 'amount', 'label': '报销金额'},
        {'key': 'bank', 'label': '收款账号'},
    ]}]}
    got = forbidden_editable_fields(cfg, {'amount': '1', 'bank': '2'}, schema)
    assert got == ['收款账号'], got
    assert forbidden_editable_fields(cfg, {'amount': '1'}, schema) == []
    print('OK test_forbidden_editable_fields_reports_names')


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        test_and_relation_counts_actual_approvers()
        test_reject_cancels_sibling_tasks()
        test_finished_instance_blocks_stale_task()
        test_field_permission_blocks_mass_assignment()
        test_forbidden_editable_fields_reports_names()
    if os.path.exists(_TMP_DB):
        try:
            os.remove(_TMP_DB)
        except OSError:
            pass
    print('ALL WORKFLOW FIX TESTS PASSED')
