# -*- coding: utf-8 -*-
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ExchangeRate
from app.api.admin import _require_admin
from app.utils.response import fail, ok

exchange_rates_api = Blueprint('exchange_rates_api', __name__)

BASE_CURRENCY = 'CNY'


def _rate_dict(row: ExchangeRate) -> dict:
    return {
        'id': row.id,
        'currency_code': row.currency_code,
        'currency_name': row.currency_name,
        'rate_to_cny': float(row.rate_to_cny),
        'sort_order': row.sort_order,
        'is_active': row.is_active,
        'remark': row.remark or '',
        'updated_at': row.updated_at.strftime('%Y-%m-%d %H:%M') if row.updated_at else '',
    }


def _parse_rate(val) -> Decimal | None:
    try:
        d = Decimal(str(val))
        if d <= 0:
            return None
        return d
    except (InvalidOperation, TypeError, ValueError):
        return None


@exchange_rates_api.route('/exchange-rates', methods=['GET'])
@login_required
def list_exchange_rates():
    """表单填写：获取启用中的汇率。"""
    active_only = request.args.get('active_only', '1') != '0'
    q = ExchangeRate.query
    if active_only:
        q = q.filter_by(is_active=True)
    rows = q.order_by(ExchangeRate.sort_order, ExchangeRate.id).all()
    data = [_rate_dict(r) for r in rows]
    if active_only and not any(r['currency_code'] == BASE_CURRENCY for r in data):
        data.insert(
            0,
            {
                'id': 0,
                'currency_code': BASE_CURRENCY,
                'currency_name': '人民币',
                'rate_to_cny': 1.0,
                'sort_order': -1,
                'is_active': True,
                'remark': '',
                'updated_at': '',
            },
        )
    return ok(data)


@exchange_rates_api.route('/admin/exchange-rates', methods=['GET'])
@login_required
def admin_list_rates():
    err = _require_admin()
    if err:
        return err
    rows = ExchangeRate.query.order_by(ExchangeRate.sort_order, ExchangeRate.id).all()
    return ok([_rate_dict(r) for r in rows])


@exchange_rates_api.route('/admin/exchange-rates', methods=['POST'])
@login_required
def admin_create_rate():
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    code = (data.get('currency_code') or '').strip().upper()
    name = (data.get('currency_name') or '').strip()
    rate = _parse_rate(data.get('rate_to_cny'))
    if not code or not name:
        return fail('请填写币种编码与名称')
    if rate is None:
        return fail('汇率必须大于 0')
    if ExchangeRate.query.filter_by(currency_code=code).first():
        return fail('币种编码已存在')
    row = ExchangeRate(
        currency_code=code,
        currency_name=name,
        rate_to_cny=rate,
        sort_order=int(data.get('sort_order') or 0),
        is_active=data.get('is_active', True) is not False,
        remark=(data.get('remark') or '').strip(),
    )
    db.session.add(row)
    db.session.commit()
    return ok(_rate_dict(row), '已添加')


@exchange_rates_api.route('/admin/exchange-rates/<int:rate_id>', methods=['PUT'])
@login_required
def admin_update_rate(rate_id):
    err = _require_admin()
    if err:
        return err
    row = ExchangeRate.query.get(rate_id)
    if not row:
        return fail('记录不存在', status=404)
    data = request.get_json(silent=True) or {}
    if 'currency_name' in data:
        name = (data.get('currency_name') or '').strip()
        if not name:
            return fail('名称不能为空')
        row.currency_name = name
    if 'rate_to_cny' in data:
        rate = _parse_rate(data.get('rate_to_cny'))
        if rate is None:
            return fail('汇率必须大于 0')
        row.rate_to_cny = rate
    if 'sort_order' in data:
        row.sort_order = int(data.get('sort_order') or 0)
    if 'is_active' in data:
        row.is_active = bool(data.get('is_active'))
    if 'remark' in data:
        row.remark = (data.get('remark') or '').strip()
    db.session.commit()
    return ok(_rate_dict(row), '已更新')


@exchange_rates_api.route('/admin/exchange-rates/<int:rate_id>', methods=['DELETE'])
@login_required
def admin_delete_rate(rate_id):
    err = _require_admin()
    if err:
        return err
    row = ExchangeRate.query.get(rate_id)
    if not row:
        return fail('记录不存在', status=404)
    if row.currency_code == BASE_CURRENCY:
        return fail('人民币基准不可删除')
    db.session.delete(row)
    db.session.commit()
    return ok(message='已删除')
