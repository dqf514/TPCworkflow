# -*- coding: utf-8 -*-
import json
from datetime import datetime
from urllib.parse import quote

from flask import Blueprint, Response, request
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.services.approval_token import get_valid_token, mark_token_used
from app.services.email_action_page import render_email_action_error, render_email_action_page

from app.extensions import db
from app.models import (
    BusinessSector,
    Department,
    FormDefinition,
    InstanceTimeline,
    TaskInstance,
    User,
    WorkflowDefinition,
    WorkflowInstance,
)
from app.services.excel_export import build_instances_workbook
from app.services.finance_export_profiles import get_finance_export_profile, list_finance_export_profiles
from app.services.finance_export_mapping_service import (
    create_mapping,
    delete_mapping,
    finance_mapping_meta,
    get_mapping,
    list_mappings_for_sector,
    list_profiles_for_sector,
    list_sector_workflow_definitions,
    list_workflow_field_sources,
    load_template_columns,
    mapping_row_to_dict,
    resolve_finance_export_profile,
    update_mapping,
    _builtin_profile_as_mapping_template,
)
from app.services.finance_voucher_export import build_yonsuite_voucher_workbook, sanitize_export_filename
from app.services.permissions import (
    get_scoped_admin,
    get_user_sector_ids,
    is_global_admin,
    user_can_export_sector,
    user_can_view_sector_instances,
)
from app.services.form_schema import (
    clone_form_for_resubmit,
    parse_schema,
    prepare_form_for_submit,
    resolve_definition_schema,
    validate_form_data,
)
from app.services.record_set_service import sync_record_sets_from_form
from app.services.receipt_duplicate_service import validate_form_receipt_duplicates
from app.services.graph_utils import find_node, parse_graph, parse_variables, resolve_node_display_name
from app.services.instance_progress import (
    count_mine_unread_progress,
    instance_has_unread_progress,
    mark_instance_seen,
)
from app.services.instance_access import (
    ensure_instance_public_uuid,
    participated_instances_filter,
    PARTICIPATED_TASK_STATUSES,
    resolve_instance_by_public_uuid,
    user_can_view_instance,
)
from app.services.workflow_settings import merge_settings
from app.services.workflow_engine import WorkflowEngine
from app.services.workflow_publish import (
    definition_allows_existing_instance,
    definition_allows_new_application,
)
from app.utils.datetime_fmt import format_display_datetime
from app.utils.response import fail, ok

workflow_api = Blueprint('workflow_api', __name__)
_engine = WorkflowEngine()


@workflow_api.route('/business-sectors', methods=['GET'])
@login_required
def list_business_sectors():
    rows = BusinessSector.query.filter_by(is_active=True).order_by(
        BusinessSector.sort_order,
        BusinessSector.id,
    ).all()
    return ok([{'id': s.id, 'code': s.code, 'name': s.name} for s in rows])


@workflow_api.route('/definitions', methods=['GET'])
@login_required
def list_definitions():
    company_id = request.args.get('company_id', type=int)
    status = request.args.get('status')
    q = WorkflowDefinition.query
    if status:
        q = q.filter_by(status=status)
    else:
        q = q.filter(WorkflowDefinition.status.in_(['published', 'draft']))
    rows = q.order_by(WorkflowDefinition.key, WorkflowDefinition.version.desc()).all()
    out = []
    seen = set()
    for d in rows:
        if d.key in seen and status != 'draft':
            continue
        if company_id and not _visible_for_company(d, company_id):
            continue
        seen.add(d.key)
        out.append(_definition_dict(d, full=request.args.get('full') == '1'))
    return ok(out)


@workflow_api.route('/definitions/<int:def_id>', methods=['GET'])
@login_required
def get_definition(def_id):
    d = WorkflowDefinition.query.get(def_id)
    if not d:
        return fail('流程模板不存在', status=404)
    return ok(_definition_dict(d, full=True))


@workflow_api.route('/definitions', methods=['POST'])
@login_required
def create_definition():
    if not current_user.is_system_admin:
        return fail('无权限', status=403)
    data = request.get_json(silent=True) or {}
    key = (data.get('key') or '').strip()
    name = (data.get('name') or '').strip()
    if not key or not name:
        return fail('请填写流程标识与名称')
    d = WorkflowDefinition(
        key=key,
        name=name,
        version=int(data.get('version') or 1),
        status=data.get('status') or 'draft',
        scope_type=data.get('scope_type') or 'global',
        company_id=data.get('company_id'),
        company_ids=json.dumps(data.get('company_ids') or [], ensure_ascii=False)
        if data.get('company_ids') is not None
        else None,
        form_schema=json.dumps(data.get('form_schema') or [], ensure_ascii=False),
        process_graph=json.dumps(data.get('process_graph') or {'nodes': [], 'edges': []}, ensure_ascii=False),
        settings=json.dumps(data.get('settings') or {}, ensure_ascii=False),
        created_by=current_user.id,
    )
    db.session.add(d)
    db.session.commit()
    return ok(_definition_dict(d, full=True), '已创建')


@workflow_api.route('/definitions/<int:def_id>', methods=['PUT'])
@login_required
def update_definition(def_id):
    if not current_user.is_system_admin:
        return fail('无权限', status=403)
    d = WorkflowDefinition.query.get(def_id)
    if not d:
        return fail('流程模板不存在', status=404)
    data = request.get_json(silent=True) or {}
    for field in ('name', 'status', 'scope_type', 'company_id'):
        if field in data:
            setattr(d, field, data[field])
    if 'company_ids' in data:
        d.company_ids = json.dumps(data['company_ids'] or [], ensure_ascii=False)
    if 'form_schema' in data:
        d.form_schema = json.dumps(data['form_schema'] or [], ensure_ascii=False)
    if 'process_graph' in data:
        d.process_graph = json.dumps(data['process_graph'] or {}, ensure_ascii=False)
    if 'settings' in data:
        d.settings = json.dumps(data['settings'] or {}, ensure_ascii=False)
    db.session.commit()
    return ok(_definition_dict(d, full=True), '已保存')


@workflow_api.route('/definitions/<int:def_id>/publish', methods=['POST'])
@login_required
def publish_definition(def_id):
    if not current_user.is_system_admin:
        return fail('无权限', status=403)
    d = WorkflowDefinition.query.get(def_id)
    if not d:
        return fail('流程模板不存在', status=404)
    graph = parse_graph(d.process_graph)
    if not any(n.get('type') == 'start' for n in graph.get('nodes') or []):
        return fail('流程图需包含开始节点')
    d.status = 'published'
    db.session.commit()
    return ok(_definition_dict(d), '已发布')


def _instance_can_withdraw(inst: WorkflowInstance, user_id: int) -> bool:
    if inst.initiator_id != user_id:
        return False
    if inst.status == 'running':
        return True
    if inst.status == 'approved':
        settings = merge_settings(inst.definition.settings if inst.definition else None)
        return bool(settings.get('allow_revoke_after_approved'))
    return False


@workflow_api.route('/instances', methods=['GET'])
@login_required
def list_instances():
    from app.services.instance_list_meta import apply_instance_list_sort

    participated = request.args.get('participated') == '1'
    mine = request.args.get('mine') == '1'
    sort_field = (request.args.get('sort_field') or '').strip() or None
    sort_order = (request.args.get('sort_order') or '').strip() or None
    if participated and mine:
        return fail('参数冲突：mine 与 participated 不能同时使用')

    q = WorkflowInstance.query
    if mine:
        q = q.filter_by(initiator_id=current_user.id)
        q = apply_instance_list_sort(
            q,
            sort_field=sort_field,
            sort_order=sort_order,
            default_field='updated_at',
        )
        rows = q.limit(100).all()
        out = []
        latest_id = None
        latest_ts = None
        for i in rows:
            if i.status == 'draft':
                continue
            ts = i.updated_at or i.finished_at or i.started_at
            if ts and (latest_ts is None or ts > latest_ts):
                latest_ts = ts
                latest_id = i.id
        for i in rows:
            d = _instance_dict_mine(i, current_user.id)
            d['is_latest_update'] = bool(latest_id and i.id == latest_id and i.status != 'draft')
            out.append(d)
        return ok(out)
    elif participated:
        q = q.filter(participated_instances_filter(current_user.id))
        q = q.filter(WorkflowInstance.status != 'draft')
    else:
        return fail('请指定 mine=1 或 participated=1')

    q = apply_instance_list_sort(q, sort_field=sort_field, sort_order=sort_order)
    rows = q.limit(100).all()
    out = []
    for i in rows:
        if participated:
            d = _instance_dict_participated(i, current_user.id)
        else:
            d = _instance_dict(i, brief=True)
            d['can_withdraw'] = _instance_can_withdraw(i, current_user.id)
        out.append(d)
    return ok(out)


@workflow_api.route('/sector-monitor/sectors', methods=['GET'])
@login_required
def list_sector_monitor_sectors():
    """审批统计板块下拉：仅返回当前用户有权限且存在流程数据的板块及条数。"""
    if is_global_admin(current_user):
        allowed_ids = None
    else:
        allowed_ids = get_user_sector_ids(current_user)
        row = get_scoped_admin(current_user)
        if not row or not row.can_view_instances or not allowed_ids:
            return ok([])

    q = (
        db.session.query(
            WorkflowInstance.business_sector_id,
            func.count(WorkflowInstance.id),
        )
        .filter(WorkflowInstance.business_sector_id.isnot(None))
        .filter(WorkflowInstance.status != 'draft')
        .group_by(WorkflowInstance.business_sector_id)
    )
    if allowed_ids is not None:
        q = q.filter(WorkflowInstance.business_sector_id.in_(allowed_ids))

    counts = {int(sid): int(cnt) for sid, cnt in q.all() if sid}
    if not counts:
        return ok([])

    sectors = BusinessSector.query.filter(
        BusinessSector.id.in_(counts.keys()),
    ).order_by(BusinessSector.sort_order, BusinessSector.id).all()

    out = []
    for sector in sectors:
        if not user_can_view_sector_instances(current_user, sector.id):
            continue
        cnt = counts.get(sector.id, 0)
        if cnt <= 0:
            continue
        out.append({
            'id': sector.id,
            'name': sector.name,
            'instance_count': cnt,
        })
    return ok(out)


@workflow_api.route('/sector-instances', methods=['GET'])
@login_required
def list_sector_instances():
    from app.services.instance_list_meta import apply_instance_list_sort

    sector_id = request.args.get('sector_id', type=int)
    if not sector_id:
        return fail('请指定业务板块')
    if not user_can_view_sector_instances(current_user, sector_id):
        return fail('无权限查看该板块流程', status=403)
    status = request.args.get('status')
    sort_field = (request.args.get('sort_field') or '').strip() or None
    sort_order = (request.args.get('sort_order') or '').strip() or None
    q = WorkflowInstance.query.filter_by(business_sector_id=sector_id)
    q = q.filter(WorkflowInstance.status != 'draft')
    if status:
        q = q.filter_by(status=status)
    q = apply_instance_list_sort(q, sort_field=sort_field, sort_order=sort_order)
    rows = q.limit(500).all()
    return ok([_instance_row(i) for i in rows])


@workflow_api.route('/sector-instances/export', methods=['GET'])
@login_required
def export_sector_instances():
    sector_id = request.args.get('sector_id', type=int)
    if not sector_id:
        return fail('请指定业务板块')
    if not user_can_export_sector(current_user, sector_id):
        return fail('无权限导出', status=403)
    status = request.args.get('status')
    q = WorkflowInstance.query.filter_by(business_sector_id=sector_id)
    q = q.filter(WorkflowInstance.status != 'draft')
    if status:
        q = q.filter_by(status=status)
    rows = (
        q.options(joinedload(WorkflowInstance.definition))
        .order_by(WorkflowInstance.started_at.desc())
        .limit(2000)
        .all()
    )
    data = build_instances_workbook(rows)
    sector = BusinessSector.query.get(sector_id)
    fname = f'流程清单_{sector.name if sector else sector_id}_{datetime.now().strftime("%Y%m%d%H%M")}.xlsx'
    ascii_name = f'workflow_list_{sector_id}_{datetime.now().strftime("%Y%m%d%H%M")}.xlsx'
    return Response(
        data,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': (
                f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(fname)}'
            ),
        },
    )


def _parse_query_datetime(val: str | None) -> datetime | None:
    if not val:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(val.strip()[:19], fmt)
        except ValueError:
            continue
    return None


def _finance_export_allowed_sector_ids(user) -> list[int] | None:
    """全局管理员返回 None 表示不限；否则返回可导出板块 ID 列表。"""
    if is_global_admin(user):
        return None
    row = get_scoped_admin(user)
    if not row or not row.can_export_instances:
        return []
    return get_user_sector_ids(user)


def _apply_finance_instance_filters(q, *, status: str, time_field: str, date_from, date_to):
    q = q.filter(WorkflowInstance.status != 'draft')
    if status:
        q = q.filter_by(status=status)
    field_col = WorkflowInstance.finished_at if time_field == 'finished_at' else WorkflowInstance.started_at
    if date_from:
        q = q.filter(field_col >= date_from)
    if date_to:
        q = q.filter(field_col <= date_to)
    return q


@workflow_api.route('/finance-export/sectors', methods=['GET'])
@login_required
def list_finance_export_sectors():
    """财务导出板块下拉：仅返回当前用户有导出权限且存在流程数据的板块。"""
    allowed_ids = _finance_export_allowed_sector_ids(current_user)
    if allowed_ids is not None and not allowed_ids:
        return ok([])

    q = (
        db.session.query(
            WorkflowInstance.business_sector_id,
            func.count(WorkflowInstance.id),
        )
        .filter(WorkflowInstance.business_sector_id.isnot(None))
        .filter(WorkflowInstance.status != 'draft')
        .group_by(WorkflowInstance.business_sector_id)
    )
    if allowed_ids is not None:
        q = q.filter(WorkflowInstance.business_sector_id.in_(allowed_ids))

    counts = {int(sid): int(cnt) for sid, cnt in q.all() if sid}
    if not counts:
        return ok([])

    sectors = BusinessSector.query.filter(
        BusinessSector.id.in_(counts.keys()),
    ).order_by(BusinessSector.sort_order, BusinessSector.id).all()

    out = []
    for sector in sectors:
        if not user_can_export_sector(current_user, sector.id):
            continue
        cnt = counts.get(sector.id, 0)
        if cnt <= 0:
            continue
        out.append({
            'id': sector.id,
            'name': sector.name,
            'instance_count': cnt,
        })
    return ok(out)


@workflow_api.route('/finance-export/instances', methods=['GET'])
@login_required
def list_finance_export_instances():
    from app.services.instance_list_meta import apply_instance_list_sort

    sector_id = request.args.get('sector_id', type=int)
    if not sector_id:
        return fail('请指定业务板块')
    if not user_can_export_sector(current_user, sector_id):
        return fail('无权限导出该板块流程', status=403)

    status = request.args.get('status') or ''
    time_field = request.args.get('time_field') or 'started_at'
    sort_field = (request.args.get('sort_field') or '').strip() or None
    sort_order = (request.args.get('sort_order') or '').strip() or None
    if time_field not in ('started_at', 'finished_at'):
        time_field = 'started_at'
    date_from = _parse_query_datetime(request.args.get('date_from'))
    date_to = _parse_query_datetime(request.args.get('date_to'))
    if date_to and len((request.args.get('date_to') or '').strip()) <= 10:
        date_to = date_to.replace(hour=23, minute=59, second=59)

    q = WorkflowInstance.query.filter_by(business_sector_id=sector_id)
    q = _apply_finance_instance_filters(
        q,
        status=status,
        time_field=time_field,
        date_from=date_from,
        date_to=date_to,
    )
    q = apply_instance_list_sort(q, sort_field=sort_field, sort_order=sort_order)
    rows = (
        q.options(joinedload(WorkflowInstance.definition))
        .limit(2000)
        .all()
    )
    return ok([_instance_row(i) for i in rows])


def _parse_finance_runtime_options(profile: dict, payload: dict) -> dict:
    opts: dict = {}
    for field in profile.get('options') or []:
        key = field.get('key')
        if not key:
            continue
        raw = payload.get(key)
        if raw is None or raw == '':
            if field.get('default') is not None:
                opts[key] = field.get('default')
            continue
        if field.get('type') == 'switch':
            if isinstance(raw, bool):
                opts[key] = raw
            else:
                opts[key] = str(raw).lower() in ('1', 'true', 'yes', 'on')
        else:
            opts[key] = raw
    return opts


@workflow_api.route('/finance-export/profiles', methods=['GET'])
@login_required
def list_finance_export_profiles_api():
    sector_id = request.args.get('sector_id', type=int)
    return ok(list_profiles_for_sector(sector_id))


@workflow_api.route('/finance-export/template-columns', methods=['GET'])
@login_required
def list_finance_export_template_columns():
    return ok(load_template_columns())


@workflow_api.route('/finance-export/mapping-meta', methods=['GET'])
@login_required
def finance_export_mapping_meta_api():
    return ok(finance_mapping_meta())


@workflow_api.route('/finance-export/workflow-definitions', methods=['GET'])
@login_required
def list_finance_export_workflow_definitions():
    sector_id = request.args.get('sector_id', type=int)
    if not sector_id:
        return fail('请指定业务板块')
    if not user_can_export_sector(current_user, sector_id):
        return fail('无权限', status=403)
    return ok(list_sector_workflow_definitions(sector_id))


@workflow_api.route('/finance-export/workflow-fields', methods=['GET'])
@login_required
def list_finance_export_workflow_fields():
    sector_id = request.args.get('sector_id', type=int)
    raw_ids = request.args.get('definition_ids') or ''
    if not sector_id:
        return fail('请指定业务板块')
    if not user_can_export_sector(current_user, sector_id):
        return fail('无权限', status=403)
    definition_ids = []
    for part in str(raw_ids).split(','):
        part = part.strip()
        if not part:
            continue
        try:
            definition_ids.append(int(part))
        except ValueError:
            continue
    return ok(list_workflow_field_sources(definition_ids))


@workflow_api.route('/finance-export/mappings', methods=['GET'])
@login_required
def list_finance_export_mappings():
    sector_id = request.args.get('sector_id', type=int)
    if not sector_id:
        return fail('请指定业务板块')
    if not user_can_export_sector(current_user, sector_id):
        return fail('无权限', status=403)
    return ok(list_mappings_for_sector(sector_id))


@workflow_api.route('/finance-export/mappings/template/<profile_id>', methods=['GET'])
@login_required
def get_finance_export_mapping_template(profile_id: str):
    sector_id = request.args.get('sector_id', type=int)
    if not sector_id:
        return fail('请指定业务板块')
    if not user_can_export_sector(current_user, sector_id):
        return fail('无权限', status=403)
    tpl = _builtin_profile_as_mapping_template(profile_id)
    if not tpl:
        return fail('未知的内置方案')
    return ok(tpl)


@workflow_api.route('/finance-export/mappings', methods=['POST'])
@login_required
def create_finance_export_mapping():
    data = request.get_json(silent=True) or {}
    sector_id = data.get('sector_id')
    if not sector_id:
        return fail('请指定业务板块')
    try:
        sector_id = int(sector_id)
    except (TypeError, ValueError):
        return fail('业务板块无效')
    if not user_can_export_sector(current_user, sector_id):
        return fail('无权限', status=403)
    if not str(data.get('name') or '').strip():
        return fail('请填写方案名称')
    row = create_mapping(sector_id, data, current_user.id)
    return ok(row)


@workflow_api.route('/finance-export/mappings/<int:mapping_id>', methods=['GET'])
@login_required
def get_finance_export_mapping(mapping_id: int):
    sector_id = request.args.get('sector_id', type=int)
    row = get_mapping(mapping_id, sector_id)
    if not row:
        return fail('映射方案不存在', status=404)
    if not user_can_export_sector(current_user, row.sector_id):
        return fail('无权限', status=403)
    return ok(mapping_row_to_dict(row))


@workflow_api.route('/finance-export/mappings/<int:mapping_id>', methods=['PUT'])
@login_required
def update_finance_export_mapping(mapping_id: int):
    data = request.get_json(silent=True) or {}
    row = get_mapping(mapping_id)
    if not row:
        return fail('映射方案不存在', status=404)
    if not user_can_export_sector(current_user, row.sector_id):
        return fail('无权限', status=403)
    updated = update_mapping(row, data)
    return ok(updated)


@workflow_api.route('/finance-export/mappings/<int:mapping_id>', methods=['DELETE'])
@login_required
def delete_finance_export_mapping(mapping_id: int):
    row = get_mapping(mapping_id)
    if not row:
        return fail('映射方案不存在', status=404)
    if not user_can_export_sector(current_user, row.sector_id):
        return fail('无权限', status=403)
    delete_mapping(row)
    return ok({'deleted': mapping_id})


@workflow_api.route('/finance-export/export', methods=['POST'])
@login_required
def export_finance_voucher():
    data = request.get_json(silent=True) or {}
    sector_id = data.get('sector_id')
    profile_id = str(data.get('profile_id') or '').strip()
    if not sector_id:
        return fail('请指定业务板块')
    if not profile_id:
        return fail('请选择导出方案')
    try:
        sector_id = int(sector_id)
    except (TypeError, ValueError):
        return fail('业务板块无效')

    if not user_can_export_sector(current_user, sector_id):
        return fail('无权限导出', status=403)

    profile = resolve_finance_export_profile(profile_id)
    if not profile:
        return fail('未知的财务导出方案')

    runtime = _parse_finance_runtime_options(profile, data.get('options') or data)
    for field in profile.get('options') or []:
        if not field.get('required'):
            continue
        key = field.get('key')
        if field.get('type') == 'switch':
            continue
        val = runtime.get(key)
        if val is None or str(val).strip() == '':
            return fail(f'请填写{field.get("label") or key}')

    raw_ids = data.get('instance_ids')
    if not raw_ids or not isinstance(raw_ids, (list, tuple)):
        return fail('请至少选择一条需要导出的流程')
    try:
        instance_ids = [int(x) for x in raw_ids if x is not None]
    except (TypeError, ValueError):
        return fail('所选流程无效')
    if not instance_ids:
        return fail('请至少选择一条需要导出的流程')

    rows = (
        WorkflowInstance.query.filter(
            WorkflowInstance.id.in_(instance_ids),
            WorkflowInstance.business_sector_id == sector_id,
        )
        .options(joinedload(WorkflowInstance.definition))
        .order_by(WorkflowInstance.started_at.desc())
        .all()
    )
    found_ids = {r.id for r in rows}
    if len(found_ids) != len(set(instance_ids)):
        return fail('部分所选流程不存在或不属于当前板块')

    try:
        blob = build_yonsuite_voucher_workbook(rows, profile_id, runtime)
    except ValueError as exc:
        return fail(str(exc))
    except FileNotFoundError as exc:
        return fail(str(exc))

    sector = BusinessSector.query.get(sector_id)
    sector_name = sector.name if sector else str(sector_id)
    ts = datetime.now().strftime('%Y%m%d%H%M')
    fname = sanitize_export_filename(f'凭证导入_{profile.get("name")}_{sector_name}_{ts}.xlsx')
    ascii_name = f'yonsuite_voucher_{sector_id}_{ts}.xlsx'
    return Response(
        blob,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': (
                f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(fname)}'
            ),
        },
    )


def _draft_payload(data: dict) -> tuple[dict, dict]:
    form_payload = data.get('form') or {}
    variables = data.get('variables') or {}
    variables['form'] = form_payload
    return form_payload, variables


def _merge_submit_form_errors(
    schema: dict,
    form_payload: dict,
    company_id: int | None,
    exclude_instance_ref: str | None = None,
) -> list[str]:
    errs = list(validate_form_data(schema, form_payload))
    errs.extend(
        validate_form_receipt_duplicates(
            schema,
            form_payload,
            company_id,
            exclude_instance_ref,
        ),
    )
    return errs


@workflow_api.route('/instances', methods=['POST'])
@login_required
def start_instance():
    data = request.get_json(silent=True) or {}
    def_id = data.get('definition_id')
    company_id = data.get('company_id')
    if not def_id or not company_id:
        return fail('请选择流程模板与发起公司')
    definition = WorkflowDefinition.query.get(def_id)
    if not definition_allows_new_application(definition):
        return fail('流程模板不存在或未发布', status=404)
    form_payload, variables = _draft_payload(data)
    schema = _resolve_form_schema(definition)
    as_draft = data.get('as_draft') is True or data.get('save_as_draft') is True
    if as_draft:
        from app.services.date_range_value import apply_date_range_auto_days
        apply_date_range_auto_days(schema, form_payload, int(company_id), current_user.id)
        variables['form'] = form_payload
        try:
            inst = _engine.save_draft(
                definition=definition,
                initiator_id=current_user.id,
                company_id=int(company_id),
                department_id=data.get('department_id'),
                org_unit_id=data.get('org_unit_id'),
                variables=variables,
            )
        except ValueError as exc:
            return fail(str(exc))
        sync_record_sets_from_form(schema, form_payload, current_user.id)
        return ok(_instance_dict(inst), '草稿已保存')

    form_payload = prepare_form_for_submit(
        schema,
        form_payload,
        form_definition_id=getattr(definition, 'form_definition_id', None),
        definition_id=definition.id,
        company_id=int(company_id),
        user_id=current_user.id,
    )
    variables['form'] = form_payload
    ferrs = _merge_submit_form_errors(schema, form_payload, int(company_id))
    if ferrs:
        return fail('；'.join(ferrs))
    try:
        inst = _engine.start(
            definition=definition,
            initiator_id=current_user.id,
            company_id=int(company_id),
            department_id=data.get('department_id'),
            org_unit_id=data.get('org_unit_id'),
            variables=variables,
            business_type=data.get('business_type'),
            business_id=data.get('business_id'),
        )
    except ValueError as exc:
        return fail(str(exc))
    sync_record_sets_from_form(schema, form_payload, current_user.id)
    return ok(_instance_dict(inst), '流程已发起')


@workflow_api.route('/instances/<instance_ref>', methods=['PUT'])
@login_required
def update_instance_draft(instance_ref):
    """更新本人草稿（不校验必填项）。"""
    inst, err = _load_viewable_instance(instance_ref)
    if err:
        return fail(err, status=404)
    if inst.initiator_id != current_user.id:
        return fail('无权修改该草稿', status=403)
    if inst.status != 'draft':
        return fail('仅草稿可更新')
    data = request.get_json(silent=True) or {}
    company_id = data.get('company_id') or inst.company_id
    if not company_id:
        return fail('请选择发起公司')
    definition = inst.definition
    if not definition_allows_existing_instance(definition, inst):
        return fail('流程模板不存在或未发布', status=404)
    form_payload, variables = _draft_payload(data)
    schema = _resolve_form_schema(definition)
    from app.services.date_range_value import apply_date_range_auto_days
    apply_date_range_auto_days(schema, form_payload, int(company_id), current_user.id)
    variables['form'] = form_payload
    try:
        inst = _engine.save_draft(
            definition=definition,
            initiator_id=current_user.id,
            company_id=int(company_id),
            department_id=data.get('department_id'),
            org_unit_id=data.get('org_unit_id'),
            variables=variables,
            instance=inst,
        )
    except ValueError as exc:
        return fail(str(exc))
    sync_record_sets_from_form(schema, form_payload, current_user.id)
    return ok(_instance_dict(inst), '草稿已保存')


@workflow_api.route('/instances/<instance_ref>/submit', methods=['POST'])
@login_required
def submit_instance_draft(instance_ref):
    """将草稿正式提交。"""
    inst, err = _load_viewable_instance(instance_ref)
    if err:
        return fail(err, status=404)
    if inst.initiator_id != current_user.id:
        return fail('无权提交该草稿', status=403)
    if inst.status != 'draft':
        return fail('该申请已不是草稿')
    data = request.get_json(silent=True) or {}
    if data.get('form') is not None:
        form_payload = data.get('form') or {}
        variables = parse_variables(inst.variables)
        variables['form'] = form_payload
        if data.get('company_id'):
            inst.company_id = int(data['company_id'])
        if 'department_id' in data:
            inst.department_id = data.get('department_id')
        if 'org_unit_id' in data:
            inst.org_unit_id = data.get('org_unit_id')
        vars_payload = dict(variables)
        vars_payload.setdefault('org', {})
        vars_payload['org'].update({
            'company_id': inst.company_id,
            'department_id': inst.department_id,
            'org_unit_id': inst.org_unit_id,
            'initiator_id': current_user.id,
        })
        inst.variables = json.dumps(vars_payload, ensure_ascii=False)
        db.session.flush()
    else:
        form_payload = (parse_variables(inst.variables).get('form') or {})

    definition = inst.definition
    if not definition_allows_existing_instance(definition, inst):
        return fail('流程模板不存在或未发布', status=404)
    schema = _resolve_form_schema(definition)
    form_payload = prepare_form_for_submit(
        schema,
        form_payload,
        form_definition_id=getattr(definition, 'form_definition_id', None),
        definition_id=definition.id,
        company_id=inst.company_id,
        user_id=inst.initiator_id,
    )
    variables = parse_variables(inst.variables)
    variables['form'] = form_payload
    vars_payload = dict(variables)
    vars_payload.setdefault('org', {})
    vars_payload['org'].update({
        'company_id': inst.company_id,
        'department_id': inst.department_id,
        'org_unit_id': inst.org_unit_id,
        'initiator_id': current_user.id,
    })
    inst.variables = json.dumps(vars_payload, ensure_ascii=False)
    db.session.flush()
    ferrs = _merge_submit_form_errors(
        schema,
        form_payload,
        inst.company_id,
        ensure_instance_public_uuid(inst),
    )
    if ferrs:
        return fail('；'.join(ferrs))
    try:
        inst = _engine.submit_draft(inst, current_user.id)
    except ValueError as exc:
        return fail(str(exc))
    sync_record_sets_from_form(schema, form_payload, current_user.id)
    return ok(_instance_dict(inst), '流程已发起')


def _load_viewable_instance(instance_ref: str) -> tuple[WorkflowInstance | None, str | None]:
    """按 UUID 加载实例；无权限与不存在均返回相同错误，避免枚举。"""
    inst = resolve_instance_by_public_uuid(instance_ref)
    if not inst:
        return None, '流程不存在'
    if not user_can_view_instance(current_user, inst):
        return None, '流程不存在'
    return inst, None


@workflow_api.route('/instances/<instance_ref>', methods=['GET'])
@login_required
def get_instance(instance_ref):
    inst, err = _load_viewable_instance(instance_ref)
    if err:
        return fail(err, status=404)
    if inst.initiator_id == current_user.id:
        mark_instance_seen(current_user.id, inst)
        db.session.commit()
    return ok(_instance_detail(inst))


@workflow_api.route('/instances/<instance_ref>/withdraw', methods=['POST'])
@login_required
def withdraw_instance(instance_ref):
    """发起人撤回本人申请。"""
    inst, err = _load_viewable_instance(instance_ref)
    if err:
        return fail(err, status=404)
    try:
        inst = _engine.withdraw(inst, current_user.id)
    except ValueError as exc:
        return fail(str(exc))
    d = _instance_dict(inst, brief=True)
    d['can_withdraw'] = False
    return ok(d, '已撤回')


@workflow_api.route('/instances/<instance_ref>/resubmit', methods=['GET'])
@login_required
def resubmit_context(instance_ref):
    """再次提交：返回原申请表单数据及组织上下文（仅发起人本人）。"""
    inst, err = _load_viewable_instance(instance_ref)
    if err:
        return fail(err, status=404)
    if inst.initiator_id != current_user.id:
        return fail('只能基于本人发起的申请再次提交', status=403)
    definition = inst.definition
    if not definition_allows_new_application(definition):
        return fail('该流程已下线或未发布，无法再次提交')
    schema = _resolve_form_schema(definition)
    vars_payload = parse_variables(inst.variables)
    form_payload = clone_form_for_resubmit(schema, vars_payload.get('form') or {})
    icon = 'general'
    if definition.form_definition_id:
        from app.models import FormDefinition

        fd = FormDefinition.query.get(definition.form_definition_id)
        if fd and fd.icon:
            icon = fd.icon
    return ok({
        'source_instance_id': inst.id,
        'source_public_uuid': ensure_instance_public_uuid(inst),
        'definition_id': definition.id,
        'definition_name': definition.name,
        'icon': icon,
        'company_id': inst.company_id,
        'org_unit_id': inst.org_unit_id,
        'department_id': inst.department_id,
        'form': form_payload,
    })


@workflow_api.route('/tasks/email-action', methods=['GET', 'POST'])
def task_email_action():
    """邮件内快速审批（令牌鉴权，无需登录）。"""
    token_str = (request.args.get('token') or request.form.get('token') or '').strip()
    row = get_valid_token(token_str)
    if not row:
        html = render_email_action_error('链接无效、已使用或已过期，请登录系统在待办中处理。')
        return Response(html, status=400, mimetype='text/html; charset=utf-8')

    task = TaskInstance.query.get(row.task_id)
    if not task:
        return Response('任务不存在', status=404, mimetype='text/html; charset=utf-8')

    if request.method == 'GET':
        html = render_email_action_page(task=task, action=row.action, token=token_str)
        return Response(html, mimetype='text/html; charset=utf-8')

    if request.form.get('confirm') != 'yes':
        html = render_email_action_page(
            task=task,
            action=row.action,
            token=token_str,
            error='已取消操作',
        )
        return Response(html, mimetype='text/html; charset=utf-8')

    comment = '邮件快速同意' if row.action == 'approve' else '邮件快速驳回'
    try:
        _engine.complete_task(
            task=task,
            action=row.action,
            actor_id=row.assignee_id,
            comment=comment,
        )
        mark_token_used(row)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        html = render_email_action_page(
            task=task,
            action=row.action,
            token=token_str,
            error=str(exc),
        )
        return Response(html, status=400, mimetype='text/html; charset=utf-8')

    label = '已同意' if row.action == 'approve' else '已驳回'
    html = render_email_action_page(
        task=task,
        action=row.action,
        token=token_str,
        success=f'操作成功：{label}。可关闭本页，或登录系统查看详情。',
    )
    return Response(html, mimetype='text/html; charset=utf-8')


@workflow_api.route('/tasks/badge-summary', methods=['GET'])
@login_required
def task_badge_summary():
    """导航角标：待办总数、他人发起且待本人处理的审批数。"""
    uid = current_user.id
    todo_count = TaskInstance.query.filter_by(assignee_id=uid, status='pending').count()
    participated_pending_count = (
        TaskInstance.query.join(
            WorkflowInstance,
            TaskInstance.instance_id == WorkflowInstance.id,
        )
        .filter(
            TaskInstance.assignee_id == uid,
            TaskInstance.status == 'pending',
            WorkflowInstance.initiator_id != uid,
        )
        .count()
    )
    return ok({
        'todo_count': todo_count,
        'participated_pending_count': participated_pending_count,
        'mine_unread_count': count_mine_unread_progress(uid),
    })


@workflow_api.route('/tasks/todo', methods=['GET'])
@login_required
def todo_tasks():
    from app.services.task_list_meta import query_user_tasks, task_list_row

    page = max(1, request.args.get('page', 1, type=int))
    page_size = min(100, max(1, request.args.get('page_size', 20, type=int)))
    keyword = (request.args.get('keyword') or '').strip() or None
    sector_id = request.args.get('sector_id', type=int)
    sort_field = (request.args.get('sort_field') or '').strip() or None
    sort_order = (request.args.get('sort_order') or '').strip() or None

    q = query_user_tasks(
        current_user.id,
        mode='todo',
        sector_id=sector_id,
        keyword=keyword,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        'items': [task_list_row(t) for t in rows],
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@workflow_api.route('/tasks/done', methods=['GET'])
@login_required
def done_tasks():
    from app.services.task_list_meta import query_user_tasks, task_list_row

    page = max(1, request.args.get('page', 1, type=int))
    page_size = min(100, max(1, request.args.get('page_size', 20, type=int)))
    keyword = (request.args.get('keyword') or '').strip() or None
    sector_id = request.args.get('sector_id', type=int)
    task_status = (request.args.get('task_status') or '').strip() or None
    sort_field = (request.args.get('sort_field') or '').strip() or None
    sort_order = (request.args.get('sort_order') or '').strip() or None

    q = query_user_tasks(
        current_user.id,
        mode='done',
        task_status=task_status,
        sector_id=sector_id,
        keyword=keyword,
        sort_field=sort_field,
        sort_order=sort_order,
    )
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        'items': [task_list_row(t) for t in rows],
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@workflow_api.route('/tasks/batch-complete', methods=['POST'])
@login_required
def batch_complete_tasks():
    data = request.get_json(silent=True) or {}
    raw_ids = data.get('task_ids') or []
    if not isinstance(raw_ids, list) or not raw_ids:
        return fail('请选择至少一条待办')
    action = (data.get('action') or 'approve').strip()
    if action != 'approve':
        return fail('批量操作目前仅支持同意')
    comment = (data.get('comment') or '同意').strip() or '同意'

    succeeded: list[int] = []
    failed: list[dict] = []
    from app.services.task_list_meta import task_can_quick_approve

    for raw in raw_ids:
        try:
            task_id = int(raw)
        except (TypeError, ValueError):
            failed.append({'task_id': raw, 'reason': '无效的任务编号'})
            continue
        task = TaskInstance.query.get(task_id)
        if not task or task.assignee_id != current_user.id:
            failed.append({'task_id': task_id, 'reason': '任务不存在或无权处理'})
            continue
        if task.status != 'pending':
            failed.append({'task_id': task_id, 'reason': '任务已处理'})
            continue
        if not task_can_quick_approve(task):
            failed.append({'task_id': task_id, 'reason': '需打开详情填写表单或签名'})
            continue
        try:
            _engine.complete_task(
                task=task,
                action=action,
                actor_id=current_user.id,
                comment=comment,
            )
            succeeded.append(task_id)
        except ValueError as exc:
            failed.append({'task_id': task_id, 'reason': str(exc)})
        except Exception as exc:
            failed.append({'task_id': task_id, 'reason': str(exc)})

    if not succeeded and failed:
        return fail(failed[0]['reason'], data={'succeeded': succeeded, 'failed': failed})
    try:
        from app.services.client_events import on_users_touched

        on_users_touched([current_user.id])
    except Exception:
        pass
    return ok(
        {'succeeded': succeeded, 'failed': failed},
        f'已成功处理 {len(succeeded)} 条' + (f'，{len(failed)} 条未处理' if failed else ''),
    )


@workflow_api.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    task = TaskInstance.query.get(task_id)
    if not task:
        return fail('任务不存在', status=404)
    return ok(_task_dict(task, detail=True))


@workflow_api.route('/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    task = TaskInstance.query.get(task_id)
    if not task:
        return fail('任务不存在', status=404)
    data = request.get_json(silent=True) or {}
    action = (data.get('action') or 'approve').strip()
    form_update = data.get('form')
    if form_update and isinstance(form_update, dict) and action == 'approve':
        definition = task.instance.definition
        schema = _resolve_form_schema(definition) if definition else {}
        merged = dict(parse_variables(task.instance.variables).get('form') or {})
        merged.update(form_update)
        from app.services.date_range_value import apply_date_range_auto_days
        apply_date_range_auto_days(
            schema, merged, task.instance.company_id, task.instance.initiator_id,
        )
        form_update = merged
        dup_errs = validate_form_receipt_duplicates(
            schema,
            merged,
            task.instance.company_id,
            ensure_instance_public_uuid(task.instance),
        )
        if dup_errs:
            return fail('；'.join(dup_errs))
    try:
        inst = _engine.complete_task(
            task=task,
            action=action,
            actor_id=current_user.id,
            comment=data.get('comment'),
            action_meta=data.get('action_meta'),
            form_update=form_update if isinstance(form_update, dict) else None,
        )
    except ValueError as exc:
        return fail(str(exc))
    try:
        from app.services.client_events import on_users_touched

        on_users_touched([current_user.id])
    except Exception:
        pass
    return ok(_instance_dict(inst), '已处理')


@workflow_api.route('/users/options', methods=['GET'])
@login_required
def user_options():
    rows = User.query.filter_by(is_active=True).order_by(User.username).all()
    return ok([
        {'id': u.id, 'username': u.username, 'display_name': u.display_label()}
        for u in rows
    ])


def _resolve_form_schema(wf: WorkflowDefinition) -> dict:
    return resolve_definition_schema(wf)


def _visible_for_company(d: WorkflowDefinition, company_id: int) -> bool:
    if d.scope_type == 'global':
        return True
    if d.scope_type == 'company':
        return d.company_id == company_id
    if d.scope_type == 'companies':
        try:
            ids = json.loads(d.company_ids or '[]')
        except (json.JSONDecodeError, TypeError):
            ids = []
        return company_id in ids
    return False


def _definition_dict(d: WorkflowDefinition, full: bool = False) -> dict:
    base = {
        'id': d.id,
        'key': d.key,
        'name': d.name,
        'version': d.version,
        'status': d.status,
        'scope_type': d.scope_type,
        'company_id': d.company_id,
        'company_ids': json.loads(d.company_ids) if d.company_ids else [],
    }
    if not full:
        return base
    base['form_schema'] = _resolve_form_schema(d)
    base['form_definition_id'] = d.form_definition_id
    base['process_graph'] = parse_graph(d.process_graph)
    base['settings'] = merge_settings(d.settings)
    return base


def _instance_dict_mine(inst: WorkflowInstance, user_id: int) -> dict:
    d = _instance_dict(inst, brief=True)
    d['can_withdraw'] = _instance_can_withdraw(inst, user_id)
    d['has_unread_update'] = instance_has_unread_progress(inst, user_id)
    return d


def _instance_dict_participated(inst: WorkflowInstance, user_id: int) -> dict:
    """与我相关的审批：他人发起，本人有待办、已处理或或签取消的节点。"""
    d = _instance_dict(inst, brief=True)
    d['can_withdraw'] = False
    initiator = User.query.get(inst.initiator_id) if inst.initiator_id else None
    d['initiator_name'] = initiator.display_label() if initiator else ''
    pending_task = (
        TaskInstance.query.filter_by(instance_id=inst.id, assignee_id=user_id, status='pending')
        .order_by(TaskInstance.id.desc())
        .first()
    )
    if pending_task:
        d['my_task_status'] = 'pending'
        d['my_completed_at'] = None
        d['has_pending_task'] = True
        return d
    closed_statuses = PARTICIPATED_TASK_STATUSES + ('cancelled',)
    last_task = (
        TaskInstance.query.filter_by(instance_id=inst.id, assignee_id=user_id)
        .filter(TaskInstance.status.in_(closed_statuses))
        .order_by(TaskInstance.completed_at.desc(), TaskInstance.id.desc())
        .first()
    )
    if last_task:
        status = last_task.status
        if status == 'reject':
            status = 'rejected'
        d['my_task_status'] = status
        d['my_completed_at'] = format_display_datetime(last_task.completed_at)
    d['has_pending_task'] = False
    return d


def _instance_row(inst: WorkflowInstance) -> dict:
    from app.services.instance_list_meta import enrich_instance_list_row

    initiator = User.query.get(inst.initiator_id) if inst.initiator_id else None
    dept = Department.query.get(inst.department_id) if inst.department_id else None
    sector_name = ''
    if inst.business_sector_id:
        s = BusinessSector.query.get(inst.business_sector_id)
        sector_name = s.name if s else ''
    updated = getattr(inst, 'updated_at', None) or inst.finished_at or inst.started_at
    row = {
        'id': inst.id,
        'public_uuid': ensure_instance_public_uuid(inst),
        'display_no': inst.display_no or str(inst.id),
        'definition_name': inst.definition.name if inst.definition else None,
        'business_sector_name': sector_name,
        'status': inst.status,
        'initiator_name': initiator.display_label() if initiator else '',
        'department_name': dept.name if dept else '',
        'started_at': format_display_datetime(inst.started_at),
        'updated_at': format_display_datetime(updated),
        'finished_at': format_display_datetime(inst.finished_at),
    }
    return enrich_instance_list_row(inst, row)


def _instance_dict(inst: WorkflowInstance, brief: bool = False) -> dict:
    from app.services.instance_list_meta import enrich_instance_list_row

    d = {
        'id': inst.id,
        'public_uuid': ensure_instance_public_uuid(inst),
        'display_no': inst.display_no or str(inst.id),
        'definition_id': inst.definition_id,
        'definition_name': inst.definition.name if inst.definition else None,
        'status': inst.status,
        'company_id': inst.company_id,
        'department_id': inst.department_id,
        'org_unit_id': inst.org_unit_id,
        'business_sector_id': inst.business_sector_id,
        'initiator_id': inst.initiator_id,
        'started_at': format_display_datetime(inst.started_at),
        'finished_at': format_display_datetime(inst.finished_at),
    }
    updated = getattr(inst, 'updated_at', None) or inst.finished_at or inst.started_at
    d['updated_at'] = format_display_datetime(updated)
    if brief:
        enrich_instance_list_row(inst, d)
    else:
        from app.services.instance_list_meta import attach_instance_status_meta

        attach_instance_status_meta(inst, d)
    if not brief:
        d['variables'] = parse_variables(inst.variables)
    return d


def _instance_flow_progress(inst: WorkflowInstance) -> dict:
    """实例审批流程图展示：当前节点、已完成节点、本节点等待时长起点。"""
    graph = (
        parse_graph(inst.definition.process_graph)
        if inst.definition
        else {'nodes': [], 'edges': []}
    )
    try:
        current_ids = json.loads(inst.current_node_ids or '[]')
    except (json.JSONDecodeError, TypeError):
        current_ids = []
    if not isinstance(current_ids, list):
        current_ids = []
    current_ids = [str(x) for x in current_ids if x]
    if not current_ids:
        current_ids = [
            t.node_id
            for t in inst.tasks.filter_by(status='pending').all()
            if t.node_id
        ]

    done = set()
    for row in InstanceTimeline.query.filter_by(instance_id=inst.id).all():
        if row.node_id and row.action in (
            'start',
            'approve',
            'complete',
            'auto_approve',
            'reject',
            'withdraw',
        ):
            done.add(row.node_id)
    for t in inst.tasks.filter(TaskInstance.status.in_(['approved', 'completed', 'rejected'])).all():
        if t.node_id:
            done.add(t.node_id)

    if inst.status in ('approved', 'rejected', 'cancelled') and inst.finished_at:
        for node in graph.get('nodes') or []:
            if node.get('type') == 'end' and node.get('id'):
                done.add(str(node['id']))
        done.add('end')

    step_started = None
    pending = [
        t
        for t in inst.tasks.filter_by(status='pending').all()
        if t.node_id and (not current_ids or t.node_id in current_ids)
    ]
    if pending:
        times = [t.created_at for t in pending if t.created_at]
        if times:
            step_started = min(times)

    return {
        'process_graph': graph,
        'current_node_ids': current_ids,
        'completed_node_ids': list(done),
        'step_started_at': step_started.isoformat() if step_started else None,
    }


def _instance_apply_org_snapshot(inst: WorkflowInstance) -> dict:
    """发起时选择的公司/组织与部门（查看、打印共用）。"""
    from app.models import Company, Department, User
    from app.services.org_service import build_department_path_under_org

    dept = Department.query.get(inst.department_id) if inst.department_id else None
    company = Company.query.get(inst.company_id) if inst.company_id else None
    org_unit = Department.query.get(inst.org_unit_id) if inst.org_unit_id else None
    org_label = org_unit.name if org_unit else (company.name if company else '')
    dept_name = dept.name if dept else ''
    dept_path = (
        build_department_path_under_org(inst.department_id, inst.org_unit_id)
        if inst.department_id
        else ''
    )
    initiator = User.query.get(inst.initiator_id) if inst.initiator_id else None
    return {
        'initiator_name': (initiator.display_name or initiator.username) if initiator else '',
        'company_name': org_label,
        'org_unit_name': org_unit.name if org_unit else '',
        'department_name': dept_name,
        'apply_department_path': dept_path,
    }


def _instance_detail(inst: WorkflowInstance) -> dict:
    import json

    from app.models import User

    data = _instance_dict(inst)
    data['display_no'] = inst.display_no or str(inst.id)
    data['definition_name'] = inst.definition.name if inst.definition else None
    data['variables'] = parse_variables(inst.variables)
    data.update(_instance_apply_org_snapshot(inst))
    data['settings'] = merge_settings(inst.definition.settings) if inst.definition else {}
    data['form_schema'] = _resolve_form_schema(inst.definition) if inst.definition else {}
    data['print_config'] = (data['form_schema'].get('print') or {}) if data.get('form_schema') else {}
    try:
        from app.services.print_template_service import resolve_print_schema

        pts = resolve_print_schema(data.get('print_config'))
        if pts:
            data['print_template_schema'] = pts
    except Exception:
        pass
    graph = (
        parse_graph(inst.definition.process_graph)
        if inst.definition
        else {'nodes': [], 'edges': []}
    )
    timeline_rows = []
    for t in (
        InstanceTimeline.query.filter_by(instance_id=inst.id)
        .order_by(InstanceTimeline.created_at)
        .all()
    ):
        actor = User.query.get(t.actor_id) if t.actor_id else None
        payload = {}
        if t.payload:
            try:
                payload = json.loads(t.payload) if isinstance(t.payload, str) else (t.payload or {})
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
        timeline_rows.append(
            {
                'id': t.id,
                'actor_id': t.actor_id,
                'actor_name': actor.display_label() if actor else ('系统' if t.action == 'auto_approve' else ''),
                'action': t.action,
                'node_id': t.node_id,
                'node_name': resolve_node_display_name(find_node(graph, t.node_id), t.node_id)
                if t.node_id
                else None,
                'comment': t.comment,
                'created_at': format_display_datetime(t.created_at),
                'signature_path': payload.get('signature_path'),
                'signature_data': payload.get('signature_data'),
            },
        )
    data['timeline'] = timeline_rows
    data['tasks'] = [
        _task_dict(t, detail=False)
        for t in inst.tasks.order_by(TaskInstance.created_at).all()
    ]
    data['flow_progress'] = _instance_flow_progress(inst)
    return data


def _task_dict(t: TaskInstance, detail: bool = False) -> dict:
    inst = t.instance
    settings = merge_settings(inst.definition.settings) if inst and inst.definition else {}
    graph = parse_graph(inst.definition.process_graph) if inst and inst.definition else {}
    d = {
        'id': t.id,
        'instance_id': t.instance_id,
        'node_id': t.node_id,
        'node_name': resolve_node_display_name(find_node(graph, t.node_id), t.node_id),
        'node_type': t.node_type,
        'status': t.status,
        'assignee_id': t.assignee_id,
        'created_at': format_display_datetime(t.created_at),
        'completed_at': format_display_datetime(t.completed_at),
        'instance': _instance_dict(inst, brief=True) if inst else None,
    }
    meta = {}
    if t.action_meta:
        try:
            meta = json.loads(t.action_meta) if isinstance(t.action_meta, str) else (t.action_meta or {})
        except (TypeError, ValueError, json.JSONDecodeError):
            meta = {}
    d['task_meta'] = meta
    d['is_add_sign_task'] = bool(meta.get('add_sign'))
    d['add_sign_mode'] = meta.get('add_sign_mode')
    d['is_on_hold'] = t.status == 'on_hold'
    if meta.get('add_sign') and meta.get('requested_by'):
        req = User.query.get(int(meta['requested_by']))
        d['add_sign_requested_by_name'] = req.display_label() if req else ''

    if detail:
        d['settings'] = settings
        d['form_schema'] = (
            _resolve_form_schema(inst.definition) if inst and inst.definition else {}
        )
        d['print_config'] = (d['form_schema'].get('print') or {}) if d['form_schema'] else {}
        try:
            from app.services.print_template_service import resolve_print_schema

            pts = resolve_print_schema(d.get('print_config'))
            if pts:
                d['print_template_schema'] = pts
        except Exception:
            pass
        d['variables'] = parse_variables(inst.variables) if inst else {}
        node = next((n for n in graph.get('nodes') or [] if n.get('id') == t.node_id), {})
        d['node_config'] = node.get('config') or {}
        if inst:
            org = _instance_apply_org_snapshot(inst)
            d['initiator_name'] = org['initiator_name']
            d['apply_org'] = org
            base_inst = d.get('instance') or {}
            d['instance'] = {**base_inst, **org}
    return d
