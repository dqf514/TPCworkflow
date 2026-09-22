# -*- coding: utf-8 -*-
import base64
import os
import re
from datetime import datetime

from flask import Blueprint, current_app, request
from flask_login import current_user, login_required

from app.extensions import db
import json

from app.models import BusinessSector, FlowRole, FlowRoleMember, SystemSetting, User, UserScopedAdmin
from app.services.flow_role_service import (
    add_flow_role_member as svc_add_flow_role_member,
    flow_role_dict,
    flow_role_member_dict,
    set_flow_role_members,
    set_user_flow_roles,
)
from app.services.company_branding import (
    BRANDING_UPLOAD_SUBDIR,
    SETTING_COMPANY_NAME,
    clear_company_logo,
    get_company_logo_url,
    get_company_name,
    resolve_logo_abs_path,
    set_company_logo_path,
    sync_company_name,
)
from app.services.admin_confirm_code import (
    PURPOSE_DELETE_WORKFLOW_INSTANCE,
    send_admin_email_confirm_code,
    verify_admin_email_confirm_code,
)
from app.services.admin_workflow_instances import (
    admin_instance_row,
    purge_workflow_instance,
    query_admin_workflow_instances,
    resolve_admin_instance_ref,
)
from app.services.notify import MAIL_CONFIG_KEYS, send_test_email
from app.utils.response import fail, ok

admin_api = Blueprint('admin_api', __name__)

_SETTING_KEYS = (
    SETTING_COMPANY_NAME,
    'MAIL_SERVER',
    'MAIL_PORT',
    'MAIL_USE_TLS',
    'MAIL_USE_SSL',
    'MAIL_USERNAME',
    'MAIL_PASSWORD',
    'MAIL_DEFAULT_SENDER',
    'SMS_GATEWAY_URL',
    'SMS_API_KEY',
    'AZURE_TENANT_ID',
    'AZURE_CLIENT_ID',
    'AZURE_CLIENT_SECRET',
    'AZURE_REDIRECT_URI',
    'PUBLIC_BASE_URL',
    'ATTACHMENT_ALLOWED_EXTENSIONS',
    'ATTACHMENT_MAX_SIZE_MB',
)


def _require_admin():
    if not current_user.is_system_admin:
        return fail('无权限', status=403)
    return None


@admin_api.route('/settings', methods=['GET'])
@login_required
def get_settings():
    err = _require_admin()
    if err:
        return err
    out = {}
    for key in _SETTING_KEYS:
        row = SystemSetting.query.get(key)
        if key == SETTING_COMPANY_NAME:
            out[key] = row.value if row and row.value else get_company_name()
        else:
            out[key] = row.value if row else current_app.config.get(key, '')
    out['company_logo_url'] = get_company_logo_url()
    return ok(out)


@admin_api.route('/settings', methods=['PUT'])
@login_required
def put_settings():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for key, value in data.items():
        if key not in _SETTING_KEYS:
            continue
        row = SystemSetting.query.get(key)
        if not row:
            row = SystemSetting(key=key)
            db.session.add(row)
        row.value = '' if value is None else str(value)
    if SETTING_COMPANY_NAME in data:
        sync_company_name(str(data.get(SETTING_COMPANY_NAME) or ''))
    db.session.commit()
    return ok({'company_logo_url': get_company_logo_url()}, '设置已保存')


_LOGO_MAX_BYTES = 2 * 1024 * 1024


@admin_api.route('/brand-logo', methods=['POST'])
@login_required
def upload_brand_logo():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    b64 = data.get('logo_data') or ''
    if not b64.startswith('data:image'):
        return fail('无效图片数据')
    match = re.match(r'data:image/(png|jpeg|jpg|webp);base64,(.+)', b64, re.I)
    if not match:
        return fail('仅支持 PNG / JPEG / WebP')
    ext = match.group(1).lower().replace('jpeg', 'jpg')
    try:
        raw = base64.b64decode(match.group(2))
    except Exception:
        return fail('图片数据解析失败')
    if len(raw) > _LOGO_MAX_BYTES:
        return fail('图片不能超过 2MB')
    folder = current_app.config.get('BRANDING_FOLDER')
    os.makedirs(folder, exist_ok=True)
    old_rel = clear_company_logo()
    if old_rel:
        old_abs = resolve_logo_abs_path(old_rel, current_app.root_path)
        if os.path.isfile(old_abs):
            try:
                os.remove(old_abs)
            except OSError:
                pass
    fname = f'logo_{datetime.now().strftime("%Y%m%d%H%M%S")}.{ext}'
    path = os.path.join(folder, fname)
    with open(path, 'wb') as f:
        f.write(raw)
    rel = f'{BRANDING_UPLOAD_SUBDIR}/{fname}'
    set_company_logo_path(rel)
    db.session.commit()
    url = get_company_logo_url()
    return ok({'company_logo_url': url, 'logo_url': url}, 'Logo 已更新')


@admin_api.route('/brand-logo', methods=['DELETE'])
@login_required
def delete_brand_logo():
    err = _require_admin()
    if err:
        return err
    rel = clear_company_logo()
    if rel:
        abs_path = resolve_logo_abs_path(rel, current_app.root_path)
        if os.path.isfile(abs_path):
            try:
                os.remove(abs_path)
            except OSError:
                pass
    db.session.commit()
    return ok({'company_logo_url': None}, 'Logo 已移除')


@admin_api.route('/settings/test-mail', methods=['POST'])
@login_required
def test_mail():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    to_addr = (data.get('to') or current_user.email or '').strip()
    if not to_addr:
        return fail('请指定测试收件邮箱')
    if '@' not in to_addr or '.' not in to_addr.split('@')[-1]:
        return fail('测试收件邮箱格式不正确，请填写真实邮箱（如 name@example.com）')
    override = {}
    for key in MAIL_CONFIG_KEYS:
        if key in data and data[key] is not None and str(data[key]).strip() != '':
            override[key] = data[key]
    ok_send, msg = send_test_email(
        current_app,
        to_addr,
        config_override=override or None,
        operator_id=current_user.id,
    )
    if not ok_send:
        return fail(msg)
    return ok(message='测试邮件已发送')


@admin_api.route('/flow-roles', methods=['GET'])
@login_required
def list_flow_roles():
    rows = FlowRole.query.order_by(FlowRole.code).all()
    counts = dict(
        db.session.query(FlowRoleMember.flow_role_id, db.func.count(FlowRoleMember.id))
        .filter(
            FlowRoleMember.company_id.is_(None),
            FlowRoleMember.department_id.is_(None),
        )
        .group_by(FlowRoleMember.flow_role_id)
        .all()
    )
    return ok([flow_role_dict(r, member_count=counts.get(r.id, 0)) for r in rows])


@admin_api.route('/flow-roles', methods=['POST'])
@login_required
def create_flow_role():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    name = (data.get('name') or '').strip()
    if not code or not name:
        return fail('请填写角色编码与名称')
    if FlowRole.query.filter_by(code=code).first():
        return fail('编码已存在')
    r = FlowRole(code=code, name=name, description=data.get('description'))
    db.session.add(r)
    db.session.commit()
    return ok(flow_role_dict(r, member_count=0), '已创建')


@admin_api.route('/flow-roles/<int:role_id>/members', methods=['GET'])
@login_required
def list_flow_role_members(role_id):
    rows = FlowRoleMember.query.filter_by(
        flow_role_id=role_id,
        company_id=None,
        department_id=None,
    ).all()
    return ok([flow_role_member_dict(m) for m in rows])


@admin_api.route('/flow-roles/<int:role_id>/members', methods=['POST'])
@login_required
def add_flow_role_member_api(role_id):
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data['user_id'])
    except (TypeError, ValueError, KeyError):
        return fail('请指定用户')
    m, err_msg = svc_add_flow_role_member(role_id, user_id)
    if err_msg:
        return fail(err_msg)
    db.session.commit()
    return ok(flow_role_member_dict(m), '已添加')


@admin_api.route('/flow-roles/<int:role_id>/members/batch', methods=['PUT'])
@login_required
def set_flow_role_members_api(role_id):
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    user_ids = data.get('user_ids') or []
    if not isinstance(user_ids, list):
        return fail('user_ids 格式无效')
    members, err_msg = set_flow_role_members(role_id, user_ids)
    if err_msg:
        return fail(err_msg)
    db.session.commit()
    return ok(members, '成员已更新')


@admin_api.route('/users/<int:user_id>/flow-roles', methods=['GET'])
@login_required
def get_user_flow_roles(user_id):
    err = _require_admin()
    if err:
        return err
    rows = (
        FlowRoleMember.query.filter_by(user_id=user_id, company_id=None, department_id=None)
        .join(FlowRole, FlowRoleMember.flow_role_id == FlowRole.id)
        .order_by(FlowRole.code)
        .all()
    )
    role_ids = [m.flow_role_id for m in rows]
    roles = FlowRole.query.filter(FlowRole.id.in_(role_ids)).order_by(FlowRole.code).all() if role_ids else []
    return ok({
        'role_ids': role_ids,
        'roles': [flow_role_dict(r) for r in roles],
    })


@admin_api.route('/users/<int:user_id>/flow-roles', methods=['PUT'])
@login_required
def set_user_flow_roles_api(user_id):
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    role_ids = data.get('role_ids') or []
    if not isinstance(role_ids, list):
        return fail('role_ids 格式无效')
    roles, err_msg = set_user_flow_roles(user_id, role_ids)
    if err_msg:
        return fail(err_msg)
    db.session.commit()
    return ok({'role_ids': [r['id'] for r in roles], 'roles': roles}, '流程角色已更新')


@admin_api.route('/flow-roles/<int:role_id>', methods=['PUT'])
@login_required
def update_flow_role(role_id):
    err = _require_admin()
    if err:
        return err
    r = FlowRole.query.get(role_id)
    if not r:
        return fail('角色不存在', status=404)
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return fail('请填写角色名称')
        r.name = name
    if 'description' in data:
        r.description = data.get('description')
    if 'is_active' in data:
        r.is_active = bool(data.get('is_active'))
    db.session.commit()
    return ok({'id': r.id}, '已更新')


@admin_api.route('/flow-roles/<int:role_id>', methods=['DELETE'])
@login_required
def delete_flow_role(role_id):
    err = _require_admin()
    if err:
        return err
    r = FlowRole.query.get(role_id)
    if not r:
        return fail('角色不存在', status=404)
    r.is_active = False
    db.session.commit()
    return ok(message='流程角色已停用')


@admin_api.route('/flow-roles/<int:role_id>/members/<int:member_id>', methods=['DELETE'])
@login_required
def delete_flow_role_member(role_id, member_id):
    err = _require_admin()
    if err:
        return err
    m = FlowRoleMember.query.filter_by(id=member_id, flow_role_id=role_id).first()
    if not m:
        return fail('成员不存在', status=404)
    db.session.delete(m)
    db.session.commit()
    return ok(message='成员已移除')


@admin_api.route('/business-sectors', methods=['GET'])
@login_required
def list_business_sectors():
    err = _require_admin()
    if err:
        return err
    rows = BusinessSector.query.order_by(BusinessSector.sort_order, BusinessSector.id).all()
    return ok([_sector_dict(s) for s in rows])


@admin_api.route('/business-sectors', methods=['POST'])
@login_required
def create_business_sector():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    name = (data.get('name') or '').strip()
    if not code or not name:
        return fail('请填写板块编码与名称')
    if BusinessSector.query.filter_by(code=code).first():
        return fail('编码已存在')
    s = BusinessSector(code=code, name=name, sort_order=int(data.get('sort_order') or 0))
    db.session.add(s)
    db.session.commit()
    return ok(_sector_dict(s), '已创建')


@admin_api.route('/business-sectors/<int:sector_id>', methods=['PUT'])
@login_required
def update_business_sector(sector_id):
    err = _require_admin()
    if err:
        return err
    s = BusinessSector.query.get(sector_id)
    if not s:
        return fail('板块不存在', status=404)
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        s.name = (data.get('name') or '').strip() or s.name
    if 'sort_order' in data:
        s.sort_order = int(data.get('sort_order') or 0)
    if 'is_active' in data:
        s.is_active = bool(data.get('is_active'))
    db.session.commit()
    return ok(_sector_dict(s), '已更新')


@admin_api.route('/business-sectors/<int:sector_id>', methods=['DELETE'])
@login_required
def delete_business_sector(sector_id):
    err = _require_admin()
    if err:
        return err
    s = BusinessSector.query.get(sector_id)
    if not s:
        return fail('板块不存在', status=404)
    s.is_active = False
    db.session.commit()
    return ok(message='板块已停用')


@admin_api.route('/scoped-admins', methods=['GET'])
@login_required
def list_scoped_admins():
    err = _require_admin()
    if err:
        return err
    rows = UserScopedAdmin.query.all()
    out = []
    for row in rows:
        u = User.query.get(row.user_id)
        if not u:
            continue
        out.append(_scoped_admin_dict(row, u))
    return ok(out)


@admin_api.route('/scoped-admins', methods=['POST'])
@login_required
def save_scoped_admin():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    if not user_id:
        return fail('请选择用户')
    u = User.query.get(int(user_id))
    if not u:
        return fail('用户不存在', status=404)
    if u.is_system_admin:
        return fail('该用户已是全局管理员，无需分级授权')
    sector_ids = data.get('sector_ids') or []
    row = UserScopedAdmin.query.filter_by(user_id=u.id).first()
    if not row:
        row = UserScopedAdmin(user_id=u.id)
        db.session.add(row)
    row.sector_ids = json.dumps([int(x) for x in sector_ids], ensure_ascii=False)
    row.can_design_workflow = bool(data.get('can_design_workflow', True))
    row.can_view_instances = bool(data.get('can_view_instances', True))
    row.can_export_instances = bool(data.get('can_export_instances', True))
    db.session.commit()
    return ok(_scoped_admin_dict(row, u), '已保存')


@admin_api.route('/scoped-admins/<int:user_id>', methods=['DELETE'])
@login_required
def delete_scoped_admin(user_id):
    err = _require_admin()
    if err:
        return err
    row = UserScopedAdmin.query.filter_by(user_id=user_id).first()
    if row:
        db.session.delete(row)
        db.session.commit()
    return ok(message='已移除分级管理员')


def _parse_admin_page() -> tuple[int, int]:
    page = max(1, int(request.args.get('page', 1) or 1))
    page_size = min(100, max(10, int(request.args.get('page_size', 20) or 20)))
    return page, page_size


@admin_api.route('/workflow-instances', methods=['GET'])
@login_required
def list_all_workflow_instances():
    err = _require_admin()
    if err:
        return err
    page, page_size = _parse_admin_page()
    status = (request.args.get('status') or '').strip() or None
    sector_id = request.args.get('sector_id', type=int)
    keyword = (request.args.get('keyword') or '').strip() or None
    sort_field = (request.args.get('sort_field') or '').strip() or None
    sort_order = (request.args.get('sort_order') or '').strip() or None
    q = query_admin_workflow_instances(
        status=status,
        sector_id=sector_id,
        keyword=keyword,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        'items': [admin_instance_row(i) for i in rows],
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@admin_api.route('/workflow-instances/delete-confirm/send', methods=['POST'])
@login_required
def send_delete_workflow_instance_confirm_code():
    err = _require_admin()
    if err:
        return err
    ok_send, msg = send_admin_email_confirm_code(current_user, PURPOSE_DELETE_WORKFLOW_INSTANCE)
    if not ok_send:
        return fail(msg)
    return ok(message=msg)


@admin_api.route('/workflow-instances/<ref>', methods=['DELETE'])
@login_required
def delete_workflow_instance(ref):
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    code = (data.get('email_code') or '').strip()
    ok_code, code_msg = verify_admin_email_confirm_code(
        current_user,
        PURPOSE_DELETE_WORKFLOW_INSTANCE,
        code,
    )
    if not ok_code:
        return fail(code_msg)
    inst = resolve_admin_instance_ref(ref)
    if not inst:
        return fail('审批单不存在', status=404)
    purge_workflow_instance(inst)
    db.session.commit()
    return ok(message='审批单已删除')


def _sector_dict(s: BusinessSector) -> dict:
    return {
        'id': s.id,
        'code': s.code,
        'name': s.name,
        'sort_order': s.sort_order,
        'is_active': s.is_active,
    }


def _scoped_admin_dict(row: UserScopedAdmin, user: User) -> dict:
    try:
        sector_ids = json.loads(row.sector_ids or '[]')
    except (json.JSONDecodeError, TypeError):
        sector_ids = []
    return {
        'id': row.id,
        'user_id': user.id,
        'username': user.username,
        'display_name': user.display_label(),
        'email': user.email,
        'sector_ids': sector_ids,
        'can_design_workflow': row.can_design_workflow,
        'can_view_instances': row.can_view_instances,
        'can_export_instances': row.can_export_instances,
    }
