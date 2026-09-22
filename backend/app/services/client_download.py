# -*- coding: utf-8 -*-
"""Windows 客户端安装包路径解析。"""
from __future__ import annotations

import os

from flask import current_app

DEFAULT_EXE_NAME = 'TPCWorkflow.Client.exe'
DEFAULT_SETUP_NAME = 'TPCWorkflow-Setup.exe'
DEFAULT_ZIP_NAME = 'TPCWorkflow-Client.zip'


def _download_dirs() -> list[str]:
    app_root = current_app.root_path
    backend_dir = os.path.abspath(os.path.join(app_root, '..'))
    project_root = os.path.abspath(os.path.join(backend_dir, '..'))
    return [
        os.path.join(project_root, 'deploy', 'downloads'),
        os.path.join(backend_dir, 'deploy', 'downloads'),
        os.path.join(backend_dir, 'data', 'downloads'),
        os.path.join(backend_dir, 'downloads'),
    ]


def _resolve_in_dirs(filename: str) -> str | None:
    configured = (current_app.config.get('CLIENT_DOWNLOAD_FILE') or '').strip()
    candidates: list[str] = []
    if configured:
        if filename in (DEFAULT_EXE_NAME, DEFAULT_SETUP_NAME):
            candidates.append(configured)
            if filename == DEFAULT_SETUP_NAME:
                base, _ = os.path.splitext(configured)
                candidates.append(base + '-Setup.exe')
        elif filename == DEFAULT_ZIP_NAME:
            base, _ = os.path.splitext(configured)
            candidates.append(base + '.zip')
            candidates.append(base.replace('.Client', '-Client') + '.zip')
    for directory in _download_dirs():
        candidates.append(os.path.join(directory, filename))

    seen: set[str] = set()
    for raw in candidates:
        path = os.path.abspath(raw)
        if path in seen:
            continue
        seen.add(path)
        if os.path.isfile(path) and os.access(path, os.R_OK):
            return path
    return None


def resolve_client_download_path(fmt: str) -> str | None:
    """按格式 setup / zip / exe 返回安装包绝对路径。"""
    fmt = (fmt or '').strip().lower()
    if fmt == 'setup':
        return _resolve_in_dirs(DEFAULT_SETUP_NAME) or _resolve_in_dirs(DEFAULT_EXE_NAME)
    if fmt == 'zip':
        return _resolve_in_dirs(DEFAULT_ZIP_NAME)
    if fmt == 'exe':
        return _resolve_in_dirs(DEFAULT_EXE_NAME)
    return None


def _format_meta(fmt: str, filename: str, download_url: str) -> dict:
    path = resolve_client_download_path(fmt)
    if not path:
        return {
            'available': False,
            'filename': filename,
            'size_bytes': 0,
            'download_url': download_url,
        }
    return {
        'available': True,
        'filename': os.path.basename(path),
        'size_bytes': os.path.getsize(path),
        'download_url': download_url,
    }


def client_download_meta() -> dict:
    setup_meta = _format_meta('setup', DEFAULT_SETUP_NAME, '/api/v1/client/download/setup')
    zip_meta = _format_meta('zip', DEFAULT_ZIP_NAME, '/api/v1/client/download/zip')
    exe_meta = _format_meta('exe', DEFAULT_EXE_NAME, '/api/v1/client/download/exe')
    available = setup_meta['available'] or zip_meta['available'] or exe_meta['available']
    if not available:
        current_app.logger.warning(
            '客户端安装包未找到，请检查 deploy/downloads 下是否存在 Setup/exe/zip',
        )
    return {
        'available': available,
        'setup': setup_meta,
        'zip': zip_meta,
        'exe': exe_meta,
    }
