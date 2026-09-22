# -*- coding: utf-8 -*-
"""业务板块与分级管理员。"""
from datetime import datetime

from app.extensions import db


class BusinessSector(db.Model):
    __tablename__ = 'business_sectors'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())


class UserScopedAdmin(db.Model):
    """分级管理员：按业务板块授权流程监管/设计/导出。"""
    __tablename__ = 'user_scoped_admins'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        unique=True,
        index=True,
    )
    sector_ids = db.Column(db.Text, default='[]')
    can_design_workflow = db.Column(db.Boolean, default=True, nullable=False)
    can_view_instances = db.Column(db.Boolean, default=True, nullable=False)
    can_export_instances = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    user = db.relationship('User', backref=db.backref('scoped_admin', uselist=False))
