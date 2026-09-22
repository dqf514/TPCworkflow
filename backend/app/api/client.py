# -*- coding: utf-8 -*-
"""Windows 桌面客户端专用 API（不影响现有 Web 路由行为）。"""
from __future__ import annotations

import json
import queue

from flask import Blueprint, Response, request, send_file, stream_with_context
import os
from flask_login import current_user, login_required

from app.services.client_bootstrap import build_client_bootstrap
from app.services.client_download import (
    client_download_meta,
    resolve_client_download_path,
)
from app.services.client_version import build_client_version_info
from app.services.client_events import subscribe, unsubscribe
from app.utils.client_auth import client_auth_required
from app.utils.response import fail, ok

client_api = Blueprint('client_api', __name__)


@client_api.route('/bootstrap', methods=['GET'])
@client_auth_required
def client_bootstrap():
    """一次返回用户信息、角标、待办预览与导航菜单。"""
    return ok(build_client_bootstrap(current_user))


@client_api.route('/events/stream', methods=['GET'])
@client_auth_required
def client_events_stream():
    """SSE：待办分配、角标变化等实时事件。"""
    user_id = current_user.id
    q = subscribe(user_id)

    def generate():
        try:
            yield f"event: connected\ndata: {json.dumps({'ok': True}, ensure_ascii=False)}\n\n"
            while True:
                try:
                    evt = q.get(timeout=30)
                    yield (
                        f"event: {evt['type']}\n"
                        f"data: {json.dumps(evt.get('data') or {}, ensure_ascii=False)}\n\n"
                    )
                except queue.Empty:
                    yield ": heartbeat\n\n"
        finally:
            unsubscribe(user_id, q)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@client_api.route('/embed-check', methods=['GET'])
def client_embed_check():
    """供前端检测是否处于客户端嵌入上下文（无副作用）。"""
    embed = (request.args.get('embed') or '').strip()
    return ok({'embed_desktop': embed == 'desktop'})


@client_api.route('/version', methods=['GET'])
def client_version():
    """客户端版本检查（无需登录，启动时即可调用）。"""
    return ok(build_client_version_info())


@client_api.route('/download-info', methods=['GET'])
@login_required
def client_download_info():
    """当前是否可下载 Windows 客户端（zip / exe 分别返回）。"""
    return ok(client_download_meta())


def _send_client_package(fmt: str):
    path = resolve_client_download_path(fmt)
    if not path:
        labels = {'zip': 'ZIP 压缩包', 'setup': '安装包', 'exe': 'EXE 程序'}
        label = labels.get(fmt, '安装包')
        return fail(f'客户端{label}暂未发布', status=404)

    if fmt == 'zip':
        mimetype = 'application/zip'
        download_name = 'TPCWorkflow-Client.zip'
    elif fmt == 'setup':
        mimetype = 'application/octet-stream'
        download_name = 'TPCWorkflow-Setup.exe'
    else:
        mimetype = 'application/octet-stream'
        download_name = 'TPCWorkflow-Client.exe'

    response = send_file(
        path,
        as_attachment=True,
        download_name=download_name,
        mimetype=mimetype,
        max_age=0,
        conditional=False,
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Content-Disposition'] = f'attachment; filename="{download_name}"'
    return response


@client_api.route('/download/setup', methods=['GET'])
@login_required
def client_download_setup():
    """下载安装包（首次安装 / 自动更新，覆盖用户目录）。"""
    return _send_client_package('setup')


@client_api.route('/download/zip', methods=['GET'])
@login_required
def client_download_zip():
    """下载 ZIP 压缩包（推荐，Edge 拦截较少）。"""
    return _send_client_package('zip')


@client_api.route('/download/exe', methods=['GET'])
@login_required
def client_download_exe():
    """下载单文件 EXE。"""
    return _send_client_package('exe')


@client_api.route('/download', methods=['GET'])
@login_required
def client_download():
    """兼容旧链接：优先 ZIP，否则 EXE。"""
    path = resolve_client_download_path('setup') or resolve_client_download_path('zip') or resolve_client_download_path('exe')
    if not path:
        return fail('客户端安装包暂未发布', status=404)
    if path.lower().endswith('.zip'):
        fmt = 'zip'
    elif path.lower().endswith('-setup.exe') or 'setup' in os.path.basename(path).lower():
        fmt = 'setup'
    else:
        fmt = 'exe'
    return _send_client_package(fmt)
