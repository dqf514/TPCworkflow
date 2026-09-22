# -*- coding: utf-8 -*-
from datetime import datetime

from app.extensions import db


class SystemSetting(db.Model):
    """系统配置（邮件、短信、Azure SSO 等）。"""
    __tablename__ = 'system_settings'

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )


class NotificationLog(db.Model):
    __tablename__ = 'notification_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    channel = db.Column(db.String(32), nullable=False)
    # login_code | approval_notify | test | sms_login 等
    mail_type = db.Column(db.String(32), index=True)
    recipient = db.Column(db.String(256))
    task_id = db.Column(db.Integer, index=True)
    instance_id = db.Column(db.Integer, index=True)
    subject = db.Column(db.String(256))
    body = db.Column(db.Text)
    status = db.Column(db.String(32), default='pending')
    error_message = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(), index=True)
