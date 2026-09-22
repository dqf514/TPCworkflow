# -*- coding: utf-8 -*-
"""大模型接入配置（管理员维护，按优先级调用）。"""
from __future__ import annotations

from datetime import datetime

from app.extensions import db

PROVIDER_TYPES = (
    'openai_compatible',
    'anthropic_compatible',
    'ollama',
)


class LlmProvider(db.Model):
    __tablename__ = 'llm_providers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, default='')
    provider_type = db.Column(db.String(32), nullable=False, default='openai_compatible')
    base_url = db.Column(db.String(512), nullable=False)
    api_key = db.Column(db.String(512))
    model_name = db.Column(db.String(128))
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_test_ok = db.Column(db.Boolean)
    last_test_message = db.Column(db.String(512))
    last_tested_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )
