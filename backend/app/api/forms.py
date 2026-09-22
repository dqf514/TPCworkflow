# -*- coding: utf-8 -*-
import json
from datetime import datetime

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import BusinessSector, FormDefinition, WorkflowDefinition, WorkflowInstance
from app.services.apply_visibility import user_can_apply_workflow
from app.services.instance_access import ensure_instance_public_uuid
from app.services.assignee_resolver import _user_in_company
from app.services.permissions import is_global_admin, user_can_design_sector
from app.services.form_schema import (
    DEFAULT_SCHEMA,
    apply_form_description,
    parse_schema,
    validate_form_data,
    validate_schema,
)
from app.services.form_templates.registry import get_builtin_template, list_builtin_templates
from app.services.workflow_publish import ACTIVE_INSTANCE_STATUSES
from app.utils.response import fail, ok
from app.utils.datetime_fmt import format_display_datetime

forms_api = Blueprint('forms_api', __name__)


def _can_manage_form(user, form: FormDefinition | None = None, sector_id: int | None = None) -> bool:
    sid = sector_id
    if form is not None:
        sid = form.business_sector_id
    if is_global_admin(user):
        return True
    return user_can_design_sector(user, sid)


@forms_api.route('/builtin-templates', methods=['GET'])
@login_required
def list_builtin_form_templates():
    return ok(list_builtin_templates())


@forms_api.route('/builtin-templates/<template_key>', methods=['GET'])
@login_required
def get_builtin_form_template(template_key: str):
    admin_id = current_user.id if current_user.is_authenticated else None
    payload = get_builtin_template(template_key, admin_user_id=admin_id)
    if not payload:
        return fail('模板不存在', status=404)
    return ok(payload)


@forms_api.route('/definitions', methods=['GET'])
@login_required
def list_forms():
    status = request.args.get('status')
    q = FormDefinition.query
    if status:
        q = q.filter_by(status=status)
    elif not request.args.get('include_archived'):
        q = q.filter(FormDefinition.status != 'archived')
    rows = q.order_by(FormDefinition.key, FormDefinition.version.desc()).all()
    return ok([_form_dict(r) for r in rows])


@forms_api.route('/linkable-instances', methods=['GET'])
@login_required
def linkable_instances():
    """当前用户已提交的、且在允许关联范围内的申请单。"""
    raw = (request.args.get('form_keys') or '').strip()
    keys = [k.strip() for k in raw.split(',') if k.strip()]
    if not keys:
        return ok([])
    forms = FormDefinition.query.filter(FormDefinition.key.in_(keys)).all()
    wf_ids = {f.workflow_definition_id for f in forms if f.workflow_definition_id}
    if not wf_ids:
        return ok([])
    key_by_wf = {f.workflow_definition_id: f.key for f in forms if f.workflow_definition_id}
    rows = (
        WorkflowInstance.query.filter(
            WorkflowInstance.initiator_id == current_user.id,
            WorkflowInstance.definition_id.in_(wf_ids),
        )
        .order_by(WorkflowInstance.started_at.desc())
        .limit(200)
        .all()
    )
    out = []
    for inst in rows:
        title = inst.business_type or ''
        wf = inst.definition
        if wf:
            title = wf.name or title
        started = format_display_datetime(inst.started_at) or ''
        from app.services.instance_list_meta import resolve_instance_current_node_label

        out.append({
            'instance_id': inst.id,
            'public_uuid': ensure_instance_public_uuid(inst),
            'title': f'{title} {inst.display_no or ""}'.strip(),
            'form_key': key_by_wf.get(inst.definition_id, ''),
            'status': inst.status,
            'current_node_label': resolve_instance_current_node_label(inst),
            'started_at': started,
        })
    return ok(out)


@forms_api.route('/applications', methods=['GET'])
@login_required
def list_applications():
    """已发布且绑定已发布流程的表单（发起申请用）。"""
    company_id = request.args.get('company_id', type=int)
    rows = FormDefinition.query.filter_by(status='published').all()
    out = []
    for f in rows:
        wf = WorkflowDefinition.query.get(f.workflow_definition_id) if f.workflow_definition_id else None
        if not wf or wf.status != 'published':
            continue
        if company_id:
            if not _workflow_visible(wf, company_id):
                continue
            if not user_can_apply_workflow(current_user, wf, company_id):
                continue
        else:
            if not any(
                _workflow_visible(wf, cid) and user_can_apply_workflow(current_user, wf, cid)
                for cid in {m.company_id for m in current_user.org_memberships}
            ):
                continue
        out.append(_application_item(f, wf))
    return ok(out)


@forms_api.route('/applications-catalog', methods=['GET'])
@login_required
def applications_catalog():
    """发起申请导航：按业务板块展示全部可发起的流程（不按公司过滤，点击后再校验）。"""
    company_id = request.args.get('company_id', type=int)
    company_ids = set()
    if company_id:
        company_ids.add(company_id)
    else:
        for m in current_user.org_memberships:
            company_ids.add(m.company_id)
    rows = FormDefinition.query.filter_by(status='published').all()
    sectors = {
        s.id: s
        for s in BusinessSector.query.filter_by(is_active=True).order_by(
            BusinessSector.sort_order,
            BusinessSector.id,
        ).all()
    }
    ungrouped: list[dict] = []
    by_sector: dict[int, list[dict]] = {}
    for f in rows:
        wf = WorkflowDefinition.query.get(f.workflow_definition_id) if f.workflow_definition_id else None
        if not wf or wf.status != 'published':
            continue
        if company_ids:
            visible = any(
                _user_in_company(current_user, cid)
                and _workflow_visible(wf, cid)
                and user_can_apply_workflow(current_user, wf, cid)
                for cid in company_ids
            )
            if not visible:
                continue
        item = _application_item(f, wf, sectors)
        sid = f.business_sector_id or wf.business_sector_id
        if sid and sid in sectors:
            by_sector.setdefault(sid, []).append(item)
        else:
            ungrouped.append(item)
    groups = []
    for sid, sector in sectors.items():
        items = by_sector.get(sid) or []
        if not items:
            continue
        groups.append({
            'sector_id': sid,
            'sector_name': sector.name,
            'sector_sort_order': sector.sort_order,
            'items': sorted(items, key=lambda x: x.get('form_name') or ''),
        })
    if ungrouped:
        groups.append({
            'sector_id': None,
            'sector_name': '其他',
            'sector_sort_order': 9999,
            'items': sorted(ungrouped, key=lambda x: x.get('form_name') or ''),
        })
    return ok(groups)


@forms_api.route('/definitions/<int:form_id>', methods=['GET'])
@login_required
def get_form(form_id):
    f = FormDefinition.query.get(form_id)
    if not f:
        return fail('表单不存在', status=404)
    return ok(_form_dict(f, full=True))


@forms_api.route('/definitions', methods=['POST'])
@login_required
def create_form():
    data = request.get_json(silent=True) or {}
    if not _can_manage_form(current_user, sector_id=data.get('business_sector_id')):
        return fail('无权限', status=403)
    key = (data.get('key') or '').strip()
    name = (data.get('name') or '').strip()
    if not key or not name:
        return fail('请填写表单标识与名称')
    schema = data.get('schema') or DEFAULT_SCHEMA
    description = (data.get('description') or '').strip() or None
    schema = apply_form_description(schema, description)
    errs = validate_schema(schema)
    if errs:
        return fail('；'.join(errs))
    f = FormDefinition(
        key=key,
        name=name,
        version=int(data.get('version') or 1),
        status='draft',
        description=description,
        schema_json=json.dumps(schema, ensure_ascii=False),
        business_sector_id=data.get('business_sector_id'),
        icon=(data.get('icon') or '').strip() or None,
        created_by=current_user.id,
    )
    db.session.add(f)
    db.session.flush()
    wf = _create_or_update_workflow_for_form(f, data.get('workflow'), current_user.id)
    if wf:
        f.workflow_definition_id = wf.id
        wf.form_definition_id = f.id
    db.session.commit()
    return ok(_form_dict(f, full=True), '表单已创建')


@forms_api.route('/definitions/<int:form_id>', methods=['PUT'])
@login_required
def update_form(form_id):
    f = FormDefinition.query.get(form_id)
    if not f:
        return fail('表单不存在', status=404)
    data = request.get_json(silent=True) or {}
    sector_id = data.get('business_sector_id', f.business_sector_id)
    if not _can_manage_form(current_user, form=f, sector_id=sector_id):
        return fail('无权限', status=403)
    if 'name' in data:
        f.name = data['name']
    if 'description' in data:
        f.description = (data.get('description') or '').strip() or None
    if 'business_sector_id' in data:
        f.business_sector_id = data.get('business_sector_id')
        if f.workflow_definition_id:
            wf_sector = WorkflowDefinition.query.get(f.workflow_definition_id)
            if wf_sector:
                wf_sector.business_sector_id = f.business_sector_id
    if 'icon' in data:
        f.icon = (data.get('icon') or '').strip() or None
    if 'schema' in data:
        schema = apply_form_description(data['schema'], f.description)
        errs = validate_schema(schema)
        if errs:
            return fail('；'.join(errs))
        f.schema_json = json.dumps(schema, ensure_ascii=False)
        if f.workflow_definition_id:
            wf_sync = WorkflowDefinition.query.get(f.workflow_definition_id)
            if wf_sync:
                wf_sync.form_schema = f.schema_json
    elif 'description' in data:
        schema = apply_form_description(parse_schema(f.schema_json), f.description)
        f.schema_json = json.dumps(schema, ensure_ascii=False)
        if f.workflow_definition_id:
            wf_sync = WorkflowDefinition.query.get(f.workflow_definition_id)
            if wf_sync:
                wf_sync.form_schema = f.schema_json
    if 'workflow' in data:
        wf = _create_or_update_workflow_for_form(f, data['workflow'], current_user.id)
        if wf:
            f.workflow_definition_id = wf.id
            wf.form_definition_id = f.id
    db.session.commit()
    return ok(_form_dict(f, full=True), '已保存')


@forms_api.route('/definitions/<int:form_id>/publish', methods=['POST'])
@login_required
def publish_form(form_id):
    f = FormDefinition.query.get(form_id)
    if not _can_manage_form(current_user, form=f):
        return fail('无权限', status=403)
    if not f:
        return fail('表单不存在', status=404)
    schema = parse_schema(f.schema_json)
    errs = validate_schema(schema)
    if errs:
        return fail('；'.join(errs))
    if not f.workflow_definition_id:
        return fail('请先设计并保存关联流程')
    wf = WorkflowDefinition.query.get(f.workflow_definition_id)
    if not wf:
        return fail('关联流程不存在')
    f.status = 'published'
    f.published_at = datetime.now()
    wf.status = 'published'
    wf.form_definition_id = f.id
    if f.schema_json:
        wf.form_schema = f.schema_json
    db.session.commit()
    return ok(_form_dict(f), '表单与流程已发布')


@forms_api.route('/definitions/<int:form_id>/unpublish', methods=['POST'])
@login_required
def unpublish_form(form_id):
    """取消发布：不再出现在发起列表，但已有实例/草稿可继续处理。"""
    f = FormDefinition.query.get(form_id)
    if not f:
        return fail('表单不存在', status=404)
    if not _can_manage_form(current_user, form=f):
        return fail('无权限', status=403)
    if f.status == 'archived':
        return fail('已归档表单无法取消发布')
    if f.status != 'published':
        return fail('当前表单未发布')
    if not f.workflow_definition_id:
        return fail('未关联流程')
    wf = WorkflowDefinition.query.get(f.workflow_definition_id)
    if not wf:
        return fail('关联流程不存在')
    f.status = 'draft'
    wf.status = 'draft'
    active_count = WorkflowInstance.query.filter(
        WorkflowInstance.definition_id == wf.id,
        WorkflowInstance.status.in_(ACTIVE_INSTANCE_STATUSES),
    ).count()
    db.session.commit()
    data = _form_dict(f)
    data['active_instance_count'] = active_count
    msg = '已取消发布，新用户将无法发起该流程'
    if active_count:
        msg += f'；当前仍有 {active_count} 条进行中的申请或草稿可继续处理'
    return ok(data, msg)


@forms_api.route('/definitions/<int:form_id>/validate-data', methods=['POST'])
@login_required
def validate_data(form_id):
    f = FormDefinition.query.get(form_id)
    if not f:
        return fail('表单不存在', status=404)
    schema = parse_schema(f.schema_json)
    data = request.get_json(silent=True) or {}
    payload = data.get('form') or data
    errs = validate_form_data(schema, payload)
    if errs:
        return fail('；'.join(errs))
    return ok(message='校验通过')


@forms_api.route('/definitions/<int:form_id>', methods=['DELETE'])
@login_required
def delete_form(form_id):
    f = FormDefinition.query.get(form_id)
    if not _can_manage_form(current_user, form=f):
        return fail('无权限', status=403)
    if not f:
        return fail('表单不存在', status=404)
    wf = (
        WorkflowDefinition.query.get(f.workflow_definition_id)
        if f.workflow_definition_id
        else None
    )
    if wf:
        running = WorkflowInstance.query.filter_by(
            definition_id=wf.id,
            status='running',
        ).count()
        if running:
            return fail('该流程仍有进行中的实例，无法删除')
    f.status = 'archived'
    if wf:
        wf.status = 'archived'
    db.session.commit()
    return ok(message='表单与流程已归档删除')


def _create_or_update_workflow_for_form(form: FormDefinition, wf_data: dict | None, user_id: int):
    if not wf_data:
        if form.workflow_definition_id:
            return WorkflowDefinition.query.get(form.workflow_definition_id)
        return None
    wf_id = wf_data.get('id') or form.workflow_definition_id
    if wf_id:
        wf = WorkflowDefinition.query.get(wf_id)
        if not wf:
            return None
        wf.name = wf_data.get('name') or form.name
        if 'process_graph' in wf_data:
            wf.process_graph = json.dumps(wf_data['process_graph'], ensure_ascii=False)
        if 'settings' in wf_data:
            wf.settings = json.dumps(wf_data['settings'], ensure_ascii=False)
        if 'scope_type' in wf_data:
            wf.scope_type = wf_data['scope_type']
        if 'business_sector_id' in wf_data:
            wf.business_sector_id = wf_data['business_sector_id']
        elif form.business_sector_id:
            wf.business_sector_id = form.business_sector_id
        wf.form_definition_id = form.id
        if form.schema_json:
            wf.form_schema = form.schema_json
        return wf
    wf = WorkflowDefinition(
        key=wf_data.get('key') or form.key,
        name=wf_data.get('name') or form.name,
        version=1,
        status='draft',
        scope_type=wf_data.get('scope_type') or 'global',
        process_graph=json.dumps(
            wf_data.get('process_graph') or {'nodes': [], 'edges': []},
            ensure_ascii=False,
        ),
        settings=json.dumps(wf_data.get('settings') or {}, ensure_ascii=False),
        form_definition_id=form.id,
        business_sector_id=wf_data.get('business_sector_id') or form.business_sector_id,
        created_by=user_id,
    )
    db.session.add(wf)
    db.session.flush()
    return wf


def _workflow_visible(wf: WorkflowDefinition, company_id: int) -> bool:
    if wf.scope_type == 'global':
        return True
    if wf.scope_type == 'company':
        return wf.company_id == company_id
    if wf.scope_type == 'companies':
        try:
            ids = json.loads(wf.company_ids or '[]')
        except (json.JSONDecodeError, TypeError):
            ids = []
        return company_id in ids
    return False


def _application_item(
    f: FormDefinition,
    wf: WorkflowDefinition,
    sectors: dict | None = None,
) -> dict:
    sid = f.business_sector_id or wf.business_sector_id
    sector_name = None
    sector_sort = 9999
    if sectors and sid and sid in sectors:
        sector_name = sectors[sid].name
        sector_sort = sectors[sid].sort_order
    return {
        'form_id': f.id,
        'form_key': f.key,
        'form_name': f.name,
        'workflow_definition_id': wf.id,
        'workflow_name': wf.name,
        'description': f.description,
        'icon': f.icon or 'general',
        'business_sector_id': sid,
        'sector_name': sector_name,
        'sector_sort_order': sector_sort,
    }


def _form_dict(f: FormDefinition, full: bool = False) -> dict:
    sector_name = ''
    if f.business_sector_id:
        s = BusinessSector.query.get(f.business_sector_id)
        sector_name = s.name if s else ''
    base = {
        'id': f.id,
        'key': f.key,
        'name': f.name,
        'version': f.version,
        'status': f.status,
        'description': f.description,
        'workflow_definition_id': f.workflow_definition_id,
        'business_sector_id': f.business_sector_id,
        'sector_name': sector_name,
        'icon': f.icon or 'general',
        'published_at': format_display_datetime(f.published_at),
    }
    if not full:
        return base
    schema = apply_form_description(parse_schema(f.schema_json), f.description)
    base['schema'] = schema
    wf = WorkflowDefinition.query.get(f.workflow_definition_id) if f.workflow_definition_id else None
    if wf:
        from app.services.graph_utils import parse_graph
        from app.services.workflow_settings import merge_settings

        base['workflow'] = {
            'id': wf.id,
            'key': wf.key,
            'name': wf.name,
            'status': wf.status,
            'scope_type': wf.scope_type,
            'process_graph': parse_graph(wf.process_graph),
            'settings': merge_settings(wf.settings),
            'business_sector_id': wf.business_sector_id,
        }
    return base
