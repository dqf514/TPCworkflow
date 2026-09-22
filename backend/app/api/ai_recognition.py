# -*- coding: utf-8 -*-
"""智能票据识别 API。"""
from flask import Blueprint, request
from flask_login import login_required

from app.services.receipt_recognition_service import list_extract_keys, recognize_receipt
from app.utils.response import fail, ok

ai_recognition_api = Blueprint('ai_recognition_api', __name__)


@ai_recognition_api.route('/ai/receipt-extract-keys', methods=['GET'])
@login_required
def receipt_extract_keys():
    return ok(list_extract_keys())


@ai_recognition_api.route('/ai/recognize-receipt', methods=['POST'])
@login_required
def recognize_receipt_api():
    data = request.get_json(silent=True) or {}
    file_path = (data.get('file_path') or '').strip()
    if not file_path:
        return fail('请提供已上传文件的路径')

    scene = (data.get('scene') or 'expense').strip() or 'expense'
    provider_id = data.get('provider_id')
    if provider_id is not None and provider_id != '':
        try:
            provider_id = int(provider_id)
        except (TypeError, ValueError):
            return fail('provider_id 无效')
    else:
        provider_id = None

    mappings = data.get('mappings') or []
    if not isinstance(mappings, list):
        return fail('mappings 格式无效')

    category_options = data.get('category_options') or []
    if not isinstance(category_options, list):
        category_options = []

    form_fields = data.get('form_fields') or []
    if not isinstance(form_fields, list):
        form_fields = []

    try:
        result = recognize_receipt(
            file_path,
            scene=scene,
            provider_id=provider_id,
            mappings=mappings,
            category_options=category_options,
            form_fields=form_fields,
        )
    except ValueError as exc:
        return fail(str(exc))
    except Exception as exc:  # noqa: BLE001
        return fail(f'识别失败：{exc}')

    company_id = data.get('company_id')
    exclude_instance_ref = data.get('exclude_instance_ref') or data.get('exclude_instance_id')
    duplicate = None
    if company_id not in (None, ''):
        try:
            from app.services.receipt_duplicate_service import check_extracted_duplicate

            duplicate = check_extracted_duplicate(
                int(company_id),
                result.get('extracted'),
                file_path,
                exclude_instance_ref,
            )
        except (TypeError, ValueError):
            duplicate = None
    if duplicate:
        result['duplicate'] = duplicate
        warns = list(result.get('warnings') or [])
        label = duplicate.get('display_no') or duplicate.get('instance_id')
        doc = duplicate.get('document_number') or file_path.rsplit('/', 1)[-1]
        warns.insert(0, f'该票据（{doc}）已在已通过申请 {label} 中使用，不可重复报销')
        result['warnings'] = warns

    return ok(result, '识别完成')
