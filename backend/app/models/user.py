# -*- coding: utf-8 -*-
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    """系统登录账号。"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    display_name = db.Column(db.String(128))
    phone = db.Column(db.String(32))
    email = db.Column(db.String(256), index=True)
    job_title = db.Column(db.String(128))
    locale = db.Column(db.String(16), default='zh-CN', nullable=False)
    holiday_regions = db.Column(db.String(128), default='', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_system_admin = db.Column(db.Boolean, default=False, nullable=False)
    auth_provider = db.Column(db.String(32), default='local', nullable=False)
    external_id = db.Column(db.String(128), index=True)
    avatar_path = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    org_memberships = db.relationship(
        'UserOrgMembership',
        back_populates='user',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def display_label(self) -> str:
        return (self.display_name or self.username or '').strip() or self.username


class LoginSmsCode(db.Model):
    """短信验证码登录。"""
    __tablename__ = 'login_sms_codes'

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(32), nullable=False, index=True)
    code_hash = db.Column(db.String(256), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(), index=True)


class LoginEmailCode(db.Model):
    """邮箱验证码登录（短时有效）。"""
    __tablename__ = 'login_email_codes'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), nullable=False, index=True)
    code_hash = db.Column(db.String(256), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(), index=True)


class AdminEmailConfirmCode(db.Model):
    """管理员敏感操作邮箱确认码。"""
    __tablename__ = 'admin_email_confirm_codes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    purpose = db.Column(db.String(64), nullable=False, index=True)
    code_hash = db.Column(db.String(256), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(), index=True)
