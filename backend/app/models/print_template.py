# -*- coding: utf-8 -*-
from datetime import datetime

from app.extensions import db


class PrintTemplate(db.Model):
    """可配置打印模板（管理员后台维护）。"""

    __tablename__ = 'print_templates'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(512), default='')
    category = db.Column(db.String(32), default='custom')
    is_builtin = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    schema_json = db.Column(db.Text, nullable=False, default='{}')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )
