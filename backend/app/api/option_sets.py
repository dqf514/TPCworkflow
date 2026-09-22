# -*- coding: utf-8 -*-
import json
import re
import uuid

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import OptionSet, OptionSetColumn, OptionSetItem, OptionSetRecord, User
from app.models.option_set import SET_TYPE_OPTION, SET_TYPE_RECORD, RECORD_SET_DATA_SCOPES, SCOPE_COMPANY, SCOPE_MIXED, SCOPE_PERSONAL
from app.api.admin import _require_admin
from app.services.record_set_service import (
    build_record_dict,
    column_dict,
    get_record_set_by_code,
    list_records_payload,
    normalize_column_span,
    normalize_record_data,
    record_set_data_scope,
    upsert_personal_record,
    _column_keys,
)
from app.utils.response import fail, ok

option_sets_api = Blueprint('option_sets_api', __name__)

_FIELD_KEY_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$')


def _format_option_label(name: str, code: str) -> str:
    name = (name or '').strip()
    code = (code or '').strip()
    if name and code:
        return f'{name}（{code}）'
    return name or code


def _item_dict(item: OptionSetItem) -> dict:
    return {
        'id': item.id,
        'code': item.code,
        'name': item.name,
        'label': _format_option_label(item.name, item.code),
        'value': item.code,
        'sort_order': item.sort_order,
        'is_active': item.is_active,
    }


def _column_dict(col: OptionSetColumn) -> dict:
    return column_dict(col)


def _record_dict(rec: OptionSetRecord, columns: list[OptionSetColumn] | None = None) -> dict:
    return build_record_dict(rec, columns)


def _set_dict(s: OptionSet, *, with_items: bool = False, with_record: bool = False) -> dict:
    st = s.set_type or SET_TYPE_OPTION
    out = {
        'id': s.id,
        'code': s.code,
        'name': s.name,
        'set_type': st,
        'data_scope': record_set_data_scope(s) if st == SET_TYPE_RECORD else SCOPE_MIXED,
        'description': s.description or '',
        'sort_order': s.sort_order,
        'is_active': s.is_active,
    }
    if with_items and st == SET_TYPE_OPTION:
        rows = s.items.order_by(OptionSetItem.sort_order, OptionSetItem.id).all()
        out['items'] = [_item_dict(i) for i in rows if i.is_active]
    if with_record or (with_items and st == SET_TYPE_RECORD):
        cols = s.columns.order_by(OptionSetColumn.sort_order, OptionSetColumn.id).all()
        out['columns'] = [_column_dict(c) for c in cols]
        if with_items or with_record:
            rows = (
                s.records.filter(
                    OptionSetRecord.owner_user_id.is_(None),
                    OptionSetRecord.is_active.is_(True),
                )
                .order_by(OptionSetRecord.sort_order, OptionSetRecord.id)
                .all()
            )
            out['records'] = [_record_dict(r, cols) for r in rows]
    return out


def _filter_set_type(q, set_type: str | None):
    if set_type in (SET_TYPE_OPTION, SET_TYPE_RECORD):
        return q.filter_by(set_type=set_type)
    return q


@option_sets_api.route('/option-sets', methods=['GET'])
@login_required
def list_option_sets():
    active_only = request.args.get('active_only', '1') != '0'
    set_type = (request.args.get('set_type') or '').strip() or None
    q = OptionSet.query
    q = _filter_set_type(q, set_type)
    if active_only:
        q = q.filter_by(is_active=True)
    rows = q.order_by(OptionSet.sort_order, OptionSet.id).all()
    return ok([_set_dict(s) for s in rows])


@option_sets_api.route('/option-sets/<string:code>/options', methods=['GET'])
@login_required
def list_option_set_items(code):
    s = OptionSet.query.filter_by(code=code.strip(), is_active=True).first()
    if not s:
        return fail('配置表不存在或已停用', status=404)
    if (s.set_type or SET_TYPE_OPTION) != SET_TYPE_OPTION:
        return fail('该配置表不是选项配置表', status=400)
    rows = (
        s.items.filter_by(is_active=True)
        .order_by(OptionSetItem.sort_order, OptionSetItem.id)
        .all()
    )
    return ok([_item_dict(i) for i in rows])


@option_sets_api.route('/option-sets/<string:code>/records', methods=['GET'])
@login_required
def list_option_set_records(code):
    s = get_record_set_by_code(code)
    if not s:
        return fail('配置表不存在或已停用', status=404)
    include_company = request.args.get('include_company', '1') != '0'
    include_personal = request.args.get('include_personal', '1') != '0'
    return ok(
        list_records_payload(
            s,
            current_user.id,
            include_company=include_company,
            include_personal=include_personal,
        ),
    )


@option_sets_api.route('/me/record-sets', methods=['GET'])
@login_required
def my_record_sets_overview():
    """个人中心：已启用的控件配置表及本人数据条数。"""
    rows = (
        OptionSet.query.filter_by(is_active=True, set_type=SET_TYPE_RECORD)
        .order_by(OptionSet.sort_order, OptionSet.id)
        .all()
    )
    out = []
    for s in rows:
        scope = record_set_data_scope(s)
        if scope == SCOPE_COMPANY:
            continue
        cnt = s.records.filter_by(owner_user_id=current_user.id, is_active=True).count()
        out.append({
            'id': s.id,
            'code': s.code,
            'name': s.name,
            'description': s.description or '',
            'data_scope': scope,
            'personal_count': cnt,
        })
    return ok(out)


@option_sets_api.route('/me/record-sets/<string:code>', methods=['GET'])
@login_required
def my_record_set_detail(code):
    s = get_record_set_by_code(code)
    if not s:
        return fail('配置表不存在或已停用', status=404)
    return ok(
        list_records_payload(
            s,
            current_user.id,
            include_company=False,
            include_personal=True,
        ),
    )


@option_sets_api.route('/me/record-sets/<string:code>/records', methods=['POST'])
@login_required
def my_create_record(code):
    s = get_record_set_by_code(code)
    if not s:
        return fail('配置表不存在或已停用', status=404)
    if record_set_data_scope(s) == SCOPE_COMPANY:
        return fail('该配置表为公司级，请在系统设置中维护公司数据', status=400)
    data = request.get_json(silent=True) or {}
    row_code = (data.get('row_code') or '').strip()
    payload = {'row_code': row_code, 'data': data.get('data') if isinstance(data.get('data'), dict) else data}
    col_keys = _column_keys(s)
    clean = normalize_record_data(payload.get('data'), col_keys)
    if not any(clean.values()):
        return fail('请至少填写一个字段')
    from app.services.record_set_service import find_company_record_by_data

    if find_company_record_by_data(s, clean):
        return fail('该内容与已有公司配置相同，无需保存到个人')
    rec = upsert_personal_record(s, current_user.id, payload)
    if not rec:
        return fail('保存失败，请检查填写内容')
    db.session.commit()
    cols = s.columns.order_by(OptionSetColumn.sort_order, OptionSetColumn.id).all()
    return ok(_record_dict(rec, cols), '已保存')


@option_sets_api.route('/me/record-sets/<string:code>/records/<string:row_code>', methods=['PUT'])
@login_required
def my_update_record(code, row_code):
    s = get_record_set_by_code(code)
    if not s:
        return fail('配置表不存在或已停用', status=404)
    if record_set_data_scope(s) == SCOPE_COMPANY:
        return fail('该配置表为公司级，请在系统设置中维护公司数据', status=400)
    rec = OptionSetRecord.query.filter_by(
        option_set_id=s.id,
        owner_user_id=current_user.id,
        row_code=row_code.strip(),
    ).first()
    if not rec:
        return fail('记录不存在', status=404)
    data = request.get_json(silent=True) or {}
    col_keys = _column_keys(s)
    clean = normalize_record_data(data.get('data') if isinstance(data.get('data'), dict) else data, col_keys)
    if not any(clean.values()):
        return fail('请至少填写一个字段')
    rec.set_data(clean)
    rec.is_active = True
    db.session.commit()
    cols = s.columns.order_by(OptionSetColumn.sort_order, OptionSetColumn.id).all()
    return ok(_record_dict(rec, cols), '已保存')


@option_sets_api.route('/me/record-sets/<string:code>/records/<string:row_code>', methods=['DELETE'])
@login_required
def my_delete_record(code, row_code):
    s = get_record_set_by_code(code)
    if not s:
        return fail('配置表不存在或已停用', status=404)
    if record_set_data_scope(s) == SCOPE_COMPANY:
        return fail('该配置表为公司级，请在系统设置中维护公司数据', status=400)
    rec = OptionSetRecord.query.filter_by(
        option_set_id=s.id,
        owner_user_id=current_user.id,
        row_code=row_code.strip(),
    ).first()
    if not rec:
        return fail('记录不存在', status=404)
    db.session.delete(rec)
    db.session.commit()
    return ok(message='已删除')


@option_sets_api.route('/admin/option-sets/<int:set_id>/personal-records', methods=['GET'])
@login_required
def admin_list_personal_records(set_id):
    err = _require_admin()
    if err:
        return err
    s = OptionSet.query.get(set_id)
    if not s:
        return fail('配置表不存在', status=404)
    if (s.set_type or SET_TYPE_OPTION) != SET_TYPE_RECORD:
        return fail('该配置表不是控件配置表', status=400)
    if record_set_data_scope(s) == SCOPE_PERSONAL:
        return fail('个人级配置表的数据仅本人可见，管理员无法查看', status=403)
    cols = s.columns.order_by(OptionSetColumn.sort_order, OptionSetColumn.id).all()
    rows = (
        s.records.filter(
            OptionSetRecord.owner_user_id.isnot(None),
            OptionSetRecord.is_active.is_(True),
        )
        .order_by(OptionSetRecord.owner_user_id, OptionSetRecord.sort_order, OptionSetRecord.id)
        .all()
    )
    user_ids = {r.owner_user_id for r in rows if r.owner_user_id}
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}
    out = []
    for r in rows:
        d = _record_dict(r, cols)
        u = users.get(r.owner_user_id)
        d['owner_display_name'] = (u.display_name if u else '') or (u.email if u else '')
        d['owner_user_id'] = r.owner_user_id
        out.append(d)
    return ok({'columns': [_column_dict(c) for c in cols], 'records': out})


@option_sets_api.route('/admin/option-sets', methods=['GET'])
@login_required
def admin_list_option_sets():
    err = _require_admin()
    if err:
        return err
    set_type = (request.args.get('set_type') or '').strip() or None
    q = OptionSet.query
    q = _filter_set_type(q, set_type)
    rows = q.order_by(OptionSet.sort_order, OptionSet.id).all()
    return ok([_set_dict(s, with_items=True, with_record=True) for s in rows])


@option_sets_api.route('/admin/option-sets/<int:set_id>', methods=['GET'])
@login_required
def admin_get_option_set(set_id):
    err = _require_admin()
    if err:
        return err
    s = OptionSet.query.get(set_id)
    if not s:
        return fail('配置表不存在', status=404)
    return ok(_set_dict(s, with_items=True, with_record=True))


@option_sets_api.route('/admin/option-sets', methods=['POST'])
@login_required
def admin_create_option_set():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    return _save_option_set(None, data, create=True)


@option_sets_api.route('/admin/option-sets/<int:set_id>', methods=['PUT'])
@login_required
def admin_update_option_set(set_id):
    err = _require_admin()
    if err:
        return err
    s = OptionSet.query.get(set_id)
    if not s:
        return fail('配置表不存在', status=404)
    data = request.get_json(silent=True) or {}
    return _save_option_set(s, data, create=False)


@option_sets_api.route('/admin/option-sets/<int:set_id>', methods=['DELETE'])
@login_required
def admin_delete_option_set(set_id):
    err = _require_admin()
    if err:
        return err
    s = OptionSet.query.get(set_id)
    if not s:
        return fail('配置表不存在', status=404)
    db.session.delete(s)
    db.session.commit()
    return ok(message='已删除')


def _save_option_set(s: OptionSet | None, data: dict, *, create: bool):
    code = (data.get('code') or (s.code if s else '') or '').strip()
    name = (data.get('name') or (s.name if s else '') or '').strip()
    if not code or not name:
        return fail('请填写编码与名称')
    set_type = (data.get('set_type') or (s.set_type if s else '') or SET_TYPE_OPTION).strip()
    if set_type not in (SET_TYPE_OPTION, SET_TYPE_RECORD):
        return fail('无效的配置表类型')
    data_scope_raw = (data.get('data_scope') or (getattr(s, 'data_scope', None) if s else '') or SCOPE_MIXED).strip()
    if data_scope_raw not in RECORD_SET_DATA_SCOPES:
        return fail('无效的数据范围')

    if create:
        if OptionSet.query.filter_by(code=code).first():
            return fail('编码已存在')
        s = OptionSet(
            code=code,
            name=name,
            set_type=set_type,
            data_scope=data_scope_raw if set_type == SET_TYPE_RECORD else SCOPE_MIXED,
            description=(data.get('description') or '').strip(),
            sort_order=int(data.get('sort_order') or 0),
            is_active=data.get('is_active', True) is not False,
        )
        db.session.add(s)
        db.session.flush()
    else:
        if 'code' in data:
            other = OptionSet.query.filter(OptionSet.code == code, OptionSet.id != s.id).first()
            if other:
                return fail('编码已存在')
            s.code = code
        if 'name' in data:
            s.name = name
        if 'set_type' in data and not create:
            if s.set_type != set_type:
                return fail('创建后不可更改配置表类型')
        if 'description' in data:
            s.description = (data.get('description') or '').strip()
        if 'sort_order' in data:
            s.sort_order = int(data.get('sort_order') or 0)
        if 'is_active' in data:
            s.is_active = bool(data.get('is_active'))
        if 'data_scope' in data and (s.set_type or SET_TYPE_OPTION) == SET_TYPE_RECORD:
            s.data_scope = data_scope_raw

    st = s.set_type or SET_TYPE_OPTION
    scope = record_set_data_scope(s) if st == SET_TYPE_RECORD else SCOPE_MIXED
    if st == SET_TYPE_OPTION:
        if 'items' in data:
            _replace_items(s, data.get('items') or [])
    else:
        if 'columns' in data:
            _replace_columns(s, data.get('columns') or [])
        if 'records' in data and scope != SCOPE_PERSONAL:
            _replace_records(s, data.get('records') or [])

    db.session.commit()
    msg = '已创建' if create else '已保存'
    return ok(_set_dict(s, with_items=True, with_record=True), msg)


def _replace_items(option_set: OptionSet, items: list) -> None:
    OptionSetItem.query.filter_by(option_set_id=option_set.id).delete(synchronize_session=False)
    seen = set()
    for idx, raw in enumerate(items):
        if not isinstance(raw, dict):
            continue
        code = (raw.get('code') or '').strip()
        name = (raw.get('name') or '').strip()
        if not code or not name:
            continue
        if code in seen:
            continue
        seen.add(code)
        db.session.add(
            OptionSetItem(
                option_set_id=option_set.id,
                code=code,
                name=name,
                sort_order=int(raw.get('sort_order') if raw.get('sort_order') is not None else idx),
                is_active=raw.get('is_active', True) is not False,
            ),
        )


def _normalize_field_key(raw: str, fallback: str) -> str:
    key = (raw or '').strip()
    if not key:
        key = fallback
    key = re.sub(r'[^\w]', '_', key)
    if not key or not _FIELD_KEY_RE.match(key):
        key = f'f_{fallback}'
    return key[:64]


def _replace_columns(option_set: OptionSet, columns: list) -> None:
    old_cols = {
        c.field_key: c
        for c in option_set.columns.order_by(OptionSetColumn.sort_order).all()
    }
    OptionSetColumn.query.filter_by(option_set_id=option_set.id).delete(synchronize_session=False)
    seen = set()
    for idx, raw in enumerate(columns):
        if not isinstance(raw, dict):
            continue
        label = (raw.get('label') or '').strip()
        if not label:
            continue
        field_key = _normalize_field_key(
            str(raw.get('field_key') or ''),
            f'col_{idx + 1}',
        )
        if field_key in seen:
            field_key = f'{field_key}_{idx}'
        seen.add(field_key)
        db.session.add(
            OptionSetColumn(
                option_set_id=option_set.id,
                field_key=field_key,
                label=label,
                sort_order=int(raw.get('sort_order') if raw.get('sort_order') is not None else idx),
                span=normalize_column_span(raw.get('span')),
            ),
        )
    db.session.flush()
    new_keys = seen
    for rec in option_set.records.filter(OptionSetRecord.owner_user_id.is_(None)).all():
        data = rec.get_data()
        rec.set_data({k: data[k] for k in data if k in new_keys})


def _replace_records(option_set: OptionSet, records: list) -> None:
    cols = {c.field_key for c in option_set.columns.all()}
    OptionSetRecord.query.filter(
        OptionSetRecord.option_set_id == option_set.id,
        OptionSetRecord.owner_user_id.is_(None),
    ).delete(synchronize_session=False)
    seen = set()
    for idx, raw in enumerate(records):
        if not isinstance(raw, dict):
            continue
        row_code = (raw.get('row_code') or '').strip()
        if not row_code:
            row_code = f'row_{uuid.uuid4().hex[:8]}'
        if row_code in seen:
            continue
        seen.add(row_code)
        data = raw.get('data') if isinstance(raw.get('data'), dict) else {}
        if not data and isinstance(raw, dict):
            data = {k: v for k, v in raw.items() if k in cols and k not in ('row_code', 'sort_order', 'is_active', 'id')}
        clean = {k: str(data.get(k) or '').strip() for k in cols}
        if not any(clean.values()):
            continue
        rec = OptionSetRecord(
            option_set_id=option_set.id,
            row_code=row_code,
            sort_order=int(raw.get('sort_order') if raw.get('sort_order') is not None else idx),
            is_active=raw.get('is_active', True) is not False,
        )
        rec.set_data(clean)
        db.session.add(rec)
