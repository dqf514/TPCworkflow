# -*- coding: utf-8 -*-
from flask import Blueprint, request
from flask_login import login_required

from app.api.admin import _require_admin
from app.extensions import db
from app.models.llm_provider import LlmProvider, PROVIDER_TYPES
from app.services.llm_client import (
    mark_default_flags,
    provider_to_dict,
    record_test_result,
    test_provider_connection,
)
from app.utils.response import fail, ok

llm_providers_api = Blueprint('llm_providers_api', __name__)


def _next_sort_order() -> int:
    last = LlmProvider.query.order_by(LlmProvider.sort_order.desc(), LlmProvider.id.desc()).first()
    if not last:
        return 0
    return int(last.sort_order or 0) + 1


def _resolve_api_key(data: dict, row: LlmProvider | None = None) -> str:
    if 'api_key' in data:
        key = (data.get('api_key') or '').strip()
        if key:
            return key
        if row and (row.api_key or '').strip():
            return row.api_key or ''
        return ''
    return (row.api_key or '').strip() if row else ''


@llm_providers_api.route('/admin/llm-providers', methods=['GET'])
@login_required
def admin_list_llm_providers():
    err = _require_admin()
    if err:
        return err
    rows = LlmProvider.query.order_by(LlmProvider.sort_order.asc(), LlmProvider.id.asc()).all()
    data = mark_default_flags([provider_to_dict(r) for r in rows])
    return ok(data)


@llm_providers_api.route('/admin/llm-providers', methods=['POST'])
@login_required
def admin_create_llm_provider():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    base_url = (data.get('base_url') or '').strip()
    if not base_url:
        return fail('请填写 Base URL')
    ptype = (data.get('provider_type') or 'openai_compatible').strip()
    if ptype not in PROVIDER_TYPES:
        return fail('接口类型无效')

    row = LlmProvider(
        name=(data.get('name') or '').strip(),
        provider_type=ptype,
        base_url=base_url,
        api_key=(data.get('api_key') or '').strip(),
        model_name=(data.get('model_name') or '').strip(),
        sort_order=int(data.get('sort_order')) if data.get('sort_order') is not None else _next_sort_order(),
        is_active=data.get('is_active', True) is not False,
    )
    db.session.add(row)
    db.session.commit()
    item = provider_to_dict(row)
    item['is_default'] = False
    return ok(item, '已添加')


@llm_providers_api.route('/admin/llm-providers/<int:provider_id>', methods=['PUT'])
@login_required
def admin_update_llm_provider(provider_id: int):
    err = _require_admin()
    if err:
        return err
    row = LlmProvider.query.get(provider_id)
    if not row:
        return fail('记录不存在', status=404)
    data = request.get_json(silent=True) or {}

    if 'name' in data:
        row.name = (data.get('name') or '').strip()
    if 'provider_type' in data:
        ptype = (data.get('provider_type') or '').strip()
        if ptype not in PROVIDER_TYPES:
            return fail('接口类型无效')
        row.provider_type = ptype
    if 'base_url' in data:
        base_url = (data.get('base_url') or '').strip()
        if not base_url:
            return fail('请填写 Base URL')
        row.base_url = base_url
    if 'api_key' in data:
        key = (data.get('api_key') or '').strip()
        if key:
            row.api_key = key
    if 'model_name' in data:
        row.model_name = (data.get('model_name') or '').strip()
    if 'is_active' in data:
        row.is_active = bool(data.get('is_active'))
    if 'sort_order' in data:
        row.sort_order = int(data.get('sort_order') or 0)

    db.session.commit()
    rows = LlmProvider.query.order_by(LlmProvider.sort_order.asc(), LlmProvider.id.asc()).all()
    data_out = mark_default_flags([provider_to_dict(r) for r in rows])
    current = next((x for x in data_out if x['id'] == row.id), provider_to_dict(row))
    return ok(current, '已更新')


@llm_providers_api.route('/admin/llm-providers/<int:provider_id>', methods=['DELETE'])
@login_required
def admin_delete_llm_provider(provider_id: int):
    err = _require_admin()
    if err:
        return err
    row = LlmProvider.query.get(provider_id)
    if not row:
        return fail('记录不存在', status=404)
    db.session.delete(row)
    db.session.commit()
    return ok(message='已删除')


@llm_providers_api.route('/admin/llm-providers/reorder', methods=['POST'])
@login_required
def admin_reorder_llm_providers():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    ids = data.get('ids') or []
    if not isinstance(ids, list) or not ids:
        return fail('请提供排序后的 ID 列表')

    rows = {r.id: r for r in LlmProvider.query.filter(LlmProvider.id.in_(ids)).all()}
    if len(rows) != len(ids):
        return fail('存在无效的配置 ID')

    for idx, pid in enumerate(ids):
        row = rows.get(int(pid))
        if row:
            row.sort_order = idx
    db.session.commit()

    ordered = LlmProvider.query.order_by(LlmProvider.sort_order.asc(), LlmProvider.id.asc()).all()
    return ok(mark_default_flags([provider_to_dict(r) for r in ordered]), '优先级已更新')


@llm_providers_api.route('/admin/llm-providers/test', methods=['POST'])
@login_required
def admin_test_llm_provider_inline():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    provider_id = data.get('id')
    row = LlmProvider.query.get(int(provider_id)) if provider_id else None

    ptype = (data.get('provider_type') or (row.provider_type if row else '') or 'openai_compatible').strip()
    base_url = (data.get('base_url') or (row.base_url if row else '') or '').strip()
    api_key = _resolve_api_key(data, row)
    model_name = (data.get('model_name') or (row.model_name if row else '') or '').strip()

    if not base_url:
        return fail('请填写 Base URL')

    ok_test, message = test_provider_connection(ptype, base_url, api_key, model_name)
    if row:
        record_test_result(row, ok_test, message)
    if not ok_test:
        return fail(message)
    return ok({'message': message}, message)


@llm_providers_api.route('/admin/llm-providers/<int:provider_id>/test', methods=['POST'])
@login_required
def admin_test_llm_provider_saved(provider_id: int):
    err = _require_admin()
    if err:
        return err
    row = LlmProvider.query.get(provider_id)
    if not row:
        return fail('记录不存在', status=404)

    data = request.get_json(silent=True) or {}
    ptype = (data.get('provider_type') or row.provider_type).strip()
    base_url = (data.get('base_url') or row.base_url).strip()
    api_key = _resolve_api_key(data, row)
    model_name = (data.get('model_name') or row.model_name or '').strip()

    ok_test, message = test_provider_connection(ptype, base_url, api_key, model_name)
    record_test_result(row, ok_test, message)
    if not ok_test:
        return fail(message)
    return ok({'message': message}, message)
