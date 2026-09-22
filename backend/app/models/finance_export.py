# -*- coding: utf-8 -*-
"""财务系统导出映射配置。"""
from datetime import datetime

from app.extensions import db


class FinanceExportMapping(db.Model):
    """板块级用友凭证导出映射方案。"""

    __tablename__ = 'finance_export_mappings'

    id = db.Column(db.Integer, primary_key=True)
    sector_id = db.Column(
        db.Integer,
        db.ForeignKey('business_sectors.id'),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    definition_ids = db.Column(db.Text, default='[]')
    line_mode = db.Column(db.String(32), default='per_detail_plus_credit', nullable=False)
    detail_key = db.Column(db.String(64))
    amount_source_key = db.Column(db.String(64), default='amount')
    column_mappings = db.Column(db.Text, default='[]')
    export_options = db.Column(db.Text, default='{}')
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )
