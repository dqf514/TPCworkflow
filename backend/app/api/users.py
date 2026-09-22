# -*- coding: utf-8 -*-
from flask import Blueprint, request
from flask_login import current_user, login_required

from app.extensions import db
from sqlalchemy import func
from app.models import Department, User, UserOrgMembership
from app.services.company_branding import get_primary_company
from app.services.org_service import ROLE_MANAGER, list_user_memberships, set_department_manager
from app.services.holiday_calendar import parse_region_list, serialize_region_list
from app.utils.response import fail, ok
from app.utils.user_utils import normalize_email, normalize_phone

users_api = Blueprint('users_api', __name__)


def _require_admin():
    if not current_user.is_system_admin:
        return fail('无权限', status=403)
    return None


def _apply_memberships(user_id: int, company_id: int, items: list) -> None:
    for item in items or []:
        dept_id = item.get('department_id')
        if not dept_id:
            continue
        dept = Department.query.filter_by(id=int(dept_id), company_id=company_id).first()
        if not dept:
            continue
        if UserOrgMembership.query.filter_by(
            user_id=user_id,
            company_id=company_id,
            department_id=dept.id,
        ).first():
            continue
        role = (item.get('role_in_dept') or 'member').strip()
        is_primary = bool(item.get('is_primary'))
        if is_primary:
            UserOrgMembership.query.filter_by(user_id=user_id).update({'is_primary': False})
        m = UserOrgMembership(
            user_id=user_id,
            company_id=company_id,
            department_id=dept.id,
            is_primary=is_primary,
            role_in_dept=role,
            job_title=(item.get('job_title') or '').strip() or None,
        )
        db.session.add(m)
        if role == ROLE_MANAGER:
            set_department_manager(company_id, dept.id, user_id)


def _user_detail(u: User) -> dict:
    return {
        'id': u.id,
        'username': u.username,
        'display_name': u.display_label(),
        'email': u.email,
        'phone': u.phone,
        'is_active': u.is_active,
        'is_system_admin': u.is_system_admin,
        'locale': u.locale or 'zh-CN',
        'holiday_regions': parse_region_list(getattr(u, 'holiday_regions', None)),
        'memberships': list_user_memberships(u.id),
    }


@users_api.route('', methods=['GET'])
@login_required
def list_users():
    err = _require_admin()
    if err:
        return err
    rows = User.query.order_by(User.id).all()
    return ok([
        {
            'id': u.id,
            'username': u.username,
            'display_name': u.display_label(),
            'email': u.email,
            'phone': u.phone,
            'is_active': u.is_active,
            'is_system_admin': u.is_system_admin,
            'holiday_regions': parse_region_list(getattr(u, 'holiday_regions', None)),
            'membership_count': UserOrgMembership.query.filter_by(user_id=u.id).count(),
        }
        for u in rows
    ])


@users_api.route('', methods=['POST'])
@login_required
def create_user():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    email = normalize_email(data.get('email'))
    if not username:
        return fail('请填写用户名')
    if not email:
        return fail('请填写邮箱')
    if User.query.filter_by(username=username).first():
        return fail('用户名已存在')
    if User.query.filter(db.func.lower(User.email) == email).first():
        return fail('该邮箱已被使用')
    u = User(
        username=username,
        display_name=data.get('display_name') or username,
        email=email,
        phone=normalize_phone(data.get('phone')) or None,
        is_system_admin=bool(data.get('is_system_admin')),
        locale=data.get('locale') or 'zh-CN',
        holiday_regions=serialize_region_list(data.get('holiday_regions')),
    )
    pwd = data.get('password') or 'ChangeMe123'
    u.set_password(pwd)
    db.session.add(u)
    db.session.flush()

    company = get_primary_company()
    memberships = data.get('memberships')
    if memberships is None and data.get('department_id'):
        memberships = [{
            'department_id': data.get('department_id'),
            'role_in_dept': data.get('role_in_dept') or 'member',
            'job_title': data.get('job_title'),
            'is_primary': bool(data.get('is_primary', True)),
        }]
    _apply_memberships(u.id, company.id, memberships or [])

    db.session.commit()
    return ok(_user_detail(u), '用户已创建')


@users_api.route('/<int:user_id>/memberships', methods=['POST'])
@login_required
def add_membership(user_id):
    err = _require_admin()
    if err:
        return err
    if not User.query.get(user_id):
        return fail('用户不存在', status=404)
    data = request.get_json(silent=True) or {}
    company = get_primary_company()
    company_id = int(data.get('company_id') or company.id)
    _apply_memberships(user_id, company_id, [data])
    db.session.commit()
    return ok(list_user_memberships(user_id), '任职已添加')


@users_api.route('/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    err = _require_admin()
    if err:
        return err
    u = User.query.get(user_id)
    if not u:
        return fail('用户不存在', status=404)
    return ok(_user_detail(u))


@users_api.route('/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    err = _require_admin()
    if err:
        return err
    u = User.query.get(user_id)
    if not u:
        return fail('用户不存在', status=404)
    data = request.get_json(silent=True) or {}
    if 'display_name' in data:
        u.display_name = (data.get('display_name') or '').strip() or u.username
    if 'phone' in data:
        u.phone = normalize_phone(data.get('phone')) or None
    if 'locale' in data:
        u.locale = data.get('locale') or 'zh-CN'
    if 'holiday_regions' in data:
        u.holiday_regions = serialize_region_list(data.get('holiday_regions'))
    if 'email' in data:
        email = normalize_email(data.get('email'))
        if not email:
            return fail('请填写邮箱')
        other = User.query.filter(func.lower(User.email) == email, User.id != user_id).first()
        if other:
            return fail('该邮箱已被使用')
        u.email = email
    if 'is_system_admin' in data:
        u.is_system_admin = bool(data.get('is_system_admin'))
    if 'is_active' in data:
        u.is_active = bool(data.get('is_active'))
    pwd = data.get('password')
    if pwd:
        u.set_password(str(pwd))
    db.session.commit()
    return ok(_user_detail(u), '用户已更新')


@users_api.route('/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    err = _require_admin()
    if err:
        return err
    if current_user.id == user_id:
        return fail('不能删除当前登录账号')
    u = User.query.get(user_id)
    if not u:
        return fail('用户不存在', status=404)
    u.is_active = False
    db.session.commit()
    return ok(message='用户已停用')


@users_api.route('/<int:user_id>/memberships/<int:membership_id>', methods=['DELETE'])
@login_required
def delete_membership(user_id, membership_id):
    err = _require_admin()
    if err:
        return err
    m = UserOrgMembership.query.filter_by(id=membership_id, user_id=user_id).first()
    if not m:
        return fail('任职记录不存在', status=404)
    db.session.delete(m)
    db.session.commit()
    return ok(message='已从该部门移除，账号保留')
