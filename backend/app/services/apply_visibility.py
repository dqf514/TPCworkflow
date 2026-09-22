# -*- coding: utf-8 -*-
"""流程发起可见范围：按部门/人员限制可填报用户。"""
from __future__ import annotations

from app.models import User, UserOrgMembership
from app.services.assignee_resolver import user_can_start_definition
from app.services.org_service import department_is_descendant_of
from app.services.workflow_settings import merge_settings

APPLY_VISIBILITY_ALL = 'all'
APPLY_VISIBILITY_RESTRICTED = 'restricted'


def user_can_apply_workflow(user: User, definition, company_id: int) -> bool:
    """是否可在指定公司下发起该流程（含公司范围与部门/人员可见范围）。"""
    if not user or not definition:
        return False
    if not user_can_start_definition(user, definition, company_id):
        return False
    if getattr(user, 'is_system_admin', False):
        return True
    settings = merge_settings(definition.settings)
    mode = settings.get('apply_visibility_mode') or APPLY_VISIBILITY_ALL
    if mode != APPLY_VISIBILITY_RESTRICTED:
        return True
    dept_ids = _norm_int_list(settings.get('visible_department_ids'))
    user_ids = _norm_int_list(settings.get('visible_user_ids'))
    if not dept_ids and not user_ids:
        return False
    if user.id in user_ids:
        return True
    if dept_ids:
        memberships = UserOrgMembership.query.filter_by(
            user_id=user.id,
            company_id=company_id,
        ).all()
        for m in memberships:
            user_dept = m.department_id
            if not user_dept:
                continue
            for visible_dept in dept_ids:
                if department_is_descendant_of(int(visible_dept), int(user_dept)):
                    return True
    return False


def apply_visibility_summary(settings: dict | None = None) -> str:
    """设计端展示用摘要。"""
    merged = merge_settings(None)
    if isinstance(settings, dict):
        merged.update(settings)
    mode = merged.get('apply_visibility_mode') or APPLY_VISIBILITY_ALL
    if mode != APPLY_VISIBILITY_RESTRICTED:
        return '全员可发起'
    dept_n = len(_norm_int_list(merged.get('visible_department_ids')))
    user_n = len(_norm_int_list(merged.get('visible_user_ids')))
    if not dept_n and not user_n:
        return '已限制（未配置部门或人员，仅系统管理员可发起）'
    parts = []
    if dept_n:
        parts.append(f'{dept_n} 个部门')
    if user_n:
        parts.append(f'{user_n} 人')
    return '指定范围：' + '、'.join(parts)


def _norm_int_list(raw) -> list[int]:
    if not raw:
        return []
    if not isinstance(raw, (list, tuple)):
        return []
    out: list[int] = []
    for x in raw:
        try:
            n = int(x)
        except (TypeError, ValueError):
            continue
        if n > 0 and n not in out:
            out.append(n)
    return out
