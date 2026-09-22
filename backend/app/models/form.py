# -*- coding: utf-8 -*-
from datetime import datetime

from app.extensions import db


class FormDefinition(db.Model):
    """审批表单模板（与流程一对一绑定）。"""
    __tablename__ = 'form_definitions'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(32), default='draft', nullable=False)
    description = db.Column(db.String(512))
    schema_json = db.Column(db.Text)
    workflow_definition_id = db.Column(db.Integer, index=True)
    business_sector_id = db.Column(db.Integer, db.ForeignKey('business_sectors.id'), index=True)
    icon = db.Column(db.String(64))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )
    published_at = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint('key', 'version', name='uq_form_def_key_version'),
    )
