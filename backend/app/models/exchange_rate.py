# -*- coding: utf-8 -*-
"""外币对人民币汇率（管理员维护）。"""
from __future__ import annotations

from datetime import datetime

from app.extensions import db


class ExchangeRate(db.Model):
    __tablename__ = 'exchange_rates'

    id = db.Column(db.Integer, primary_key=True)
    currency_code = db.Column(db.String(16), unique=True, nullable=False, index=True)
    currency_name = db.Column(db.String(64), nullable=False)
    rate_to_cny = db.Column(db.Numeric(18, 6), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    remark = db.Column(db.String(256))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )
