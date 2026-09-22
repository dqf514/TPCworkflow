# -*- coding: utf-8 -*-
"""大模型对话与视觉识别调用。"""
from __future__ import annotations

import json
import re
import urllib.error
from typing import Any

from app.models.llm_provider import LlmProvider
from app.services.llm_client import (
    _anthropic_messages_url,
    _http_request,
    _ollama_root,
    _openai_root,
    get_active_providers_ordered,
    get_default_provider,
    normalize_base_url,
)

CHAT_TIMEOUT_SEC = 120


def resolve_provider(provider_id: int | None = None) -> LlmProvider | None:
    if provider_id:
        row = LlmProvider.query.get(int(provider_id))
        if row and row.is_active:
            return row
    return get_default_provider()


def chat_with_provider(
    provider: LlmProvider,
    messages: list[dict[str, Any]],
    *,
    max_tokens: int = 4096,
    json_mode: bool = False,
    images: list[dict[str, str]] | None = None,
) -> str:
    """调用已配置的大模型，返回 assistant 文本内容。"""
    ptype = (provider.provider_type or 'openai_compatible').strip()
    api_key = (provider.api_key or '').strip()
    model = (provider.model_name or '').strip()
    if not model:
        raise ValueError('未配置模型名称，请在系统设置中填写大模型 model')

    if ptype == 'openai_compatible':
        return _chat_openai_compatible(provider.base_url, api_key, model, messages, max_tokens, json_mode, images)
    if ptype == 'anthropic_compatible':
        return _chat_anthropic(provider.base_url, api_key, model, messages, max_tokens, images)
    return _chat_ollama(provider.base_url, model, messages, max_tokens, images)


def chat_with_fallback(
    messages: list[dict[str, Any]],
    *,
    provider_id: int | None = None,
    max_tokens: int = 4096,
    json_mode: bool = False,
    images: list[dict[str, str]] | None = None,
) -> tuple[str, LlmProvider]:
    """按优先级尝试可用 Provider，返回 (content, provider)。"""
    candidates: list[LlmProvider] = []
    preferred = resolve_provider(provider_id)
    if preferred:
        candidates.append(preferred)
    for row in get_active_providers_ordered():
        if preferred and row.id == preferred.id:
            continue
        candidates.append(row)

    if not candidates:
        raise ValueError('未配置可用的大模型，请先在系统设置中添加并启用')

    errors: list[str] = []
    for provider in candidates:
        try:
            content = chat_with_provider(
                provider,
                messages,
                max_tokens=max_tokens,
                json_mode=json_mode,
                images=images,
            )
            return content, provider
        except Exception as exc:  # noqa: BLE001
            errors.append(f'{provider.name or provider.id}: {exc}')
    raise ValueError('大模型调用失败：' + '；'.join(errors[:3]))


def _chat_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
    json_mode: bool,
    images: list[dict[str, str]] | None,
) -> str:
    root = _openai_root(base_url)
    headers: dict[str, str] = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    payload_messages = _inject_openai_images(messages, images)
    body: dict[str, Any] = {
        'model': model,
        'messages': payload_messages,
        'max_tokens': max_tokens,
        'stream': False,
    }
    if json_mode:
        body['response_format'] = {'type': 'json_object'}

    status, text = _http_request('POST', f'{root}/chat/completions', headers=headers, body=body, timeout=CHAT_TIMEOUT_SEC)
    if status >= 400:
        raise ValueError(_format_http_error(status, text))
    return _parse_openai_content(text)


def _inject_openai_images(
    messages: list[dict[str, Any]],
    images: list[dict[str, str]] | None,
) -> list[dict[str, Any]]:
    if not images:
        return messages
    out: list[dict[str, Any]] = []
    injected = False
    for msg in messages:
        if not injected and msg.get('role') == 'user':
            content: list[dict[str, Any]] = []
            text = msg.get('content')
            if isinstance(text, str) and text.strip():
                content.append({'type': 'text', 'text': text})
            for img in images:
                mime = img.get('mime') or 'image/jpeg'
                b64 = img.get('base64') or ''
                content.append(
                    {
                        'type': 'image_url',
                        'image_url': {'url': f'data:{mime};base64,{b64}'},
                    },
                )
            out.append({'role': 'user', 'content': content})
            injected = True
        else:
            out.append(msg)
    if not injected:
        content = [{'type': 'image_url', 'image_url': {'url': f"data:{i.get('mime', 'image/jpeg')};base64,{i.get('base64', '')}"}} for i in images]
        out.append({'role': 'user', 'content': content})
    return out


def _chat_anthropic(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
    images: list[dict[str, str]] | None,
) -> str:
    if not api_key:
        raise ValueError('Anthropic 兼容接口需配置 API Key')
    url = _anthropic_messages_url(base_url)
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
    }
    system_parts: list[str] = []
    api_messages: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get('role')
        text = msg.get('content')
        if role == 'system':
            if isinstance(text, str):
                system_parts.append(text)
            continue
        if role not in ('user', 'assistant'):
            continue
        if role == 'user' and images and not api_messages:
            blocks: list[dict[str, Any]] = []
            if isinstance(text, str) and text.strip():
                blocks.append({'type': 'text', 'text': text})
            for img in images:
                blocks.append(
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': img.get('mime') or 'image/jpeg',
                            'data': img.get('base64') or '',
                        },
                    },
                )
            api_messages.append({'role': 'user', 'content': blocks})
            images = None
        else:
            api_messages.append({'role': role, 'content': text if isinstance(text, str) else str(text)})

    body: dict[str, Any] = {
        'model': model,
        'max_tokens': max_tokens,
        'messages': api_messages,
    }
    if system_parts:
        body['system'] = '\n\n'.join(system_parts)

    status, text = _http_request('POST', url, headers=headers, body=body, timeout=CHAT_TIMEOUT_SEC)
    if status >= 400:
        raise ValueError(_format_http_error(status, text))
    return _parse_anthropic_content(text)


def _chat_ollama(
    base_url: str,
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
    images: list[dict[str, str]] | None,
) -> str:
    root = _ollama_root(base_url)
    ollama_messages: list[dict[str, Any]] = []
    image_payload = [img.get('base64') or '' for img in (images or []) if img.get('base64')]
    injected = False
    for msg in messages:
        item = {'role': msg.get('role'), 'content': msg.get('content')}
        if not injected and item['role'] == 'user' and image_payload:
            item['images'] = image_payload
            injected = True
        ollama_messages.append(item)

    body = {
        'model': model,
        'messages': ollama_messages,
        'stream': False,
        'options': {'num_predict': max_tokens},
    }
    status, text = _http_request('POST', f'{root}/api/chat', body=body, timeout=CHAT_TIMEOUT_SEC)
    if status >= 400:
        raise ValueError(_format_http_error(status, text))
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Ollama 返回非 JSON：{text[:200]}') from exc
    content = payload.get('message', {}).get('content')
    if not content:
        raise ValueError('Ollama 未返回内容')
    return str(content)


def _parse_openai_content(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f'OpenAI 兼容接口返回非 JSON：{text[:200]}') from exc
    choices = payload.get('choices') or []
    if not choices:
        raise ValueError('OpenAI 兼容接口未返回 choices')
    message = choices[0].get('message') or {}
    content = message.get('content')
    if not content:
        raise ValueError('OpenAI 兼容接口未返回 content')
    return str(content)


def _parse_anthropic_content(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Anthropic 接口返回非 JSON：{text[:200]}') from exc
    blocks = payload.get('content') or []
    parts = []
    for block in blocks:
        if isinstance(block, dict) and block.get('type') == 'text':
            parts.append(str(block.get('text') or ''))
    if not parts:
        raise ValueError('Anthropic 接口未返回文本内容')
    return ''.join(parts)


def _format_http_error(status: int, text: str) -> str:
    snippet = (text or '').strip().replace('\n', ' ')[:240]
    return f'HTTP {status}' + (f'：{snippet}' if snippet else '')


def extract_json_object(text: str) -> dict[str, Any]:
    """从模型输出中提取 JSON 对象。"""
    raw = (text or '').strip()
    if not raw:
        raise ValueError('模型未返回内容')
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw, re.I)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = raw.find('{')
    end = raw.rfind('}')
    if start >= 0 and end > start:
        snippet = raw[start : end + 1]
        data = json.loads(snippet)
        if isinstance(data, dict):
            return data
    raise ValueError('无法解析模型返回的 JSON')
