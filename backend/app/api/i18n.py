# -*- coding: utf-8 -*-
from flask import Blueprint, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import I18nLocale, I18nMessage
from app.services.i18n import bump_bundle_version, get_bundle_version, load_messages, t
from app.services.i18n_catalog import build_seed_catalog, list_catalog_entries
from app.utils.locale import resolve_request_locale
from app.utils.response import fail, ok

i18n_api = Blueprint('i18n_api', __name__)

DEFAULT_NAMESPACES = (
    'common',
    'menu',
    'auth',
    'login',
    'workflow',
    'monitor',
    'dashboard',
    'apply',
    'validation',
    'admin',
    'studio',
    'org',
    'designer',
    'flowRole',
    'flowDesign',
    'wfSettings',
    'settings',
)


@i18n_api.route('/locales', methods=['GET'])
def list_locales():
    rows = I18nLocale.query.filter_by(is_enabled=True).order_by(
        I18nLocale.sort_order,
    ).all()
    return ok([
        {
            'code': r.code,
            'name': r.name,
            'native_name': r.native_name,
            'is_default': r.is_default,
        }
        for r in rows
    ])


@i18n_api.route('/messages', methods=['GET'])
def get_messages():
    locale = request.args.get('locale') or resolve_request_locale()
    ns_raw = request.args.get('namespaces', '')
    namespaces = [x.strip() for x in ns_raw.split(',') if x.strip()] or list(DEFAULT_NAMESPACES)
    version = get_bundle_version(locale)
    client_ver = request.headers.get('X-I18n-Version')
    if client_ver and str(client_ver) == str(version):
        return '', 304
    messages = load_messages(locale, namespaces)
    resp = ok({'version': version, 'messages': messages})
    resp[0].headers['X-I18n-Version'] = str(version)
    return resp


def _truthy_arg(name: str) -> bool:
    v = (request.args.get(name) or '').strip().lower()
    return v in ('1', 'true', 'yes', 'on')


@i18n_api.route('/admin/catalog', methods=['GET'])
@login_required
def admin_list_catalog():
    """返回种子中全部词条键名及中英参考译文。"""
    if not _can_manage_i18n():
        return fail('无权限', status=403)
    namespace = (request.args.get('namespace') or '').strip() or None
    q = (request.args.get('q') or '').strip() or None
    items = list_catalog_entries(namespace=namespace, q=q)
    return ok({'items': items, 'total': len(items)})


@i18n_api.route('/admin/messages', methods=['GET'])
@login_required
def admin_list_messages():
    if not _can_manage_i18n():
        return fail('无权限', status=403)
    locale = (request.args.get('locale') or '').strip()
    if _truthy_arg('coverage') or request.args.get('mode') == 'coverage':
        return _admin_list_messages_coverage(locale)
    namespace = request.args.get('namespace')
    q = request.args.get('q')
    empty_only = _truthy_arg('empty_only')
    query = I18nMessage.query
    if locale:
        query = query.filter_by(locale=locale)
    if namespace:
        query = query.filter_by(namespace=namespace)
    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(
                I18nMessage.msg_key.like(like),
                I18nMessage.msg_value.like(like),
            ),
        )
    if empty_only:
        query = query.filter(
            db.or_(
                I18nMessage.msg_value.is_(None),
                I18nMessage.msg_value == '',
            ),
        )
    page = max(1, int(request.args.get('page') or 1))
    per_page = min(max(1, int(request.args.get('per_page') or 100)), 500)
    total = query.count()
    rows = (
        query.order_by(I18nMessage.namespace, I18nMessage.msg_key)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return ok({
        'items': [
            {
                'id': r.id,
                'namespace': r.namespace,
                'msg_key': r.msg_key,
                'locale': r.locale,
                'msg_value': r.msg_value or '',
                'description': r.description or '',
            }
            for r in rows
        ],
        'total': total,
        'page': page,
        'per_page': per_page,
    })


def _admin_list_messages_coverage(locale: str):
    """按种子目录列出全部键，合并当前语言库内译文，支持仅空译文筛选。"""
    if not locale:
        return fail('请指定 locale')
    namespace = (request.args.get('namespace') or '').strip() or None
    q = (request.args.get('q') or '').strip() or None
    empty_only = _truthy_arg('empty_only')
    page = max(1, int(request.args.get('page') or 1))
    per_page = min(max(1, int(request.args.get('per_page') or 50)), 500)

    catalog = build_seed_catalog()
    db_rows = I18nMessage.query.filter_by(locale=locale)
    if namespace:
        db_rows = db_rows.filter_by(namespace=namespace)
    db_map: dict[tuple[str, str], I18nMessage] = {
        (r.namespace, r.msg_key): r for r in db_rows.all()
    }
    for (ns, key) in db_map:
        catalog.setdefault((ns, key), {'zh_seed': '', 'en_seed': ''})

    ql = (q or '').lower()
    merged: list[dict] = []
    ref_locale = 'zh-CN' if locale == 'en-US' else 'en-US'
    ref_rows = {
        (r.namespace, r.msg_key): r
        for r in I18nMessage.query.filter_by(locale=ref_locale).all()
    }

    for (ns, key), seeds in sorted(catalog.items(), key=lambda x: (x[0][0], x[0][1])):
        if namespace and ns != namespace:
            continue
        zh_ref = seeds.get('zh_seed') or ''
        en_ref = seeds.get('en_seed') or ''
        if ql:
            row = db_map.get((ns, key))
            cur_val = (row.msg_value if row else '') or ''
            hay = ' '.join([ns, key, zh_ref, en_ref, cur_val]).lower()
            if ql not in hay:
                continue
        row = db_map.get((ns, key))
        msg_value = (row.msg_value if row else '') or ''
        is_empty = not msg_value.strip()
        if empty_only and not is_empty:
            continue
        ref_row = ref_rows.get((ns, key))
        ref_value = (ref_row.msg_value if ref_row else '') or (
            zh_ref if ref_locale == 'zh-CN' else en_ref
        )
        merged.append({
            'id': row.id if row else None,
            'namespace': ns,
            'msg_key': key,
            'locale': locale,
            'msg_value': msg_value,
            'description': (row.description or '') if row else '',
            'zh_seed': zh_ref,
            'en_seed': en_ref,
            'ref_locale': ref_locale,
            'ref_value': ref_value,
            'is_empty': is_empty,
            'in_db': row is not None,
        })

    total = len(merged)
    start = (page - 1) * per_page
    items = merged[start : start + per_page]
    return ok({
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'coverage': True,
    })


@i18n_api.route('/admin/messages', methods=['POST'])
@login_required
def admin_upsert_message():
    if not _can_manage_i18n():
        return fail('无权限', status=403)
    data = request.get_json(silent=True) or {}
    namespace = (data.get('namespace') or '').strip()
    msg_key = (data.get('msg_key') or '').strip()
    locale = (data.get('locale') or '').strip()
    msg_value = data.get('msg_value')
    if not namespace or not msg_key or not locale:
        return fail('namespace、msg_key、locale 不能为空')
    row = I18nMessage.query.filter_by(
        namespace=namespace,
        msg_key=msg_key,
        locale=locale,
    ).first()
    if row:
        row.msg_value = msg_value or ''
        row.description = data.get('description')
        row.updated_by = current_user.id
    else:
        row = I18nMessage(
            namespace=namespace,
            msg_key=msg_key,
            locale=locale,
            msg_value=msg_value or '',
            description=data.get('description'),
            updated_by=current_user.id,
        )
        db.session.add(row)
    db.session.commit()
    bump_bundle_version(locale)
    return ok({'id': row.id}, '已保存')


@i18n_api.route('/admin/messages/<int:msg_id>', methods=['PUT'])
@login_required
def admin_update_message(msg_id: int):
    if not _can_manage_i18n():
        return fail('无权限', status=403)
    row = I18nMessage.query.get(msg_id)
    if not row:
        return fail('词条不存在', status=404)
    data = request.get_json(silent=True) or {}
    if 'msg_value' in data:
        row.msg_value = data.get('msg_value') or ''
    if 'description' in data:
        row.description = (data.get('description') or '').strip() or None
    row.updated_by = current_user.id
    db.session.commit()
    bump_bundle_version(row.locale)
    return ok(
        {
            'id': row.id,
            'namespace': row.namespace,
            'msg_key': row.msg_key,
            'locale': row.locale,
            'msg_value': row.msg_value,
            'description': row.description or '',
        },
        '已保存',
    )


@i18n_api.route('/admin/messages/<int:msg_id>', methods=['DELETE'])
@login_required
def admin_delete_message(msg_id: int):
    if not _can_manage_i18n():
        return fail('无权限', status=403)
    row = I18nMessage.query.get(msg_id)
    if not row:
        return fail('词条不存在', status=404)
    loc = row.locale
    db.session.delete(row)
    db.session.commit()
    bump_bundle_version(loc)
    return ok(message='已删除')


@i18n_api.route('/admin/namespaces', methods=['GET'])
@login_required
def admin_list_namespaces():
    if not _can_manage_i18n():
        return fail('无权限', status=403)
    from sqlalchemy import distinct

    extra = [
        r[0]
        for r in db.session.query(distinct(I18nMessage.namespace))
        .order_by(I18nMessage.namespace)
        .all()
    ]
    merged = []
    seen = set()
    for ns in list(DEFAULT_NAMESPACES) + extra:
        if ns and ns not in seen:
            seen.add(ns)
            merged.append(ns)
    return ok(merged)


@i18n_api.route('/admin/publish', methods=['POST'])
@login_required
def admin_publish():
    if not _can_manage_i18n():
        return fail('无权限', status=403)
    data = request.get_json(silent=True) or {}
    bump_bundle_version(data.get('locale'))
    return ok(message='词典已发布')


def _can_manage_i18n() -> bool:
    return bool(getattr(current_user, 'is_system_admin', False))
