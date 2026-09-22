# -*- coding: utf-8 -*-
"""选项配置表（单字段 name+code）与控件配置表（多字段行数据）。"""
from __future__ import annotations

import json
from datetime import datetime

from app.extensions import db

SET_TYPE_OPTION = 'option'
SET_TYPE_RECORD = 'record'

SCOPE_MIXED = 'mixed'
SCOPE_COMPANY = 'company'
SCOPE_PERSONAL = 'personal'
RECORD_SET_DATA_SCOPES = (SCOPE_MIXED, SCOPE_COMPANY, SCOPE_PERSONAL)


class OptionSet(db.Model):
    """配置表定义：set_type=option 为选项配置表；set_type=record 为控件配置表。"""

    __tablename__ = 'option_sets'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    set_type = db.Column(db.String(16), default=SET_TYPE_OPTION, nullable=False, index=True)
    # mixed=公司+本人个人行；company=仅公司行；personal=仅本人个人行
    data_scope = db.Column(db.String(16), default=SCOPE_MIXED, nullable=False, index=True)
    description = db.Column(db.String(512))
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    items = db.relationship(
        'OptionSetItem',
        back_populates='option_set',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='OptionSetItem.sort_order',
    )
    columns = db.relationship(
        'OptionSetColumn',
        back_populates='option_set',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='OptionSetColumn.sort_order',
    )
    records = db.relationship(
        'OptionSetRecord',
        back_populates='option_set',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='OptionSetRecord.sort_order',
    )


class OptionSetItem(db.Model):
    """选项配置表中的选项行（名称 + 编码）。"""

    __tablename__ = 'option_set_items'

    id = db.Column(db.Integer, primary_key=True)
    option_set_id = db.Column(
        db.Integer,
        db.ForeignKey('option_sets.id'),
        nullable=False,
        index=True,
    )
    code = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    option_set = db.relationship('OptionSet', back_populates='items')

    __table_args__ = (
        db.UniqueConstraint('option_set_id', 'code', name='uq_option_set_item_code'),
    )


class OptionSetColumn(db.Model):
    """控件配置表的列定义（字段数可增减）。"""

    __tablename__ = 'option_set_columns'

    id = db.Column(db.Integer, primary_key=True)
    option_set_id = db.Column(
        db.Integer,
        db.ForeignKey('option_sets.id'),
        nullable=False,
        index=True,
    )
    field_key = db.Column(db.String(64), nullable=False)
    label = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    span = db.Column(db.Integer, default=24, nullable=False)

    option_set = db.relationship('OptionSet', back_populates='columns')

    __table_args__ = (
        db.UniqueConstraint('option_set_id', 'field_key', name='uq_option_set_column_key'),
    )


class OptionSetRecord(db.Model):
    """控件配置表中的数据行。owner_user_id 为空为公司级，非空为填报人个人数据。"""

    __tablename__ = 'option_set_records'

    id = db.Column(db.Integer, primary_key=True)
    option_set_id = db.Column(
        db.Integer,
        db.ForeignKey('option_sets.id'),
        nullable=False,
        index=True,
    )
    owner_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=True,
        index=True,
    )
    row_code = db.Column(db.String(64), nullable=False)
    data_json = db.Column(db.Text, nullable=False, default='{}')
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    option_set = db.relationship('OptionSet', back_populates='records')
    owner = db.relationship('User', foreign_keys=[owner_user_id])

    __table_args__ = (
        db.UniqueConstraint(
            'option_set_id',
            'row_code',
            'owner_user_id',
            name='uq_option_set_record_scope',
        ),
    )

    def get_data(self) -> dict:
        try:
            data = json.loads(self.data_json or '{}')
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_data(self, data: dict) -> None:
        self.data_json = json.dumps(data or {}, ensure_ascii=False)
