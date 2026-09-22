# -*- coding: utf-8 -*-
"""审批人解析：组织任职、部门负责人、流程角色。"""
import json

from app.extensions import db
from app.models import Department, FlowRole, FlowRoleMember, User, UserOrgMembership, WorkflowInstance
from app.services.org_service import (
    dept_manager_chain,
    get_department_root_id,
    get_manager_user_ids,
    get_parent_department_id,
)

# 流程角色编码：语义为「申请部门负责人」，按组织架构解析，而非 flow_role_members 静态名单
DEPT_MANAGER_FLOW_ROLE_CODES = frozenset({
    'dept_leader',
    'dept_manager',
    'department_head',
    'department_manager',
    'bmfzr',
})

DEPT_MANAGER_FLOW_ROLE_NAMES = frozenset({
    '部门负责人',
    '部门领导',
    'Department Head',
    'Department Manager',
})


def is_dept_manager_flow_role(code: str | None) -> bool:
    c = (code or '').strip()
    if not c:
        return False
    if c in DEPT_MANAGER_FLOW_ROLE_CODES:
        return True
    role = FlowRole.query.filter_by(code=c, is_active=True).first()
    return bool(role and (role.name or '').strip() in DEPT_MANAGER_FLOW_ROLE_NAMES)


def resolve_department_managers(instance: WorkflowInstance) -> list[int]:
    """按实例所选申请部门解析组织架构中的部门负责人。"""
    if not instance.department_id:
        return []
    dept = Department.query.get(instance.department_id)
    company_id = dept.company_id if dept else instance.company_id
    return get_manager_user_ids(company_id, instance.department_id)


def apply_dept_manager_skip_policy(
    instance: WorkflowInstance,
    manager_ids: list[int],
) -> tuple[list[int], bool, str | None]:
    """
    部门负责人节点跳过策略：
    - 无负责人 → 自动跳过
    - 仅发起人为负责人 → 自动跳过
    - 否则 → 指派负责人（若发起人在列表中则排除，避免自审）
    """
    if not manager_ids:
        return [], True, '本部门未设置负责人，已按设置自动通过'
    initiator = instance.initiator_id
    others = [uid for uid in manager_ids if uid != initiator]
    if not others:
        return [], True, '发起人为本部门负责人，已自动通过'
    return others, False, None


def is_dept_manager_assignee_config(config: dict | None) -> bool:
    cfg = config or {}
    at = cfg.get('assignee_type')
    if at == 'initiator_dept_manager':
        return True
    if at == 'dept_manager':
        return True
    if at == 'flow_role' and is_dept_manager_flow_role(cfg.get('flow_role_code')):
        return True
    return False


class AssigneeResolver:
    def __init__(self, instance: WorkflowInstance):
        self.instance = instance
        self.variables = {}
        if instance.variables:
            try:
                self.variables = json.loads(instance.variables)
            except (json.JSONDecodeError, TypeError):
                self.variables = {}

    def resolve(self, node_config: dict) -> list[int]:
        assignee_type = (node_config or {}).get('assignee_type', 'fixed_users')
        if assignee_type == 'fixed_users':
            return self._fixed_users(node_config)
        if assignee_type == 'initiator':
            return [self.instance.initiator_id]
        if assignee_type == 'flow_role':
            return self._flow_role(node_config)
        if assignee_type == 'dept_manager':
            return self._dept_manager_explicit(node_config)
        if assignee_type == 'initiator_dept_manager':
            return resolve_department_managers(self.instance)
        if assignee_type == 'parent_dept_manager':
            parent_id = get_parent_department_id(self.instance.department_id or 0)
            if not parent_id:
                return []
            return get_manager_user_ids(self.instance.company_id, parent_id)
        if assignee_type == 'dept_chain':
            return dept_manager_chain(
                self.instance.company_id,
                self.instance.department_id,
            )
        return []

    def _fixed_users(self, cfg: dict) -> list[int]:
        ids = cfg.get('user_ids') or []
        return [int(x) for x in ids if str(x).isdigit()]

    def _flow_role(self, cfg: dict) -> list[int]:
        code = cfg.get('flow_role_code')
        if not code:
            return []
        if is_dept_manager_flow_role(code):
            return resolve_department_managers(self.instance)
        company_id = cfg.get('company_id') or self.instance.company_id
        q = (
            db.session.query(FlowRoleMember.user_id)
            .join(FlowRole, FlowRoleMember.flow_role_id == FlowRole.id)
            .join(User, FlowRoleMember.user_id == User.id)
            .filter(
                FlowRole.code == code,
                FlowRole.is_active.is_(True),
                User.is_active.is_(True),
            )
        )
        q = q.filter(
            (FlowRoleMember.company_id.is_(None))
            | (FlowRoleMember.company_id == company_id),
        )
        return [row[0] for row in q.distinct().all()]

    def _dept_manager_explicit(self, cfg: dict) -> list[int]:
        dept_id = cfg.get('department_id') or self.instance.department_id
        if not dept_id:
            return []
        return get_manager_user_ids(self.instance.company_id, dept_id)


def user_can_start_definition(user: User, definition, company_id: int) -> bool:
    if definition.scope_type == 'global':
        return _user_in_company(user, company_id)
    if definition.scope_type == 'company':
        return definition.company_id == company_id and _user_in_company(user, company_id)
    if definition.scope_type == 'companies':
        try:
            ids = json.loads(definition.company_ids or '[]')
        except (json.JSONDecodeError, TypeError):
            ids = []
        return company_id in ids and _user_in_company(user, company_id)
    return False


def _user_in_company(user: User, company_id: int) -> bool:
    return user.org_memberships.filter_by(company_id=company_id).count() > 0


def user_department_options(
    user: User,
    company_id: int,
    org_unit_id: int | None = None,
) -> list[dict]:
    """发起申请时可选的部门（用户在该公司的任职部门）。"""
    from app.services.org_service import department_is_descendant_of

    rows = UserOrgMembership.query.filter_by(
        user_id=user.id,
        company_id=company_id,
    ).all()
    from app.models import Department

    out = []
    for m in rows:
        d = Department.query.get(m.department_id)
        if not d or not d.is_active:
            continue
        if org_unit_id is not None and not department_is_descendant_of(org_unit_id, d.id):
            continue
        label = d.name
        if m.role_in_dept == 'manager':
            label += '（负责人）'
        root_id = get_department_root_id(d.id)
        out.append({
            'department_id': d.id,
            'label': label,
            'role_in_dept': m.role_in_dept,
            'is_primary': m.is_primary,
            'org_unit_id': root_id,
        })
    return out
