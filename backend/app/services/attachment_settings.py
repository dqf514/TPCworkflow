# -*- coding: utf-8 -*-
"""表单附件上传策略（扩展名、大小），从系统设置读取。"""
from __future__ import annotations

import re

from app.models import SystemSetting

SETTING_ALLOWED_EXTENSIONS = 'ATTACHMENT_ALLOWED_EXTENSIONS'
SETTING_MAX_MB = 'ATTACHMENT_MAX_SIZE_MB'

DEFAULT_ALLOWED = (
    'pdf,doc,docx,xls,xlsx,ppt,pptx,txt,csv,'
    'png,jpg,jpeg,gif,webp,bmp,'
    'zip,rar,7z,'
    'eml,msg'
)
DEFAULT_MAX_MB = 20

# 始终禁止的可执行/脚本类扩展名
HARDCODED_BLOCKED = {
    'exe', 'bat', 'cmd', 'com', 'msi', 'dll', 'scr', 'ps1', 'vbs', 'js', 'jar', 'sh',
}


def _setting_value(key: str, default: str) -> str:
    row = SystemSetting.query.get(key)
    if row and row.value is not None and str(row.value).strip() != '':
        return str(row.value).strip()
    return default


def parse_allowed_extensions(raw: str | None = None) -> list[str]:
    text = (raw if raw is not None else _setting_value(SETTING_ALLOWED_EXTENSIONS, DEFAULT_ALLOWED))
    parts = []
    for piece in re.split(r'[,;\s]+', text.lower()):
        p = piece.strip().lstrip('.')
        if not p:
            continue
        if p == '*':
            return ['*']
        parts.append(p)
    return parts or [e.strip().lstrip('.') for e in DEFAULT_ALLOWED.split(',') if e.strip()]


def get_max_bytes(raw_mb: str | None = None) -> int:
    text = raw_mb if raw_mb is not None else _setting_value(SETTING_MAX_MB, str(DEFAULT_MAX_MB))
    try:
        mb = float(text)
    except (TypeError, ValueError):
        mb = DEFAULT_MAX_MB
    if mb <= 0:
        mb = DEFAULT_MAX_MB
    if mb > 500:
        mb = 500
    return int(mb * 1024 * 1024)


def get_attachment_policy() -> dict:
    allowed = parse_allowed_extensions()
    max_bytes = get_max_bytes()
    return {
        'allowed_extensions': allowed,
        'max_bytes': max_bytes,
        'max_mb': round(max_bytes / (1024 * 1024), 2),
        'accept': _build_accept_attr(allowed),
    }


def _build_accept_attr(allowed: list[str]) -> str:
    if '*' in allowed:
        return ''
    exts = [f'.{e}' if not e.startswith('.') else e for e in allowed]
    return ','.join(exts)


def validate_attachment_file(filename: str, size: int) -> str | None:
    """通过返回 None；失败返回中文错误信息。"""
    if not filename:
        return '请选择文件'
    name = filename.replace('\\', '/').split('/')[-1]
    ext = ''
    if '.' in name:
        ext = name.rsplit('.', 1)[-1].lower()
    if ext in HARDCODED_BLOCKED:
        return f'不允许上传 .{ext} 类型文件'
    allowed = parse_allowed_extensions()
    if '*' not in allowed:
        if not ext:
            return '该文件无扩展名，不在允许列表中'
        if ext not in allowed:
            hint = '、'.join(f'.{e}' for e in allowed[:12])
            more = '…' if len(allowed) > 12 else ''
            return f'不允许上传 .{ext} 文件，允许类型：{hint}{more}'
    max_bytes = get_max_bytes()
    if size > max_bytes:
        mb = max_bytes / (1024 * 1024)
        return f'文件大小不能超过 {mb:g} MB'
    if size <= 0:
        return '文件为空'
    return None
