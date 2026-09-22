# -*- coding: utf-8 -*-
"""Windows 客户端设备令牌（与 Web Session 独立，不影响现有登录）。"""
from __future__ import annotations

from datetime import datetime

from app.extensions import db


class UserDevice(db.Model):
    __tablename__ = 'user_devices'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    device_uid = db.Column(db.String(64), nullable=False)
    device_name = db.Column(db.String(128))
    access_token_hash = db.Column(db.String(256), nullable=False, index=True)
    refresh_token_hash = db.Column(db.String(256), nullable=False, index=True)
    access_expires_at = db.Column(db.DateTime, nullable=False)
    refresh_expires_at = db.Column(db.DateTime, nullable=False)
    last_used_at = db.Column(db.DateTime)
    revoked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())

    user = db.relationship('User', backref=db.backref('devices', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'device_uid', name='uq_user_device_uid'),
    )

    @property
    def is_active(self) -> bool:
        if self.revoked_at:
            return False
        return self.refresh_expires_at >= datetime.now()
