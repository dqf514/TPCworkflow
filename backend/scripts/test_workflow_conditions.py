# -*- coding: utf-8 -*-
"""条件分支与多路径流程引擎测试。"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from app.extensions import db
from app.models import User, WorkflowDefinition, WorkflowInstance
from app.services.graph_utils import eval_condition, resolve_next_node_ids
from app.services.workflow_engine import WorkflowEngine
from scripts.bootstrap import ensure_bootstrap
from scripts.upgrade_db import _ensure_columns


def _graph_amount_branches(threshold_low: float, threshold_high: float) -> dict:
    """模拟垂直设计器导出：金额三路径 + 汇合抄送。"""
    return {
        'nodes': [
            {'id': 'start', 'type': 'start'},
            {
                'id': 'cond_amount',
                'type': 'condition',
                'config': {'title': '金额条件'},
                'branches': [
                    {
                        'label': '十万以下',
                        'priority': 1,
                        'expr': {'field': 'form.amount', 'op': 'lt', 'value': threshold_low},
                        'target': 'approve_dept',
                    },
                    {
                        'label': '一百万以上',
                        'priority': 2,
                        'expr': {'field': 'form.amount', 'op': 'gte', 'value': threshold_high},
                        'target': 'approve_gm',
                    },
                    {
                        'label': '默认条件',
                        'priority': 99,
                        'expr': 'default',
                        'target': 'approve_mgr',
                    },
                ],
            },
            {'id': 'approve_dept', 'type': 'approver', 'config': {'assignee_type': 'initiator', 'apv_rel': 'or'}},
            {'id': 'approve_gm', 'type': 'approver', 'config': {'assignee_type': 'initiator', 'apv_rel': 'or'}},
            {'id': 'approve_mgr', 'type': 'approver', 'config': {'assignee_type': 'initiator', 'apv_rel': 'or'}},
            {'id': 'cc_fin', 'type': 'cc', 'config': {'assignee_type': 'initiator'}},
            {'id': 'end', 'type': 'end'},
        ],
        'edges': [
            {'source': 'start', 'target': 'cond_amount'},
            {'source': 'approve_dept', 'target': 'cc_fin'},
            {'source': 'approve_gm', 'target': 'cc_fin'},
            {'source': 'approve_mgr', 'target': 'cc_fin'},
            {'source': 'cc_fin', 'target': 'end'},
        ],
    }


def test_eval_condition_switch():
    variables = {'form': {'need_extra': True}}
    assert eval_condition(
        {'field': 'form.need_extra', 'op': 'eq', 'value': True},
        variables,
    )
    assert eval_condition(
        {'field': 'form.need_extra', 'op': 'eq', 'value': 'true'},
        variables,
    )
    assert not eval_condition(
        {'field': 'form.need_extra', 'op': 'eq', 'value': False},
        variables,
    )
    variables['form']['need_extra'] = False
    assert eval_condition(
        {'field': 'form.need_extra', 'op': 'eq', 'value': 'false'},
        variables,
    )


def test_eval_condition_unit():
    variables = {'form': {'amount': 50000, 'days': 5}}
    assert eval_condition({'field': 'form.amount', 'op': 'lt', 'value': 100000}, variables)
    assert not eval_condition({'field': 'form.amount', 'op': 'gte', 'value': 1000000}, variables)
    assert eval_condition('default', variables)
    variables['form']['amount'] = 1500000
    assert eval_condition({'field': 'form.amount', 'op': 'gte', 'value': 1000000}, variables)


def test_resolve_next_node_ids_paths():
    graph = _graph_amount_branches(100000, 1000000)
    low = resolve_next_node_ids(graph, 'cond_amount', {'form': {'amount': 20000}})
    assert low == ['approve_dept'], low
    mid = resolve_next_node_ids(graph, 'cond_amount', {'form': {'amount': 500000}})
    assert mid == ['approve_mgr'], mid
    high = resolve_next_node_ids(graph, 'cond_amount', {'form': {'amount': 2000000}})
    assert high == ['approve_gm'], high


def test_engine_start_assigns_expected_first_task():
    app = create_app()
    with app.app_context():
        _ensure_columns()
        ensure_bootstrap()
        from app.models import Company, UserOrgMembership

        admin = User.query.filter_by(username='admin').first()
        assert admin
        mem = UserOrgMembership.query.filter_by(user_id=admin.id).first()
        company_id = mem.company_id if mem else (Company.query.first().id if Company.query.first() else 1)

        for amount, expected_node in (
            (30000, 'approve_dept'),
            (500000, 'approve_mgr'),
            (3000000, 'approve_gm'),
        ):
            wf = WorkflowDefinition(
                key=f'test_cond_{amount}',
                name=f'条件测试{amount}',
                version=1,
                status='published',
                scope_type='global',
                process_graph=json.dumps(_graph_amount_branches(100000, 1000000), ensure_ascii=False),
            )
            db.session.add(wf)
            db.session.flush()
            engine = WorkflowEngine()
            inst = engine.start(
                wf,
                initiator_id=admin.id,
                company_id=company_id,
                variables={'form': {'amount': amount}},
            )
            pending = inst.tasks.filter_by(status='pending').all()
            assert len(pending) == 1, (amount, [t.node_id for t in pending])
            assert pending[0].node_id == expected_node, (amount, pending[0].node_id)
            db.session.delete(inst)
            db.session.delete(wf)
        db.session.commit()
        print('engine path tests: OK')


def main() -> int:
    test_eval_condition_switch()
    print('eval_condition switch: OK')
    test_eval_condition_unit()
    print('eval_condition unit: OK')
    test_resolve_next_node_ids_paths()
    print('resolve_next_node_ids: OK')
    test_engine_start_assigns_expected_first_task()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
