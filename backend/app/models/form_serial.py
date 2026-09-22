# -*- coding: utf-8 -*-
"""表单流水号计数器。"""
from datetime import datetime

from app.extensions import db


class FormSerialCounter(db.Model):
    """按 counter_key 原子递增，支持按日/月/年重置。"""

    __tablename__ = 'form_serial_counters'

    id = db.Column(db.Integer, primary_key=True)
    counter_key = db.Column(db.String(256), unique=True, nullable=False, index=True)
    last_value = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())
