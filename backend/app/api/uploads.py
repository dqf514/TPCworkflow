# -*- coding: utf-8 -*-
import base64
import os
import re
import urllib.parse
import uuid
from datetime import datetime

from flask import Blueprint, current_app, request, send_from_directory
from flask_login import current_user, login_required

from app.services.attachment_settings import get_attachment_policy, validate_attachment_file
from app.utils.response import fail, ok

uploads_api = Blueprint('uploads_api', __name__)
files_api = Blueprint('files_api', __name__)
public_files_api = Blueprint('public_files_api', __name__)

# 允许通过 /api/v1/files 下载的目录白名单。
# 历史实现只过滤 '..'，等价于「backend/ 下任意文件可下载」——普通员工账号即可拖走
# data/tpcworkflow.db（含全部密码哈希、LLM Key、验证码与审批 token）与 .env。
SERVED_DIRS = (
    'uploads/attachments/',
    'uploads/avatars/',
    'uploads/signatures/',
    'uploads/branding/',
)

# 品牌 Logo 允许匿名访问（登录页也要显示）
PUBLIC_DIRS = ('uploads/branding/',)

# 只有这些类型允许浏览器内联渲染，其余一律作为附件下载，避免同源存储型 XSS
# （html / svg / xml 等可携带脚本，text/html 内联即等价于把上传内容变成同源页面）
INLINE_IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.pdf'}


def _project_base() -> str:
    return os.path.abspath(os.path.join(current_app.root_path, '..'))


def _normalize_rel(rel: str) -> str:
    """去掉路径分隔与 '..'，返回规范化相对路径。"""
    parts = []
    for seg in (rel or '').replace('\\', '/').split('/'):
        if seg in ('', '.', '..'):
            continue
        parts.append(seg)
    return '/'.join(parts)


def _resolve_upload_path(rel: str, allowed_dirs) -> str | None:
    """把请求路径解析成白名单目录内的绝对路径；越界返回 None。"""
    norm = _normalize_rel(rel)
    if not norm.startswith(tuple(allowed_dirs)):
        return None
    base = _project_base()
    full = os.path.abspath(os.path.join(base, norm))
    # 双保险：解析后必须仍在项目目录内
    if not full.startswith(base + os.sep):
        return None
    if not os.path.isfile(full):
        return None
    return full


def _send_upload(full: str):
    """发送上传文件，并按类型决定内联展示还是作为附件下载。"""
    resp = send_from_directory(os.path.dirname(full), os.path.basename(full))
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    name = os.path.basename(full)
    ext = os.path.splitext(name)[1].lower()
    if ext not in INLINE_IMAGE_EXT:
        quoted = urllib.parse.quote(name)
        resp.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{quoted}"
    return resp


@uploads_api.route('/attachment-policy', methods=['GET'])
@login_required
def attachment_policy():
    return ok(get_attachment_policy())


@uploads_api.route('/signature', methods=['POST'])
@login_required
def upload_signature():
    data = request.get_json(silent=True) or {}
    b64 = data.get('signature_data') or ''
    if not b64.startswith('data:image'):
        return fail('无效签名数据')
    match = re.match(r'data:image/(png|jpeg|jpg);base64,(.+)', b64, re.I)
    if not match:
        return fail('仅支持 PNG/JPEG 签名图')
    ext = 'png' if match.group(1).lower() == 'png' else 'jpg'
    raw = base64.b64decode(match.group(2))
    folder = current_app.config.get('SIGNATURE_FOLDER')
    os.makedirs(folder, exist_ok=True)
    fname = f'{current_user.id}_{datetime.now().strftime("%Y%m%d%H%M%S")}_{uuid.uuid4().hex[:8]}.{ext}'
    path = os.path.join(folder, fname)
    with open(path, 'wb') as f:
        f.write(raw)
    rel = f'uploads/signatures/{fname}'
    return ok({'signature_path': rel, 'url': f'/api/v1/files/{rel}'})


def _upload_file_size(f) -> int:
    """获取上传文件大小（content_length 在部分客户端/代理下可能为 0）。"""
    size = f.content_length
    if size is not None and size > 0:
        return int(size)
    try:
        pos = f.tell()
        f.seek(0, os.SEEK_END)
        measured = f.tell()
        f.seek(pos)
        return int(measured or 0)
    except Exception:
        return int(size or 0)


@uploads_api.route('/attachments', methods=['POST'])
@login_required
def upload_attachment():
    """表单附件上传（multipart 字段名 file）。"""
    f = request.files.get('file')
    if not f or not f.filename:
        return fail('请选择文件')
    raw_name = os.path.basename(f.filename)
    size = _upload_file_size(f)
    err = validate_attachment_file(raw_name, int(size or 0))
    if err:
        return fail(err)
    ext = os.path.splitext(raw_name)[1].lower()
    safe_ext = ext if re.match(r'^\.[a-z0-9]{1,8}$', ext) else ''
    folder = os.path.join(_project_base(), 'uploads', 'attachments')
    os.makedirs(folder, exist_ok=True)
    fname = f'{current_user.id}_{datetime.now().strftime("%Y%m%d%H%M%S")}_{uuid.uuid4().hex[:8]}{safe_ext}'
    path = os.path.join(folder, fname)
    f.save(path)
    rel = f'uploads/attachments/{fname}'
    return ok(
        {
            'name': raw_name,
            'path': rel,
            'url': f'/api/v1/files/{rel}',
            'size': os.path.getsize(path),
        },
        '上传成功',
    )


@public_files_api.route('/<path:subpath>', methods=['GET'])
def serve_public_file(subpath):
    """无需登录：仅允许访问组织品牌 Logo。"""
    full = _resolve_upload_path(subpath, PUBLIC_DIRS)
    if not full:
        return fail('无权访问', status=403)
    return _send_upload(full)


@files_api.route('/<path:subpath>', methods=['GET'])
@login_required
def serve_file(subpath):
    norm = _normalize_rel(subpath)
    # 白名单之外一律 403（原先可下载 backend/ 下任意文件，含 data/tpcworkflow.db）
    if not norm.startswith(SERVED_DIRS):
        # 兼容旧数据：avatar_path 仅存文件名
        if '/' not in norm:
            legacy = _resolve_upload_path(f'uploads/avatars/{norm}', SERVED_DIRS)
            if legacy:
                return _send_upload(legacy)
        return fail('无权访问', status=403)
    full = _resolve_upload_path(norm, SERVED_DIRS)
    if not full:
        return fail('文件不存在', status=404)
    return _send_upload(full)
