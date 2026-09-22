# -*- coding: utf-8 -*-
from flask import Blueprint, request
from flask_login import current_user, login_required

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Company, Department, FlowRoleMember, User, UserOrgMembership, WorkflowInstance
from app.services.assignee_resolver import user_department_options
from app.services.company_branding import get_company_name, get_primary_company, sync_company_name
from app.services.org_service import (
    ROLE_MANAGER,
    build_department_tree,
    list_department_members,
    list_user_memberships,
    list_user_top_units,
    department_is_descendant_of,
    parse_parent_id,
    purge_inactive_same_level_departments,
    same_level_department_name_taken,
    set_department_manager,
)
from app.services.holiday_calendar import normalize_region
from app.utils.response import fail, ok

org_api = Blueprint('org_api', __name__)


def _require_admin():
    if not current_user.is_system_admin:
        return fail('无权限', status=403)
    return None


@org_api.route('/primary', methods=['GET'])
@login_required
def primary_company():
    company = get_primary_company()
    return ok({
        'id': company.id,
        'name': get_company_name(),
        'code': company.code,
        'holiday_region': getattr(company, 'holiday_region', None) or 'CN',
    })


@org_api.route('/companies', methods=['GET'])
@login_required
def list_companies():
    q = Company.query
    if not (request.args.get('all') and current_user.is_system_admin):
        q = q.filter_by(is_active=True)
    rows = q.order_by(Company.sort_order, Company.id).all()
    return ok([_company_dict(c) for c in rows])


@org_api.route('/companies', methods=['POST'])
@login_required
def create_company():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return fail('请填写公司名称')
    if Company.query.filter_by(name=name).first():
        return fail('该公司已存在')
    c = Company(
        name=name,
        code=(data.get('code') or '').strip() or None,
        sort_order=int(data.get('sort_order') or 0),
        holiday_region=normalize_region(data.get('holiday_region')),
    )
    db.session.add(c)
    db.session.commit()
    return ok(_company_dict(c), '公司已创建')


@org_api.route('/companies/<int:company_id>', methods=['PUT'])
@login_required
def update_company(company_id):
    err = _require_admin()
    if err:
        return err
    c = Company.query.get(company_id)
    if not c:
        return fail('公司不存在', status=404)
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return fail('请填写公司名称')
        other = Company.query.filter(Company.id != company_id, Company.name == name).first()
        if other:
            return fail('该公司名称已存在')
        c.name = name
        if c.code == 'SYSTEM':
            sync_company_name(name)
    if 'code' in data:
        c.code = (data.get('code') or '').strip() or None
    if 'sort_order' in data:
        c.sort_order = int(data.get('sort_order') or 0)
    if 'is_active' in data:
        c.is_active = bool(data.get('is_active'))
    if 'holiday_region' in data:
        c.holiday_region = normalize_region(data.get('holiday_region'))
    db.session.commit()
    return ok(_company_dict(c), '公司已更新')


@org_api.route('/companies/<int:company_id>', methods=['DELETE'])
@login_required
def delete_company(company_id):
    err = _require_admin()
    if err:
        return err
    c = Company.query.get(company_id)
    if not c:
        return fail('公司不存在', status=404)
    running = WorkflowInstance.query.filter_by(
        company_id=company_id,
        status='running',
    ).count()
    if running:
        return fail('该公司仍有进行中的流程实例，无法删除')
    if UserOrgMembership.query.filter_by(company_id=company_id).first():
        return fail('该公司下仍有成员任职，请先移除成员并停用子部门')
    c.is_active = False
    Department.query.filter_by(company_id=company_id).update({'is_active': False})
    db.session.commit()
    return ok(message='公司已停用')


@org_api.route('/companies/<int:company_id>/departments', methods=['GET'])
@login_required
def list_departments(company_id):
    q = Department.query.filter_by(company_id=company_id)
    if not (request.args.get('all') and current_user.is_system_admin):
        q = q.filter_by(is_active=True)
    rows = q.order_by(Department.sort_order, Department.id).all()
    return ok([_department_dict(d) for d in rows])


@org_api.route('/companies/<int:company_id>/departments', methods=['POST'])
@login_required
def create_department(company_id):
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return fail('请填写部门名称')
    if not Company.query.get(company_id):
        return fail('公司不存在', status=404)
    parent_id = parse_parent_id(data.get('parent_id'))
    if parent_id:
        parent = Department.query.filter_by(
            id=parent_id,
            company_id=company_id,
            is_active=True,
        ).first()
        if not parent:
            return fail('上级部门不存在或已停用')
    purge_inactive_same_level_departments(company_id, name, parent_id)
    if same_level_department_name_taken(company_id, name, parent_id):
        return fail(f'该上级下已存在同名部门「{name}」')
    d = Department(
        company_id=company_id,
        name=name,
        parent_id=parent_id,
        sort_order=int(data.get('sort_order') or 0),
    )
    db.session.add(d)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        purge_inactive_same_level_departments(company_id, name, parent_id)
        if same_level_department_name_taken(company_id, name, parent_id):
            return fail(f'该上级下已存在同名部门「{name}」')
        return fail(
            '无法创建部门：数据库仍使用旧版「全公司部门名唯一」约束，'
            '请在服务器执行 python scripts/upgrade_db.py 后重试',
        )
    return ok(_department_dict(d), '部门已创建')


@org_api.route('/companies/<int:company_id>/departments/<int:dept_id>', methods=['PUT'])
@login_required
def update_department(company_id, dept_id):
    err = _require_admin()
    if err:
        return err
    d = Department.query.filter_by(id=dept_id, company_id=company_id).first()
    if not d:
        return fail('部门不存在', status=404)
    data = request.get_json(silent=True) or {}
    new_name = d.name
    new_parent_id = d.parent_id
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return fail('请填写部门名称')
        new_name = name
    if 'parent_id' in data:
        parent_id = parse_parent_id(data.get('parent_id'))
        if parent_id:
            parent = Department.query.filter_by(
                id=parent_id,
                company_id=company_id,
                is_active=True,
            ).first()
            if not parent:
                return fail('上级部门不存在或已停用')
            if parent_id == dept_id:
                return fail('上级部门不能为自身')
            if department_is_descendant_of(dept_id, parent_id):
                return fail('上级部门不能为本部门或其子部门')
        new_parent_id = parent_id
    purge_inactive_same_level_departments(company_id, new_name, new_parent_id)
    if same_level_department_name_taken(
        company_id,
        new_name,
        new_parent_id,
        exclude_id=dept_id,
    ):
        return fail(f'该上级下已存在同名部门「{new_name}」')
    if 'name' in data:
        d.name = new_name
    if 'parent_id' in data:
        d.parent_id = new_parent_id
    if 'sort_order' in data:
        d.sort_order = int(data.get('sort_order') or 0)
    if 'is_active' in data:
        d.is_active = bool(data.get('is_active'))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail(f'该上级下已存在同名部门「{new_name}」')
    return ok(_department_dict(d), '部门已更新')


@org_api.route('/companies/<int:company_id>/departments/<int:dept_id>', methods=['DELETE'])
@login_required
def delete_department(company_id, dept_id):
    err = _require_admin()
    if err:
        return err
    d = Department.query.filter_by(id=dept_id, company_id=company_id).first()
    if not d:
        return fail('部门不存在', status=404)
    if Department.query.filter_by(parent_id=dept_id).first():
        return fail('该部门下仍有子部门，请先删除子部门')
    UserOrgMembership.query.filter_by(department_id=dept_id).delete()
    WorkflowInstance.query.filter_by(department_id=dept_id).update({'department_id': None})
    FlowRoleMember.query.filter_by(department_id=dept_id).update({'department_id': None})
    db.session.delete(d)
    db.session.commit()
    return ok(message='部门已删除')


@org_api.route('/memberships/<int:membership_id>', methods=['DELETE'])
@login_required
def delete_membership(membership_id):
    err = _require_admin()
    if err:
        return err
    m = UserOrgMembership.query.get(membership_id)
    if not m:
        return fail('任职记录不存在', status=404)
    db.session.delete(m)
    db.session.commit()
    return ok(message='已从该部门移除，账号保留')


@org_api.route('/memberships/<int:membership_id>/primary', methods=['PUT'])
@login_required
def set_primary_membership(membership_id):
    err = _require_admin()
    if err:
        return err
    m = UserOrgMembership.query.get(membership_id)
    if not m:
        return fail('任职记录不存在', status=404)
    UserOrgMembership.query.filter_by(user_id=m.user_id).update({'is_primary': False})
    m.is_primary = True
    db.session.commit()
    return ok(message='已设为主部门')


@org_api.route('/tree', methods=['GET'])
@login_required
def org_tree():
    companies = Company.query.filter_by(is_active=True).order_by(Company.sort_order).all()
    out = []
    for c in companies:
        depts = Department.query.filter_by(company_id=c.id, is_active=True).order_by(
            Department.sort_order,
        ).all()
        out.append({
            'id': c.id,
            'name': c.name,
            'departments': [
                {'id': d.id, 'name': d.name, 'parent_id': d.parent_id}
                for d in depts
            ],
        })
    return ok(out)


@org_api.route('/companies/<int:company_id>/structure', methods=['GET'])
@login_required
def company_structure(company_id):
    c = Company.query.get(company_id)
    if not c:
        return fail('公司不存在', status=404)
    include_inactive = bool(request.args.get('all') and current_user.is_system_admin)
    return ok({
        'company': {**_company_dict(c), 'name': get_company_name()},
        'tree': build_department_tree(company_id, include_inactive=include_inactive),
    })


@org_api.route('/users/<int:user_id>/memberships', methods=['GET'])
@login_required
def user_memberships(user_id):
    err = _require_admin()
    if err:
        return err
    if not User.query.get(user_id):
        return fail('用户不存在', status=404)
    return ok(list_user_memberships(user_id))


@org_api.route('/companies/<int:company_id>/departments/<int:dept_id>/members', methods=['GET'])
@login_required
def department_members(company_id, dept_id):
    d = Department.query.filter_by(id=dept_id, company_id=company_id).first()
    if not d:
        return fail('部门不存在', status=404)
    return ok(list_department_members(dept_id))


@org_api.route('/companies/<int:company_id>/departments/<int:dept_id>/members', methods=['POST'])
@login_required
def add_department_member(company_id, dept_id):
    err = _require_admin()
    if err:
        return err
    d = Department.query.filter_by(id=dept_id, company_id=company_id).first()
    if not d:
        return fail('部门不存在', status=404)
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    if not user_id:
        return fail('请选择用户')
    if UserOrgMembership.query.filter_by(
        user_id=user_id,
        company_id=company_id,
        department_id=dept_id,
    ).first():
        return fail('该用户已在本部门任职')
    role = (data.get('role_in_dept') or 'member').strip()
    job_title = (data.get('job_title') or '').strip() or None
    if role == ROLE_MANAGER:
        m = set_department_manager(company_id, dept_id, int(user_id))
        if job_title:
            m.job_title = job_title
        db.session.commit()
        return ok(_membership_dict(m), '已添加并设为部门负责人')
    m = UserOrgMembership(
        user_id=int(user_id),
        company_id=company_id,
        department_id=dept_id,
        role_in_dept=role,
        is_primary=bool(data.get('is_primary')),
        job_title=job_title,
    )
    db.session.add(m)
    db.session.commit()
    return ok(_membership_dict(m), '成员已添加')


@org_api.route('/memberships/<int:membership_id>', methods=['PUT'])
@login_required
def update_membership(membership_id):
    err = _require_admin()
    if err:
        return err
    m = UserOrgMembership.query.get(membership_id)
    if not m:
        return fail('任职记录不存在', status=404)
    data = request.get_json(silent=True) or {}
    if 'job_title' in data:
        m.job_title = (data.get('job_title') or '').strip() or None
    if 'is_primary' in data:
        m.is_primary = bool(data.get('is_primary'))
    if 'role_in_dept' in data:
        role = (data.get('role_in_dept') or 'member').strip()
        if role == ROLE_MANAGER:
            set_department_manager(m.company_id, m.department_id, m.user_id)
        else:
            m.role_in_dept = role
    db.session.commit()
    return ok(_membership_dict(m), '已更新')


@org_api.route('/top-units', methods=['GET'])
@login_required
def top_units():
    """组织架构一级节点，作为发起申请时的「发起公司」选项。"""
    company_id = request.args.get('company_id', type=int)
    if not company_id:
        primary = get_primary_company()
        company_id = primary.id
    units = list_user_top_units(current_user.id, company_id)
    return ok(units)


@org_api.route('/departments/resolve', methods=['GET'])
@login_required
def resolve_department_labels():
    """按部门 ID 批量返回展示路径（表单查看/打印解析部门名称）。"""
    from app.services.org_service import build_department_path

    raw = (request.args.get('ids') or '').strip()
    if not raw:
        return ok({})
    ids: list[int] = []
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    if not ids:
        return ok({})
    rows = Department.query.filter(Department.id.in_(ids)).all()
    out = {str(d.id): build_department_path(d.id) for d in rows}
    return ok(out)


@org_api.route('/my-departments', methods=['GET'])
@login_required
def my_departments():
    company_id = request.args.get('company_id', type=int)
    if not company_id:
        return fail('请指定公司')
    org_unit_id = request.args.get('org_unit_id', type=int)
    return ok(user_department_options(current_user, company_id, org_unit_id=org_unit_id))


@org_api.route('/search', methods=['GET'])
@login_required
def search_org():
    q = (request.args.get('q') or '').strip()
    company_id = request.args.get('company_id', type=int)
    if not q or not company_id:
        return ok({'users': [], 'departments': []})
    like = f'%{q}%'
    users = (
        User.query.filter(User.is_active.is_(True))
        .filter(
            or_(
                User.username.like(like),
                User.display_name.like(like),
            ),
        )
        .limit(20)
        .all()
    )
    depts = (
        Department.query.filter_by(company_id=company_id, is_active=True)
        .filter(Department.name.like(like))
        .limit(20)
        .all()
    )
    return ok({
        'users': [
            {'id': u.id, 'display_name': u.display_label(), 'username': u.username}
            for u in users
        ],
        'departments': [{'id': d.id, 'name': d.name} for d in depts],
    })


@org_api.route('/memberships', methods=['GET'])
@login_required
def list_memberships():
    user_id = request.args.get('user_id', type=int)
    q = UserOrgMembership.query
    if user_id:
        q = q.filter_by(user_id=user_id)
    rows = q.order_by(UserOrgMembership.id).all()
    return ok([_membership_dict(m) for m in rows])


def _company_dict(c: Company) -> dict:
    return {
        'id': c.id,
        'code': c.code,
        'name': c.name,
        'sort_order': c.sort_order,
        'is_active': c.is_active,
        'holiday_region': getattr(c, 'holiday_region', None) or 'CN',
    }


def _department_dict(d: Department) -> dict:
    return {
        'id': d.id,
        'company_id': d.company_id,
        'parent_id': d.parent_id,
        'name': d.name,
        'sort_order': d.sort_order,
        'is_active': d.is_active,
    }


def _membership_dict(m: UserOrgMembership) -> dict:
    return {
        'id': m.id,
        'user_id': m.user_id,
        'company_id': m.company_id,
        'department_id': m.department_id,
        'is_primary': m.is_primary,
        'role_in_dept': getattr(m, 'role_in_dept', None) or 'member',
        'job_title': m.job_title,
    }
