# -*- coding: utf-8 -*-
"""组织域：部门树、部门负责人、任职关系。"""
from __future__ import annotations

from app.extensions import db
from app.models import Department, User, UserOrgMembership
from app.services.company_branding import get_company_name

ROLE_MEMBER = 'member'
ROLE_MANAGER = 'manager'


def user_display_job_title(user_id: int) -> str | None:
    """用户对外展示的职务：优先主部门任职职务。"""
    rows = (
        UserOrgMembership.query.filter_by(user_id=user_id)
        .order_by(UserOrgMembership.is_primary.desc(), UserOrgMembership.id)
        .all()
    )
    for m in rows:
        title = (m.job_title or '').strip()
        if title:
            return title
    return None


def _same_level_department_query(
    company_id: int,
    name: str,
    parent_id: int | None,
    *,
    active_only: bool = True,
):
    q = Department.query.filter_by(company_id=company_id, name=name)
    if active_only:
        q = q.filter_by(is_active=True)
    if parent_id is None:
        q = q.filter(Department.parent_id.is_(None))
    else:
        q = q.filter_by(parent_id=parent_id)
    return q


def purge_inactive_same_level_departments(
    company_id: int,
    name: str,
    parent_id: int | None,
) -> int:
    """删除同级、同名且无子部门、无任职的停用部门，避免旧唯一约束或残留记录阻塞新建。"""
    removed = 0
    for d in _same_level_department_query(
        company_id, name, parent_id, active_only=False
    ).filter_by(is_active=False).all():
        if Department.query.filter_by(parent_id=d.id).first():
            continue
        if UserOrgMembership.query.filter_by(department_id=d.id).first():
            continue
        db.session.delete(d)
        removed += 1
    if removed:
        db.session.flush()
    return removed


def same_level_department_name_taken(
    company_id: int,
    name: str,
    parent_id: int | None,
    *,
    exclude_id: int | None = None,
    active_only: bool = True,
) -> bool:
    """同级（同一上级）下是否已有同名部门；不同上级允许同名。"""
    q = _same_level_department_query(company_id, name, parent_id, active_only=active_only)
    if exclude_id is not None:
        q = q.filter(Department.id != exclude_id)
    return q.first() is not None


def get_department_root_id(dept_id: int) -> int | None:
    """返回部门所属顶级组织（parent_id 为空的一级节点）ID。"""
    d = Department.query.get(dept_id)
    if not d:
        return None
    seen = set()
    while d.parent_id and d.parent_id not in seen:
        seen.add(d.id)
        parent = Department.query.get(d.parent_id)
        if not parent:
            break
        d = parent
    return d.id


def list_user_top_units(user_id: int, company_id: int) -> list[dict]:
    """用户可发起申请时选择的顶级组织（一级部门）。"""
    memberships = UserOrgMembership.query.filter_by(
        user_id=user_id,
        company_id=company_id,
    ).all()
    root_ids: set[int] = set()
    for m in memberships:
        d = Department.query.get(m.department_id)
        if not d or not d.is_active:
            continue
        root_id = get_department_root_id(d.id)
        if root_id:
            root_ids.add(root_id)
    if not root_ids:
        return []
    rows = (
        Department.query.filter(
            Department.id.in_(root_ids),
            Department.company_id == company_id,
            Department.is_active.is_(True),
        )
        .order_by(Department.sort_order, Department.id)
        .all()
    )
    return [{'id': d.id, 'name': d.name, 'sort_order': d.sort_order} for d in rows]


def department_is_descendant_of(ancestor_id: int, node_id: int) -> bool:
    """node_id 是否为 ancestor_id 本身或其下级部门。"""
    if node_id == ancestor_id:
        return True
    for child in Department.query.filter_by(parent_id=ancestor_id).all():
        if department_is_descendant_of(child.id, node_id):
            return True
    return False


def parse_parent_id(raw) -> int | None:
    """解析上级部门 ID（兼容前端 tree-select 的 dept-123 等形式）。"""
    if raw is None or raw == '':
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    if isinstance(raw, float):
        n = int(raw)
        return n if n > 0 else None
    s = str(raw).strip()
    if not s:
        return None
    if s.startswith('dept-'):
        try:
            n = int(s[5:])
            return n if n > 0 else None
        except ValueError:
            return None
    try:
        n = int(s)
        return n if n > 0 else None
    except ValueError:
        return None


def build_department_tree(company_id: int, include_inactive: bool = False) -> list[dict]:
    q = Department.query.filter_by(company_id=company_id)
    if not include_inactive:
        q = q.filter_by(is_active=True)
    depts = q.order_by(Department.sort_order, Department.id).all()
    id_set = {d.id for d in depts}
    by_parent: dict[int | None, list[Department]] = {}
    for d in depts:
        pid = d.parent_id
        if pid is not None and pid not in id_set:
            pid = None
        by_parent.setdefault(pid, []).append(d)

    def member_count(dept_id: int) -> int:
        return UserOrgMembership.query.filter_by(department_id=dept_id).count()

    def walk(parent_id: int | None) -> list[dict]:
        nodes = []
        for d in by_parent.get(parent_id) or []:
            mgr = get_department_manager_user(d.id)
            nodes.append({
                'id': d.id,
                'key': f'dept-{d.id}',
                'value': d.id,
                'title': d.name,
                'name': d.name,
                'parent_id': d.parent_id,
                'sort_order': d.sort_order,
                'is_active': d.is_active,
                'member_count': member_count(d.id),
                'manager': mgr,
                'children': walk(d.id),
            })
        return nodes

    return walk(None)


def get_department_manager_user(dept_id: int) -> dict | None:
    m = (
        UserOrgMembership.query.filter_by(
            department_id=dept_id,
            role_in_dept=ROLE_MANAGER,
        )
        .first()
    )
    if not m:
        return None
    u = User.query.get(m.user_id)
    if not u:
        return None
    return {'user_id': u.id, 'display_name': u.display_label(), 'membership_id': m.id}


def get_manager_user_ids(company_id: int, dept_id: int | None) -> list[int]:
    if not dept_id:
        return []
    dept = Department.query.get(dept_id)
    if dept:
        company_id = dept.company_id
    rows = UserOrgMembership.query.filter_by(
        company_id=company_id,
        department_id=dept_id,
        role_in_dept=ROLE_MANAGER,
    ).all()
    return [r.user_id for r in rows]


def get_parent_department_id(dept_id: int) -> int | None:
    d = Department.query.get(dept_id)
    return d.parent_id if d else None


def dept_manager_chain(company_id: int, dept_id: int | None) -> list[int]:
    """从当前部门向上，依次收集各部门负责人（去重）。"""
    seen: set[int] = set()
    chain: list[int] = []
    current = dept_id
    while current:
        for uid in get_manager_user_ids(company_id, current):
            if uid not in seen:
                seen.add(uid)
                chain.append(uid)
        current = get_parent_department_id(current)
    return chain


def set_department_manager(company_id: int, dept_id: int, user_id: int) -> UserOrgMembership:
    """指定部门负责人；同部门原负责人降为成员。"""
    UserOrgMembership.query.filter_by(
        department_id=dept_id,
        role_in_dept=ROLE_MANAGER,
    ).update({UserOrgMembership.role_in_dept: ROLE_MEMBER})
    m = UserOrgMembership.query.filter_by(
        user_id=user_id,
        company_id=company_id,
        department_id=dept_id,
    ).first()
    if not m:
        m = UserOrgMembership(
            user_id=user_id,
            company_id=company_id,
            department_id=dept_id,
            role_in_dept=ROLE_MANAGER,
            is_primary=False,
        )
        db.session.add(m)
    else:
        m.role_in_dept = ROLE_MANAGER
    db.session.flush()
    return m


def build_department_path(department_id: int, company_label: str | None = None) -> str:
    """生成「公司 / 一级 / 二级」路径，用于成员多部门展示。"""
    label = company_label or get_company_name()
    parts: list[str] = []
    current_id: int | None = department_id
    seen: set[int] = set()
    while current_id and current_id not in seen:
        seen.add(current_id)
        d = Department.query.get(current_id)
        if not d:
            break
        parts.insert(0, d.name)
        current_id = d.parent_id
    if not parts:
        return label
    return f'{label} / {" / ".join(parts)}'


def build_department_path_under_org(
    department_id: int | None,
    org_unit_id: int | None = None,
) -> str:
    """
    申请部门展示路径：仅含组织节点以下的层级，不与「组织」字段重复拼接公司名。
    向上遍历到 org_unit_id（含该节点时停止，不把组织名再拼进路径）。
    """
    if not department_id:
        return ''
    dept = Department.query.get(department_id)
    if not dept:
        return ''
    if org_unit_id and department_id == org_unit_id:
        return dept.name

    parts: list[str] = []
    current_id: int | None = department_id
    seen: set[int] = set()
    while current_id and current_id not in seen:
        seen.add(current_id)
        d = Department.query.get(current_id)
        if not d:
            break
        if org_unit_id and current_id == org_unit_id:
            break
        parts.insert(0, d.name)
        current_id = d.parent_id

    cleaned: list[str] = []
    for name in parts:
        if cleaned and cleaned[-1] == name:
            continue
        cleaned.append(name)
    if not cleaned:
        return dept.name
    return ' / '.join(cleaned)


def list_user_memberships(user_id: int) -> list[dict]:
    rows = UserOrgMembership.query.filter_by(user_id=user_id).order_by(
        UserOrgMembership.is_primary.desc(),
        UserOrgMembership.id,
    ).all()
    out = []
    for m in rows:
        dept = Department.query.get(m.department_id)
        out.append({
            'membership_id': m.id,
            'company_id': m.company_id,
            'department_id': m.department_id,
            'department_name': dept.name if dept else None,
            'department_path': build_department_path(m.department_id),
            'is_primary': m.is_primary,
            'role_in_dept': m.role_in_dept or ROLE_MEMBER,
            'job_title': m.job_title,
        })
    return out


def list_department_members(dept_id: int) -> list[dict]:
    rows = UserOrgMembership.query.filter_by(department_id=dept_id).all()
    rows.sort(key=lambda m: (0 if (m.role_in_dept or ROLE_MEMBER) == ROLE_MANAGER else 1, m.id))
    out = []
    for m in rows:
        u = User.query.get(m.user_id)
        if not u:
            continue
        out.append({
            'membership_id': m.id,
            'user_id': u.id,
            'username': u.username,
            'display_name': u.display_label(),
            'email': u.email,
            'phone': u.phone,
            'role_in_dept': m.role_in_dept or ROLE_MEMBER,
            'job_title': m.job_title,
            'is_primary': m.is_primary,
            'is_active': u.is_active,
            'membership_count': UserOrgMembership.query.filter_by(user_id=u.id).count(),
        })
    return out
