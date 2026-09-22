# -*- coding: utf-8 -*-
"""标准报销单内置模板（含智能票据 + 费用明细）。"""
from __future__ import annotations

import copy
import json

from app.services.form_schema import DEFAULT_SCHEMA, validate_schema
from app.services.workflow_settings import DEFAULT_WORKFLOW_SETTINGS

TEMPLATE_KEY = 'std_expense_reimburse'
TEMPLATE_NAME = '标准报销单'
TEMPLATE_DESCRIPTION = (
    '内置模板：上传票据自动识别并填入费用明细，适用于日常费用报销。'
    '含报销事由、费用承担部门、智能票据、明细表与收款信息。'
)

EXPENSE_CATEGORY_OPTIONS = [
    {'name': '交通费', 'code': 'traffic', 'label': '交通费', 'value': 'traffic'},
    {'name': '餐饮费', 'code': 'meal', 'label': '餐饮费', 'value': 'meal'},
    {'name': '住宿费', 'code': 'hotel', 'label': '住宿费', 'value': 'hotel'},
    {'name': '办公费', 'code': 'office', 'label': '办公费', 'value': 'office'},
    {'name': '通讯费', 'code': 'telecom', 'label': '通讯费', 'value': 'telecom'},
    {'name': '差旅费', 'code': 'travel', 'label': '差旅费', 'value': 'travel'},
    {'name': '培训费', 'code': 'training', 'label': '培训费', 'value': 'training'},
    {'name': '其他', 'code': 'other', 'label': '其他', 'value': 'other'},
]

SPAN_HALF = {'desktop': 12, 'mobile': 24}
SPAN_FULL = {'desktop': 24, 'mobile': 24}


def build_expense_reimbursement_schema() -> dict:
    schema = copy.deepcopy(DEFAULT_SCHEMA)
    schema['title'] = TEMPLATE_NAME
    schema['description'] = TEMPLATE_DESCRIPTION
    schema['sections'] = [
        {
            'id': 'section_basic',
            'title': '基本信息',
            'collapsed': False,
            'fields': [
                {
                    'id': 'fld_reason',
                    'key': 'reason',
                    'type': 'textarea',
                    'label': '报销事由',
                    'required': True,
                    'visible': True,
                    'printable': True,
                    'placeholder': '请简要说明报销背景与用途',
                    'span': SPAN_FULL,
                    'props': {},
                },
                {
                    'id': 'fld_cost_dept',
                    'key': 'cost_department',
                    'type': 'dept_picker',
                    'label': '费用承担部门',
                    'required': True,
                    'visible': True,
                    'printable': True,
                    'span': SPAN_HALF,
                    'props': {
                        'multiple': False,
                        'defaultPrimaryDept': True,
                        'syncApplyOrg': True,
                    },
                },
            ],
        },
        {
            'id': 'section_receipt',
            'title': '票据识别',
            'collapsed': False,
            'fields': [
                {
                    'id': 'fld_smart_receipt',
                    'key': 'smart_receipt_uploads',
                    'type': 'smart_receipt',
                    'label': '智能票据',
                    'required': False,
                    'visible': True,
                    'printable': True,
                    'description': '上传发票、收据、小票等（图片或 PDF），识别后确认填入下方明细',
                    'span': SPAN_FULL,
                    'props': {
                        'accept': 'image/jpeg,image/png,image/webp,image/gif,.pdf',
                        'maxCount': 20,
                        'recognition': {
                            'enabled': True,
                            'scene': 'expense',
                            'providerId': None,
                            'fillMode': 'detail_row',
                            'targetDetailKey': 'expense_items',
                            'mappings': [
                                {
                                    'extractKey': 'total_amount',
                                    'targetKey': 'amount',
                                    'targetScope': 'detail',
                                },
                                {
                                    'extractKey': 'expense_category',
                                    'targetKey': 'expense_type',
                                    'targetScope': 'detail',
                                },
                                {
                                    'extractKey': 'transaction_date',
                                    'targetKey': 'occur_date',
                                    'targetScope': 'detail',
                                },
                                {
                                    'extractKey': 'merchant_name',
                                    'targetKey': 'remark',
                                    'targetScope': 'detail',
                                },
                                {
                                    'extractKey': 'document_number',
                                    'targetKey': 'voucher_no',
                                    'targetScope': 'detail',
                                },
                            ],
                            'categoryFieldKey': 'expense_type',
                            'autoFill': True,
                            'attachToFieldKey': 'invoice_file',
                            'attachToScope': 'detail',
                        },
                    },
                },
            ],
        },
        {
            'id': 'section_items',
            'title': '费用明细',
            'collapsed': False,
            'fields': [
                {
                    'id': 'fld_expense_items',
                    'key': 'expense_items',
                    'type': 'detail',
                    'label': '报销明细',
                    'required': True,
                    'visible': True,
                    'printable': True,
                    'span': SPAN_FULL,
                    'props': {
                        'showSummary': True,
                        'minRows': 0,
                        'maxRows': 50,
                        'columns': [
                            {
                                'id': 'col_expense_type',
                                'key': 'expense_type',
                                'type': 'select',
                                'label': '消费类别',
                                'required': True,
                                'visible': True,
                                'printable': True,
                                'span': SPAN_HALF,
                                'props': {
                                    'optionSource': 'manual',
                                    'options': copy.deepcopy(EXPENSE_CATEGORY_OPTIONS),
                                },
                            },
                            {
                                'id': 'col_occur_date',
                                'key': 'occur_date',
                                'type': 'date',
                                'label': '发生日期',
                                'required': True,
                                'visible': True,
                                'printable': True,
                                'span': SPAN_HALF,
                                'props': {},
                            },
                            {
                                'id': 'col_amount',
                                'key': 'amount',
                                'type': 'money',
                                'label': '金额',
                                'required': True,
                                'visible': True,
                                'printable': True,
                                'span': SPAN_HALF,
                                'props': {'precision': 2},
                                'defaultValue': {
                                    'currency': 'CNY',
                                    'amount': None,
                                    'exchange_rate': 1,
                                    'rmb_amount': None,
                                },
                            },
                            {
                                'id': 'col_voucher_no',
                                'key': 'voucher_no',
                                'type': 'input',
                                'label': '票号/订单号',
                                'required': False,
                                'visible': True,
                                'printable': True,
                                'span': SPAN_HALF,
                                'props': {},
                            },
                            {
                                'id': 'col_remark',
                                'key': 'remark',
                                'type': 'input',
                                'label': '商户/备注',
                                'required': False,
                                'visible': True,
                                'printable': True,
                                'span': SPAN_HALF,
                                'props': {},
                            },
                            {
                                'id': 'col_invoice_file',
                                'key': 'invoice_file',
                                'type': 'attachment',
                                'label': '票据附件',
                                'required': False,
                                'visible': True,
                                'printable': True,
                                'span': SPAN_HALF,
                                'props': {
                                    'allowMultiple': False,
                                    'maxCount': 1,
                                    'accept': 'image/jpeg,image/png,image/webp,image/gif,.pdf',
                                    'recognition': {
                                        'enabled': True,
                                        'scene': 'expense',
                                        'providerId': None,
                                        'mappings': [
                                            {
                                                'extractKey': 'total_amount',
                                                'targetKey': 'amount',
                                                'targetScope': 'detail',
                                            },
                                            {
                                                'extractKey': 'expense_category',
                                                'targetKey': 'expense_type',
                                                'targetScope': 'detail',
                                            },
                                            {
                                                'extractKey': 'transaction_date',
                                                'targetKey': 'occur_date',
                                                'targetScope': 'detail',
                                            },
                                            {
                                                'extractKey': 'merchant_name',
                                                'targetKey': 'remark',
                                                'targetScope': 'detail',
                                            },
                                            {
                                                'extractKey': 'document_number',
                                                'targetKey': 'voucher_no',
                                                'targetScope': 'detail',
                                            },
                                        ],
                                        'categoryFieldKey': 'expense_type',
                                        'autoFill': True,
                                    },
                                },
                            },
                        ],
                    },
                },
            ],
        },
        {
            'id': 'section_payment',
            'title': '收款信息',
            'collapsed': False,
            'fields': [
                {
                    'id': 'fld_payee_name',
                    'key': 'payee_name',
                    'type': 'input',
                    'label': '收款户名',
                    'required': True,
                    'visible': True,
                    'printable': True,
                    'placeholder': '与银行卡户名一致',
                    'span': SPAN_HALF,
                    'props': {},
                },
                {
                    'id': 'fld_bank_account',
                    'key': 'bank_account',
                    'type': 'input',
                    'label': '银行账号',
                    'required': True,
                    'visible': True,
                    'printable': True,
                    'span': SPAN_HALF,
                    'props': {},
                },
                {
                    'id': 'fld_bank_name',
                    'key': 'bank_name',
                    'type': 'input',
                    'label': '开户行',
                    'required': True,
                    'visible': True,
                    'printable': True,
                    'placeholder': '如：中国工商银行上海分行 XX 支行',
                    'span': SPAN_FULL,
                    'props': {},
                },
            ],
        },
    ]
    errs = validate_schema(schema)
    if errs:
        raise ValueError('标准报销单 schema 无效：' + '；'.join(errs))
    schema.setdefault('print', {})
    schema['print']['showDescription'] = False
    return schema


def build_expense_reimbursement_process_graph(admin_user_id: int | None = None) -> dict:
    """部门负责人审批 → 结束（可按需在设计器中增加财务节点）。"""
    return {
        'nodes': [
            {'id': 'start', 'type': 'start', 'x': 120, 'y': 280},
            {
                'id': 'approve_dept',
                'type': 'approver',
                'x': 360,
                'y': 280,
                'config': {
                    'assignee_type': 'flow_role',
                    'flow_role_code': 'dept_leader',
                    'apv_rel': 'or',
                },
            },
            {
                'id': 'approve_finance',
                'type': 'approver',
                'x': 600,
                'y': 280,
                'config': {
                    'assignee_type': 'fixed_users',
                    'user_ids': [admin_user_id] if admin_user_id else [],
                    'apv_rel': 'or',
                },
            },
            {'id': 'end', 'type': 'end', 'x': 840, 'y': 280},
        ],
        'edges': [
            {'source': 'start', 'target': 'approve_dept'},
            {'source': 'approve_dept', 'target': 'approve_finance'},
            {'source': 'approve_finance', 'target': 'end'},
        ],
    }


def build_expense_reimbursement_workflow_settings() -> dict:
    settings = copy.deepcopy(DEFAULT_WORKFLOW_SETTINGS)
    settings['require_comment'] = True
    settings['require_handwritten_sign'] = False
    return settings


def build_expense_reimbursement_template_payload() -> dict:
    schema = build_expense_reimbursement_schema()
    return {
        'key': TEMPLATE_KEY,
        'name': TEMPLATE_NAME,
        'description': TEMPLATE_DESCRIPTION,
        'icon': 'reimburse',
        'schema': schema,
        'workflow': {
            'key': TEMPLATE_KEY,
            'name': TEMPLATE_NAME,
            'scope_type': 'global',
            'process_graph': build_expense_reimbursement_process_graph(),
            'settings': build_expense_reimbursement_workflow_settings(),
        },
    }


def template_payload_json() -> str:
    return json.dumps(build_expense_reimbursement_template_payload(), ensure_ascii=False)
