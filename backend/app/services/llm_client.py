# -*- coding: utf-8 -*-
"""大模型连接测试与配置解析。"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any
from urllib.parse import urlparse, urlunparse

from app.extensions import db
from app.models.llm_provider import LlmProvider, PROVIDER_TYPES

TEST_TIMEOUT_SEC = 20


def normalize_base_url(url: str) -> str:
    raw = (url or '').strip().rstrip('/')
    if not raw:
        raise ValueError('请填写 Base URL')
    if raw.startswith('@internal'):
        # @internal:8080/v1 → 本机内置服务（由后端解析，非浏览器访问）
        rest = raw[len('@internal'):].lstrip(':/')
        local_host = (os.environ.get('LLM_LOCAL_HOST') or '127.0.0.1').strip() or '127.0.0.1'
        if not rest:
            raw = f'http://{local_host}'
        elif rest[0].isdigit():
            port, _, path = rest.partition('/')
            raw = f'http://{local_host}:{port}/{path}' if path else f'http://{local_host}:{port}'
        else:
            raw = f'http://{local_host}/{rest}'
    elif not raw.startswith(('http://', 'https://')):
        raw = f'http://{raw}'
    return resolve_base_url(raw)


def resolve_base_url(url: str) -> str:
    """解析 Base URL：localhost → 127.0.0.1，避免服务端 IPv6 连接失败。"""
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if not host:
        return url

    local_aliases = {'localhost', '127.0.0.1', '::1'}
    if host not in local_aliases:
        return url

    local_host = (os.environ.get('LLM_LOCAL_HOST') or '127.0.0.1').strip() or '127.0.0.1'
    port = parsed.port
    userinfo = ''
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo += f':{parsed.password}'
        userinfo += '@'
    netloc = f'{userinfo}{local_host}:{port}' if port else f'{userinfo}{local_host}'
    return urlunparse(parsed._replace(netloc=netloc))


def _http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = TEST_TIMEOUT_SEC,
) -> tuple[int, str]:
    data = None
    req_headers = {'Accept': 'application/json', **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        req_headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode('utf-8', errors='replace')
            return resp.status, text
    except urllib.error.HTTPError as exc:
        text = exc.read().decode('utf-8', errors='replace')
        return exc.code, text


def _openai_root(base_url: str) -> str:
    base = normalize_base_url(base_url)
    if base.endswith('/v1'):
        return base
    return f'{base}/v1'


def _anthropic_messages_url(base_url: str) -> str:
    base = normalize_base_url(base_url)
    if base.endswith('/v1'):
        return f'{base}/messages'
    return f'{base}/v1/messages'


def _ollama_root(base_url: str) -> str:
    base = normalize_base_url(base_url)
    if base.endswith('/v1'):
        base = base[:-3].rstrip('/')
    return base


def _parse_models_response(text: str) -> list[str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        data = payload.get('data')
        if isinstance(data, list):
            names = []
            for item in data:
                if isinstance(item, dict) and item.get('id'):
                    names.append(str(item['id']))
            return names
        models = payload.get('models')
        if isinstance(models, list):
            names = []
            for item in models:
                if isinstance(item, dict):
                    name = item.get('name') or item.get('model')
                    if name:
                        names.append(str(name))
            return names
    return []


def test_provider_connection(
    provider_type: str,
    base_url: str,
    api_key: str = '',
    model_name: str = '',
) -> tuple[bool, str]:
    ptype = (provider_type or '').strip() or 'openai_compatible'
    if ptype not in PROVIDER_TYPES:
        return False, f'不支持的接口类型：{ptype}'

    key = (api_key or '').strip()
    model = (model_name or '').strip()

    try:
        if ptype == 'openai_compatible':
            return _test_openai_compatible(base_url, key, model)
        if ptype == 'anthropic_compatible':
            return _test_anthropic_compatible(base_url, key, model)
        return _test_ollama_native(base_url, model)
    except ValueError as exc:
        return False, str(exc)
    except urllib.error.URLError as exc:
        return False, f'无法连接：{exc.reason}'
    except Exception as exc:  # noqa: BLE001
        return False, f'测试失败：{exc}'


def _test_openai_compatible(base_url: str, api_key: str, model_name: str) -> tuple[bool, str]:
    root = _openai_root(base_url)
    headers: dict[str, str] = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    status, text = _http_request('GET', f'{root}/models', headers=headers)
    if status < 400:
        models = _parse_models_response(text)
        if model_name and models and model_name not in models:
            return True, f'连接成功（未在模型列表中找到 {model_name}，共 {len(models)} 个模型）'
        if models:
            return True, f'连接成功，可用模型 {len(models)} 个'
        return True, '连接成功'

    if model_name:
        body = {
            'model': model_name,
            'messages': [{'role': 'user', 'content': 'ping'}],
            'max_tokens': 1,
            'stream': False,
        }
        status2, text2 = _http_request('POST', f'{root}/chat/completions', headers=headers, body=body)
        if status2 < 400:
            return True, '连接成功（聊天接口可用）'
        return False, _format_http_error(status2, text2)

    hint = '请填写模型名称，或确认 Base URL 支持 GET /v1/models'
    return False, _format_http_error(status, text, extra=hint)


def _test_anthropic_compatible(base_url: str, api_key: str, model_name: str) -> tuple[bool, str]:
    if not api_key:
        return False, 'Anthropic 兼容接口需填写 API Key'
    if not model_name:
        return False, 'Anthropic 兼容接口测试需填写模型名称'

    url = _anthropic_messages_url(base_url)
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
    }
    body = {
        'model': model_name,
        'max_tokens': 1,
        'messages': [{'role': 'user', 'content': 'ping'}],
    }
    status, text = _http_request('POST', url, headers=headers, body=body)
    if status < 400:
        return True, '连接成功'
    return False, _format_http_error(status, text)


def _test_ollama_native(base_url: str, model_name: str) -> tuple[bool, str]:
    root = _ollama_root(base_url)
    status, text = _http_request('GET', f'{root}/api/tags')
    if status >= 400:
        return False, _format_http_error(status, text)

    models = _parse_models_response(text)
    if model_name and models and model_name not in models:
        return True, f'连接成功（未在本地模型列表中找到 {model_name}，共 {len(models)} 个）'
    if models:
        return True, f'连接成功，本地模型 {len(models)} 个'
    return True, '连接成功（Ollama 服务可达）'


def _format_http_error(status: int, text: str, extra: str = '') -> str:
    snippet = (text or '').strip().replace('\n', ' ')[:240]
    msg = f'HTTP {status}'
    if snippet:
        msg += f'：{snippet}'
    if extra:
        msg += f'（{extra}）'
    return msg


def provider_to_dict(row: LlmProvider, *, include_key: bool = False) -> dict:
    return {
        'id': row.id,
        'name': row.name or '',
        'provider_type': row.provider_type,
        'base_url': row.base_url,
        'api_key': row.api_key if include_key else '',
        'has_api_key': bool((row.api_key or '').strip()),
        'model_name': row.model_name or '',
        'sort_order': row.sort_order,
        'is_active': row.is_active,
        'is_default': False,
        'last_test_ok': row.last_test_ok,
        'last_test_message': row.last_test_message or '',
        'last_tested_at': row.last_tested_at.strftime('%Y-%m-%d %H:%M') if row.last_tested_at else '',
        'updated_at': row.updated_at.strftime('%Y-%m-%d %H:%M') if row.updated_at else '',
    }


def mark_default_flags(rows: list[dict]) -> list[dict]:
    """列表中第一个启用项标记为默认模型。"""
    marked = False
    for item in rows:
        if not marked and item.get('is_active'):
            item['is_default'] = True
            marked = True
        else:
            item['is_default'] = False
    return rows


def get_active_providers_ordered() -> list[LlmProvider]:
    return (
        LlmProvider.query.filter_by(is_active=True)
        .order_by(LlmProvider.sort_order.asc(), LlmProvider.id.asc())
        .all()
    )


def get_default_provider() -> LlmProvider | None:
    rows = get_active_providers_ordered()
    return rows[0] if rows else None


def record_test_result(row: LlmProvider | None, ok: bool, message: str) -> None:
    if not row or not row.id:
        return
    row.last_test_ok = ok
    row.last_test_message = (message or '')[:512]
    row.last_tested_at = datetime.now()
    db.session.commit()
