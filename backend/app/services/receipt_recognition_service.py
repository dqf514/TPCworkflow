# -*- coding: utf-8 -*-
"""智能票据识别服务。"""
from __future__ import annotations

import base64
import io
import json
import os
import re
from datetime import datetime
from typing import Any

from flask import current_app
from PIL import Image

from app.services.llm_chat import chat_with_fallback, extract_json_object
from app.services.receipt_extract_keys import RECEIPT_JSON_SCHEMA_HINT

SCENE_LABELS = {
    'expense': '费用报销',
    'payment': '付款申请',
    'general': '通用凭证',
}

ALLOWED_UPLOAD_PREFIXES = ('uploads/attachments/', 'uploads/signatures/')


def list_extract_keys() -> list[dict[str, str]]:
    from app.services.receipt_extract_keys import RECEIPT_EXTRACT_KEYS

    return RECEIPT_EXTRACT_KEYS


def _project_base() -> str:
    return os.path.abspath(os.path.join(current_app.root_path, '..'))


def _resolve_upload_path(file_path: str) -> str:
    norm = (file_path or '').replace('\\', '/').lstrip('/')
    if '..' in norm.split('/'):
        raise ValueError('无效的文件路径')
    if not any(norm.startswith(p) for p in ALLOWED_UPLOAD_PREFIXES):
        raise ValueError('仅允许识别已上传的附件')
    full = os.path.join(_project_base(), norm)
    if not os.path.isfile(full):
        raise ValueError('文件不存在或已被删除')
    return full


def _read_image_base64(full_path: str) -> tuple[str, str]:
    ext = os.path.splitext(full_path)[1].lower()
    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
    }
    mime = mime_map.get(ext, 'image/jpeg')
    with Image.open(full_path) as img:
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        buf = io.BytesIO()
        save_fmt = 'JPEG' if mime == 'image/jpeg' else 'PNG'
        if save_fmt == 'JPEG':
            img.save(buf, format=save_fmt, quality=92)
            mime = 'image/jpeg'
        else:
            img.save(buf, format=save_fmt)
        data = base64.b64encode(buf.getvalue()).decode('ascii')
    return data, mime


def _pdf_to_image_base64(full_path: str) -> tuple[str, str] | None:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None
    doc = fitz.open(full_path)
    try:
        if doc.page_count < 1:
            return None
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        data = base64.b64encode(pix.tobytes('png')).decode('ascii')
        return data, 'image/png'
    finally:
        doc.close()


def _pdf_extract_text(full_path: str) -> str:
    try:
        import fitz
    except ImportError:
        return ''
    doc = fitz.open(full_path)
    try:
        if doc.page_count < 1:
            return ''
        return doc.load_page(0).get_text() or ''
    finally:
        doc.close()


def prepare_document(full_path: str) -> dict[str, Any]:
    ext = os.path.splitext(full_path)[1].lower()
    if ext == '.pdf':
        text = _pdf_extract_text(full_path).strip()
        if len(text) >= 80:
            return {'mode': 'text', 'text': text[:12000]}
        image = _pdf_to_image_base64(full_path)
        if image:
            b64, mime = image
            return {'mode': 'vision', 'images': [{'base64': b64, 'mime': mime}]}
        if text:
            return {'mode': 'text', 'text': text[:12000]}
        raise ValueError('无法读取 PDF 内容，请尝试上传图片格式')
    if ext in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}:
        b64, mime = _read_image_base64(full_path)
        return {'mode': 'vision', 'images': [{'base64': b64, 'mime': mime}]}
    raise ValueError('不支持的文件格式，请上传图片或 PDF')


def _build_prompt(
    scene: str,
    category_options: list[dict] | None,
    doc_text: str | None,
    form_fields: list[dict] | None = None,
) -> str:
    scene_label = SCENE_LABELS.get(scene, SCENE_LABELS['general'])
    options_hint = ''
    if category_options:
        labels = []
        for opt in category_options[:80]:
            label = opt.get('label') or opt.get('name') or opt.get('value')
            value = opt.get('value') or opt.get('code')
            if label:
                labels.append(f'{label}({value})' if value else str(label))
        if labels:
            options_hint = (
                '\n费用类别请优先从以下选项中选择最接近的一项，并写入 expense_category（中文标签）'
                '；同时尽量给出匹配的 value 到 expense_category_code：\n'
                + '、'.join(labels)
            )

    form_fields_hint = ''
    if form_fields:
        compact_fields = []
        for f in form_fields[:40]:
            item: dict[str, Any] = {
                'key': f.get('key'),
                'label': f.get('label'),
                'type': f.get('type'),
            }
            if f.get('scope'):
                item['scope'] = f.get('scope')
            opts = f.get('options') or []
            if opts:
                item['options'] = [
                    {
                        'label': o.get('label') or o.get('name') or o.get('value'),
                        'value': o.get('value') or o.get('code'),
                    }
                    for o in opts[:30]
                ]
            compact_fields.append(item)
        fields_json = json.dumps(compact_fields, ensure_ascii=False)
        form_fields_hint = f"""

8. 另需根据下列表单字段（key 为写入键名，label 为字段中文名）将票据信息填入 smart_fill 对象：
{fields_json}
   - 仅填你有把握的字段；无法确认不要写入 smart_fill。
   - 根据 label 语义匹配（如「费用项目/消费类别」→ expense_category，「公司/商户」→ merchant_name）。
   - money 类型：{{"currency":"CNY","amount":12.00,"exchange_rate":1,"rmb_amount":12.00}}
   - select/radio 类型：填 options 中的 value（不是 label）
   - date 类型：YYYY-MM-DD
   - 系统会优先使用映射规则；smart_fill 仅补充规则未填上的字段。"""

    text_block = ''
    if doc_text:
        text_block = f'\n\n以下为从文档提取的文本供参考：\n{doc_text[:8000]}'

    return f"""请识别用户上传的企业费用凭证（票据/收据/收条/Invoice/Receipt/小票/发票等），业务场景：{scene_label}。

支持但不限于：中国增值税发票、电子发票、出租车票、火车票、机票行程单、餐饮/酒店小票、定额发票、机打收据、手写收条；
以及海外 Receipt、Invoice、Tax Invoice、Hotel Bill、信用卡签购单、网约车行程单、支付截图等。

要求：
1. 仅返回一个 JSON 对象，不要 markdown 或解释文字。
2. 无法确认的字段填 null，禁止编造金额或日期。
3. 金额保留两位小数；日期统一 YYYY-MM-DD；时间 HH:MM。
4. currency 使用 ISO 4217（如 CNY、USD、EUR、JPY、HKD）。
5. country_region 使用 ISO 3166-1 alpha-2（如 CN、US）。
6. confidence 与 field_confidence 取 0~1；不确定时在 warnings 中说明。
7. 不要因不是「发票」而拒绝识别，收据和小票同样处理。{options_hint}{form_fields_hint}{text_block}

JSON 结构示例：
{RECEIPT_JSON_SCHEMA_HINT}"""


def recognize_receipt(
    file_path: str,
    *,
    scene: str = 'expense',
    provider_id: int | None = None,
    mappings: list[dict] | None = None,
    category_options: list[dict] | None = None,
    form_fields: list[dict] | None = None,
) -> dict[str, Any]:
    full_path = _resolve_upload_path(file_path)
    prepared = prepare_document(full_path)
    images = prepared.get('images')
    doc_text = prepared.get('text') if prepared.get('mode') == 'text' else None

    system_msg = '你是专业的企业费用票据识别助手，擅长中国与海外各类凭证的结构化提取。'
    user_prompt = _build_prompt(
        scene or 'expense',
        category_options,
        doc_text,
        form_fields,
    )

    messages = [
        {'role': 'system', 'content': system_msg},
        {'role': 'user', 'content': user_prompt},
    ]

    content, provider = chat_with_fallback(
        messages,
        provider_id=provider_id,
        max_tokens=4096,
        json_mode=True,
        images=images if prepared.get('mode') == 'vision' else None,
    )
    raw_obj = extract_json_object(content)
    smart_fill = raw_obj.pop('smart_fill', None)
    if not isinstance(smart_fill, dict):
        smart_fill = {}
    extracted = _normalize_extracted(raw_obj, category_options)
    fill_suggestions, warnings = build_fill_suggestions(
        extracted,
        mappings or [],
        category_options,
        form_fields=form_fields,
        smart_fill=smart_fill,
    )

    all_warnings = list(extracted.get('warnings') or [])
    all_warnings.extend(warnings)

    return {
        'extracted': extracted,
        'fill_suggestions': fill_suggestions,
        'warnings': all_warnings,
        'provider_used': provider.name or provider.model_name or f'Provider#{provider.id}',
        'recognition_mode': prepared.get('mode'),
    }


def _normalize_extracted(data: dict[str, Any], category_options: list[dict] | None) -> dict[str, Any]:
    out = dict(data or {})
    for money_key in ('total_amount', 'amount_before_tax', 'tax_amount'):
        val = out.get(money_key)
        if val is not None and val != '':
            try:
                out[money_key] = round(float(val), 2)
            except (TypeError, ValueError):
                out[money_key] = None

    date_raw = out.get('transaction_date')
    if date_raw:
        out['transaction_date'] = _normalize_date(str(date_raw))

    currency = str(out.get('currency') or 'CNY').upper().strip()
    out['currency'] = currency or 'CNY'

    if category_options and out.get('expense_category') and not out.get('expense_category_code'):
        matched = match_category_option(str(out.get('expense_category')), category_options)
        if matched:
            out['expense_category_code'] = matched.get('value') or matched.get('code')

    conf = out.get('confidence')
    try:
        out['confidence'] = max(0.0, min(1.0, float(conf))) if conf is not None else None
    except (TypeError, ValueError):
        out['confidence'] = None

    return out


def _normalize_date(raw: str) -> str | None:
    s = raw.strip()
    if not s:
        return None
    m = re.match(r'^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mo, d).strftime('%Y-%m-%d')
        except ValueError:
            return None
    m = re.match(r'^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})', s)
    if m:
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mo, d).strftime('%Y-%m-%d')
        except ValueError:
            return None
    return None


def match_category_option(label: str, options: list[dict] | None) -> dict | None:
    if not label or not options:
        return None
    needle = label.strip().lower()
    for opt in options:
        for key in ('label', 'name', 'value'):
            val = opt.get(key)
            if val and str(val).strip().lower() == needle:
                return opt
    for opt in options:
        for key in ('label', 'name'):
            val = opt.get(key)
            if val and (needle in str(val).lower() or str(val).lower() in needle):
                return opt
    return None


def _money_value(amount: Any, currency: str = 'CNY') -> dict[str, Any]:
    if amount is None or amount == '':
        return {
            'currency': currency or 'CNY',
            'amount': None,
            'exchange_rate': 1,
            'rmb_amount': None,
        }
    try:
        num = round(float(amount), 2)
    except (TypeError, ValueError):
        return {
            'currency': currency or 'CNY',
            'amount': None,
            'exchange_rate': 1,
            'rmb_amount': None,
        }
    cur = (currency or 'CNY').upper()
    rmb = num if cur == 'CNY' else None
    return {
        'currency': cur,
        'amount': num,
        'exchange_rate': 1,
        'rmb_amount': rmb,
    }


def _value_for_extract_key(extracted: dict, extract_key: str, category_options: list[dict] | None) -> Any:
    currency = str(extracted.get('currency') or 'CNY').upper()
    if extract_key in ('total_amount', 'amount_before_tax', 'tax_amount'):
        return _money_value(extracted.get(extract_key), currency)
    if extract_key == 'currency':
        return currency
    if extract_key == 'expense_category':
        code = extracted.get('expense_category_code')
        if code:
            return code
        label = extracted.get('expense_category')
        matched = match_category_option(str(label or ''), category_options)
        if matched:
            return matched.get('value') or matched.get('code') or label
        return label
    return extracted.get(extract_key)


def _has_meaningful_value(val: Any) -> bool:
    if val is None or val == '':
        return False
    if isinstance(val, dict):
        if 'amount' in val:
            amt = val.get('amount')
            return amt is not None and amt != ''
        return bool(val)
    if isinstance(val, list):
        return len(val) > 0
    return True


def _coerce_field_value(field: dict, raw: Any, extracted: dict) -> Any:
    ftype = str(field.get('type') or 'input')
    currency = str(extracted.get('currency') or 'CNY').upper()
    options = field.get('options') or []

    if raw is None or raw == '':
        return None

    if ftype == 'money':
        if isinstance(raw, dict):
            cur = str(raw.get('currency') or currency).upper()
            return _money_value(raw.get('amount'), cur)
        return _money_value(raw, currency)
    if ftype == 'date':
        return _normalize_date(str(raw))
    if ftype in ('select', 'radio'):
        matched = match_category_option(str(raw), options)
        if matched:
            return matched.get('value') or matched.get('code') or raw
        return raw
    if ftype == 'multi_select':
        items = raw if isinstance(raw, list) else [raw]
        out = []
        for item in items:
            matched = match_category_option(str(item), options)
            out.append(matched.get('value') or matched.get('code') or item if matched else item)
        return out
    if ftype == 'number':
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
    return raw


def _merge_smart_fill(
    main: dict[str, Any],
    detail_row: dict[str, Any],
    form_fields: list[dict] | None,
    smart_fill: dict[str, Any] | None,
    extracted: dict,
) -> int:
    """将 LLM smart_fill 合并进建议，跳过已有映射值的字段。返回补充字段数。"""
    if not form_fields or not smart_fill:
        return 0

    field_map = {str(f.get('key')): f for f in form_fields if f.get('key')}
    filled_count = 0

    for key, raw_val in smart_fill.items():
        field = field_map.get(str(key))
        if not field:
            continue
        scope = str(field.get('scope') or 'detail')
        target = main if scope == 'main' else detail_row
        if _has_meaningful_value(target.get(key)):
            continue
        val = _coerce_field_value(field, raw_val, extracted)
        if not _has_meaningful_value(val):
            continue
        target[key] = val
        filled_count += 1

    return filled_count


def build_fill_suggestions(
    extracted: dict,
    mappings: list[dict],
    category_options: list[dict] | None,
    form_fields: list[dict] | None = None,
    smart_fill: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    main: dict[str, Any] = {}
    detail_row: dict[str, Any] = {}
    warnings: list[str] = []

    for item in mappings or []:
        extract_key = (item.get('extractKey') or item.get('extract_key') or '').strip()
        target_key = (item.get('targetKey') or item.get('target_key') or '').strip()
        scope = (item.get('targetScope') or item.get('target_scope') or 'detail').strip()
        if not extract_key or not target_key:
            continue
        val = _value_for_extract_key(extracted, extract_key, category_options)
        if val is None or val == '':
            continue
        if scope == 'main':
            main[target_key] = val
        else:
            detail_row[target_key] = val

    smart_count = _merge_smart_fill(main, detail_row, form_fields, smart_fill, extracted)
    if smart_count > 0:
        warnings.append(f'已根据字段名称智能补充 {smart_count} 项')

    fc = extracted.get('field_confidence') or {}
    if isinstance(fc, dict):
        cat_conf = fc.get('expense_category')
        try:
            if cat_conf is not None and float(cat_conf) < 0.75:
                warnings.append('费用类别置信度较低，请人工确认')
        except (TypeError, ValueError):
            pass

    conf = extracted.get('confidence')
    try:
        if conf is not None and float(conf) < 0.6:
            warnings.append('整体识别置信度较低，请核对金额与日期')
    except (TypeError, ValueError):
        pass

    return {'main': main, 'detail_row': detail_row}, warnings
