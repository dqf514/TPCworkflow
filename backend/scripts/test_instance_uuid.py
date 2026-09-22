# -*- coding: utf-8 -*-
"""流程实例 UUID 访问与权限测试。"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from app.extensions import db
from app.models import User, WorkflowInstance
from app.services.instance_access import (
    ensure_instance_public_uuid,
    is_valid_public_uuid,
    resolve_instance_by_public_uuid,
    user_can_view_instance,
)
from scripts.upgrade_db import _ensure_columns


def test_uuid_backfill_and_resolve():
    inst = WorkflowInstance.query.order_by(WorkflowInstance.id.desc()).first()
    assert inst, '无流程实例'
    uid = ensure_instance_public_uuid(inst)
    db.session.commit()
    assert is_valid_public_uuid(uid)
    found = resolve_instance_by_public_uuid(uid)
    assert found and found.id == inst.id
    assert resolve_instance_by_public_uuid('999') is None
    assert resolve_instance_by_public_uuid('not-a-uuid') is None
    print('OK test_uuid_backfill_and_resolve')


def test_view_permission():
    inst = WorkflowInstance.query.order_by(WorkflowInstance.id.desc()).first()
    assert inst
    initiator = User.query.get(inst.initiator_id)
    from app.models import InstanceTimeline, TaskInstance

    involved = {inst.initiator_id}
    for t in inst.tasks.all():
        involved.add(t.assignee_id)
    for tl in InstanceTimeline.query.filter_by(instance_id=inst.id).all():
        if tl.actor_id:
            involved.add(tl.actor_id)
    other = (
        User.query.filter(
            User.is_active.is_(True),
            User.is_system_admin.is_(False),
            ~User.id.in_(involved),
        )
        .first()
    )
    if not other:
        print('SKIP test_view_permission (无独立测试用户)')
        return
    assert initiator and other
    assert user_can_view_instance(initiator, inst)
    assert not user_can_view_instance(other, inst)
    print('OK test_view_permission')


def main():
    app = create_app()
    with app.app_context():
        _ensure_columns()
        test_uuid_backfill_and_resolve()
        test_view_permission()
        print('ALL INSTANCE UUID TESTS PASSED')


if __name__ == '__main__':
    main()
