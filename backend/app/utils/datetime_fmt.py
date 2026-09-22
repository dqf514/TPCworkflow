# -*- coding: utf-8 -*-
"""面向界面展示的本地时间格式（不含秒、不含 ISO 的 T）。"""
from __future__ import annotations

from datetime import datetime

DISPLAY_DATETIME_FMT = '%Y-%m-%d %H:%M'


def format_display_datetime(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if isinstance(dt, datetime):
        return dt.strftime(DISPLAY_DATETIME_FMT)
    return str(dt)
