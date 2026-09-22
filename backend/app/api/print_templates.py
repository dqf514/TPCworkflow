# -*- coding: utf-8 -*-
from flask import Blueprint, request
from flask_login import login_required

from app.api.admin import _require_admin
from app.models import PrintTemplate
from app.services.print_template_service import (
    clone_template,
    create_template,
    delete_template,
    get_template_by_code,
    list_templates,
    sample_form_values,
    template_dict,
    update_template,
)
from app.utils.response import fail, ok

print_templates_api = Blueprint('print_templates_api', __name__)


@print_templates_api.route('/print-templates', methods=['GET'])
@login_required
def list_all():
    """登录用户可读取模板列表（Form Studio 选用）。"""
    is_admin = _require_admin() is None
    rows = list_templates(active_only=not is_admin)
    return ok(rows)


@print_templates_api.route('/print-templates/<code>', methods=['GET'])
@login_required
def get_one(code: str):
    is_admin = _require_admin() is None
    row = get_template_by_code(code, active_only=not is_admin)
    if not row:
        return fail('模板不存在', status=404)
    return ok(template_dict(row, include_schema=True))


@print_templates_api.route('/print-templates/sample-data', methods=['GET'])
@login_required
def sample_data():
    return ok(sample_form_values())


@print_templates_api.route('/admin/print-templates', methods=['GET'])
@login_required
def admin_list():
    err = _require_admin()
    if err:
        return err
    rows = PrintTemplate.query.order_by(PrintTemplate.is_builtin.desc(), PrintTemplate.id).all()
    return ok([template_dict(r, include_schema=False) for r in rows])


@print_templates_api.route('/admin/print-templates/<int:template_id>', methods=['GET'])
@login_required
def admin_get(template_id: int):
    err = _require_admin()
    if err:
        return err
    row = PrintTemplate.query.get(template_id)
    if not row:
        return fail('模板不存在', status=404)
    return ok(template_dict(row, include_schema=True))


@print_templates_api.route('/admin/print-templates', methods=['POST'])
@login_required
def admin_create():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    row, errors = create_template(data)
    if errors:
        return fail('；'.join(errors))
    return ok(template_dict(row, include_schema=True), '已创建')


@print_templates_api.route('/admin/print-templates/<int:template_id>', methods=['PUT'])
@login_required
def admin_update(template_id: int):
    err = _require_admin()
    if err:
        return err
    row = PrintTemplate.query.get(template_id)
    if not row:
        return fail('模板不存在', status=404)
    data = request.get_json(silent=True) or {}
    errors = update_template(row, data)
    if errors:
        return fail('；'.join(errors))
    return ok(template_dict(row, include_schema=True), '已保存')


@print_templates_api.route('/admin/print-templates/<int:template_id>/clone', methods=['POST'])
@login_required
def admin_clone(template_id: int):
    err = _require_admin()
    if err:
        return err
    row = PrintTemplate.query.get(template_id)
    if not row:
        return fail('模板不存在', status=404)
    data = request.get_json(silent=True) or {}
    new_code = (data.get('code') or '').strip()
    new_name = (data.get('name') or f'{row.name} (副本)').strip()
    if not new_code:
        return fail('请填写新模板编码')
    cloned, errors = clone_template(row, new_code=new_code, new_name=new_name)
    if errors:
        return fail('；'.join(errors))
    return ok(template_dict(cloned, include_schema=True), '已克隆')


@print_templates_api.route('/admin/print-templates/<int:template_id>', methods=['DELETE'])
@login_required
def admin_remove(template_id: int):
    err = _require_admin()
    if err:
        return err
    row = PrintTemplate.query.get(template_id)
    if not row:
        return fail('模板不存在', status=404)
    msg = delete_template(row)
    if msg:
        return fail(msg)
    return ok(None, '已删除')
