# -*- coding: utf-8 -*-
"""登录与 API 访问审计。"""
from datetime import datetime

from app.extensions import db


class LoginAccessLog(db.Model):
    __tablename__ = 'login_access_logs'

    id = db.Column(db.Integer, primary_key=True)
    # auth：登录/登出/验证码；access：接口访问
    log_category = db.Column(db.String(16), nullable=False, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    subject = db.Column(db.String(256))
    ip_address = db.Column(db.String(64))
    user_agent = db.Column(db.String(512))
    request_method = db.Column(db.String(16))
    request_path = db.Column(db.String(512))
    status = db.Column(db.String(16), default='success', index=True)
    message = db.Column(db.String(512))
    detail_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(), index=True)
