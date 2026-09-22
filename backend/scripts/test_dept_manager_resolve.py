# -*- coding: utf-8 -*-
"""部门负责人解析与跳过策略自测（不依赖真实库时可跳过）。"""
from app import create_app
from app.services.assignee_resolver import (
    apply_dept_manager_skip_policy,
    is_dept_manager_flow_role,
    is_dept_manager_assignee_config,
)


def main() -> int:
    assert is_dept_manager_flow_role('dept_leader')
    assert is_dept_manager_flow_role('dept_manager')
    assert is_dept_manager_assignee_config(
        {'assignee_type': 'flow_role', 'flow_role_code': 'dept_leader'},
    )
    assert is_dept_manager_assignee_config({'assignee_type': 'initiator_dept_manager'})

    class Inst:
        initiator_id = 10

    assignees, skip, reason = apply_dept_manager_skip_policy(Inst(), [10])
    assert skip and assignees == [] and '发起人' in (reason or '')

    assignees, skip, reason = apply_dept_manager_skip_policy(Inst(), [])
    assert skip and '未设置负责人' in (reason or '')

    assignees, skip, _ = apply_dept_manager_skip_policy(Inst(), [20, 10])
    assert not skip and assignees == [20]

    print('test_dept_manager_resolve: ok')
    return 0


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        raise SystemExit(main())
