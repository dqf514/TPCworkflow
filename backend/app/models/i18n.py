# -*- coding: utf-8 -*-
from datetime import datetime

from app.extensions import db


class I18nLocale(db.Model):
    __tablename__ = 'i18n_locales'

    code = db.Column(db.String(16), primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    native_name = db.Column(db.String(64), nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    direction = db.Column(db.String(3), default='ltr', nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())


class I18nMessage(db.Model):
    __tablename__ = 'i18n_messages'

    id = db.Column(db.Integer, primary_key=True)
    namespace = db.Column(db.String(64), nullable=False, index=True)
    msg_key = db.Column(db.String(256), nullable=False, index=True)
    locale = db.Column(
        db.String(16),
        db.ForeignKey('i18n_locales.code'),
        nullable=False,
        index=True,
    )
    msg_value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(512))
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    __table_args__ = (
        db.UniqueConstraint('namespace', 'msg_key', 'locale', name='uq_i18n_message'),
    )


class I18nBusinessText(db.Model):
    """流程模板、表单字段等业务动态文案。"""
    __tablename__ = 'i18n_business_texts'

    id = db.Column(db.Integer, primary_key=True)
    owner_type = db.Column(db.String(32), nullable=False, index=True)
    owner_id = db.Column(db.Integer, nullable=False, index=True)
    field_name = db.Column(db.String(64), nullable=False)
    locale = db.Column(db.String(16), nullable=False, index=True)
    text_value = db.Column(db.Text, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    __table_args__ = (
        db.UniqueConstraint(
            'owner_type',
            'owner_id',
            'field_name',
            'locale',
            name='uq_i18n_business_text',
        ),
    )


class I18nBundleMeta(db.Model):
    """词典发布版本，用于前端缓存失效。"""
    __tablename__ = 'i18n_bundle_meta'

    locale = db.Column(db.String(16), primary_key=True)
    version = db.Column(db.BigInteger, default=1, nullable=False)
    published_at = db.Column(db.DateTime, default=lambda: datetime.now())
