# -*- coding: utf-8 -*-
import base64
import os
import re
import uuid
from datetime import datetime

from flask import Blueprint, current_app, request, send_from_directory
from flask_login import current_user, login_required

from app.services.attachment_settings import get_attachment_policy, validate_attachment_file
from app.utils.response import fail, ok

uploads_api = Blueprint('uploads_api', __name__)
files_api = Blueprint('files_api', __name__)
public_files_api = Blueprint('public_files_api', __name__)


def _project_base() -> str:
    return os.path.abspath(os.path.join(current_app.root_path, '..'))


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
    norm = subpath.replace('\\', '/')
    if not norm.startswith('uploads/branding/'):
        return fail('无权访问', status=403)
    base = _project_base()
    full = os.path.join(base, norm.replace('..', ''))
    if not os.path.isfile(full):
        return fail('文件不存在', status=404)
    directory = os.path.dirname(full)
    return send_from_directory(directory, os.path.basename(full))


@files_api.route('/<path:subpath>', methods=['GET'])
@login_required
def serve_file(subpath):
    base = _project_base()
    norm = subpath.replace('\\', '/').replace('..', '')
    full = os.path.join(base, norm)
    if not os.path.isfile(full):
        # 兼容旧数据：avatar_path 仅存文件名
        if '/' not in norm:
            legacy = os.path.join(base, 'uploads', 'avatars', norm)
            if os.path.isfile(legacy):
                full = legacy
    if not os.path.isfile(full):
        return fail('文件不存在', status=404)
    directory = os.path.dirname(full)
    return send_from_directory(directory, os.path.basename(full))
