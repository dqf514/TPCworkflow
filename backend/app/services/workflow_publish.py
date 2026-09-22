# -*- coding: utf-8 -*-
"""流程发布状态：新发起与既有实例的访问规则。"""
from __future__ import annotations

from app.models import WorkflowDefinition, WorkflowInstance

ACTIVE_INSTANCE_STATUSES = ('draft', 'running')


def definition_allows_new_application(definition: WorkflowDefinition | None) -> bool:
    """是否允许新用户发起申请或保存新草稿。"""
    return bool(definition and definition.status == 'published')


def definition_allows_existing_instance(
    definition: WorkflowDefinition | None,
    instance: WorkflowInstance | None = None,
) -> bool:
    """是否允许继续处理已存在的流程实例（含草稿提交、审批流转、详情查看）。"""
    if not definition:
        return False
    if definition.status == 'published':
        return True
    return instance is not None and instance.definition_id == definition.id
