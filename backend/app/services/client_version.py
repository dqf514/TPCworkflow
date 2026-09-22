# -*- coding: utf-8 -*-
"""Windows 客户端版本信息（与 publish.ps1 生成的 client-version.json 配合）。"""
from __future__ import annotations

import json
import os
from datetime import datetime

from flask import current_app

from app.services.client_download import client_download_meta

VERSION_JSON_NAME = 'client-version.json'


def _version_json_candidates() -> list[str]:
    app_root = current_app.root_path
    backend_dir = os.path.abspath(os.path.join(app_root, '..'))
    project_root = os.path.abspath(os.path.join(backend_dir, '..'))
    configured = (current_app.config.get('CLIENT_VERSION_FILE') or '').strip()
    candidates: list[str] = []
    if configured:
        candidates.append(configured)
    candidates.extend([
        os.path.join(project_root, 'deploy', 'downloads', VERSION_JSON_NAME),
        os.path.join(backend_dir, 'deploy', 'downloads', VERSION_JSON_NAME),
        os.path.join(backend_dir, 'data', 'downloads', VERSION_JSON_NAME),
    ])
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in candidates:
        path = os.path.abspath(raw)
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def _load_version_json() -> dict | None:
    for path in _version_json_candidates():
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get('version'):
                return data
        except (OSError, json.JSONDecodeError):
            continue
    return None


def build_client_version_info() -> dict:
    """返回服务端发布的最新客户端版本与下载信息。"""
    data = _load_version_json() or {}
    version = (data.get('version') or current_app.config.get('CLIENT_APP_VERSION') or '1.0.0').strip()
    release_notes = (data.get('release_notes') or '').strip()
    mandatory = bool(data.get('mandatory'))
    published_at = (data.get('published_at') or '').strip()
    if not published_at:
        published_at = datetime.now().isoformat(timespec='seconds')

    downloads = client_download_meta()
    return {
        'version': version,
        'release_notes': release_notes,
        'mandatory': mandatory,
        'published_at': published_at,
        'downloads': downloads,
    }
