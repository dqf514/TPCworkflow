# -*- coding: utf-8 -*-
"""借项通知单（Debit Note）内置表单与流程模板。"""
from __future__ import annotations

import copy
import uuid

from app.services.form_schema import DEFAULT_SCHEMA, validate_schema
from app.services.form_templates._builder import (
    SPAN_FULL,
    SPAN_HALF,
    build_standard_process_graph,
    build_workflow_settings,
    f_date,
    f_input,
    f_select,
    opt,
)
from app.services.print_templates.builtin_debit_note import BUILTIN_DEBIT_NOTE_CODE
from app.services.workflow_settings import DEFAULT_WORKFLOW_SETTINGS

TEMPLATE_KEY = 'std_debit_note'
TEMPLATE_NAME = '借项通知单申请'
TEMPLATE_DESCRIPTION = (
    '内置模板：借项通知单（Debit Note）申请，含收件人、费用明细与邮件投递设置；'
    '审批通过后可按流程设置自动发送英文/中文邮件。'
)


def _fid(prefix: str) -> str:
    return f'fld_{prefix}_{uuid.uuid4().hex[:6]}'


def _f_email(key: str, label: str, *, required=False):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'email',
        'label': label,
        'required': required,
        'visible': True,
        'printable': False,
        'span': SPAN_HALF,
        'props': {},
    }


def _f_serial(key: str, label: str, *, pattern: str):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'serial_no',
        'label': label,
        'required': True,
        'visible': True,
        'printable': True,
        'readonly': True,
        'span': SPAN_HALF,
        'props': {
            'pattern': pattern,
            'resetCycle': 'month',
        },
    }


def _f_plain_amount(key: str, label: str, *, required=False):
    return {
        'id': _fid(key),
        'key': key,
        'type': 'plain_amount',
        'label': label,
        'required': required,
        'visible': True,
        'printable': True,
        'span': SPAN_HALF,
        'props': {'precision': 2},
    }


def _f_formula_total():
    return {
        'id': _fid('total_amount'),
        'key': 'total_amount',
        'type': 'formula',
        'label': '合计金额',
        'required': False,
        'visible': True,
        'printable': True,
        'readonly': True,
        'span': SPAN_HALF,
        'props': {
            'expression': 'SUM(${particulars.amount})',
            'precision': 2,
        },
    }


def build_debit_note_schema() -> dict:
    schema = copy.deepcopy(DEFAULT_SCHEMA)
    schema['title'] = TEMPLATE_NAME
    schema['description'] = TEMPLATE_DESCRIPTION
    schema['print'] = {
        'enabled': True,
        'templateMode': 'custom',
        'templateCode': BUILTIN_DEBIT_NOTE_CODE,
        'pageSize': 'A4',
        'orientation': 'portrait',
        'marginMm': 10,
        'showTitle': False,
        'showDescription': False,
        'showInitiator': False,
        'showCompany': False,
        'showPrintTime': False,
        'showApprovalHistory': False,
    }
    schema['sections'] = [
        {
            'id': 'sec_recipient',
            'title': '收件人信息',
            'collapsed': False,
            'fields': [
                f_input('recipient_company', '收件公司 (To)', required=True, span=SPAN_FULL),
                f_input('recipient_role', '收件方说明', required=False, placeholder='如 The Owner of Selo'),
                f_input('attn_name', '联系人 (Attn)', required=True),
                f_input('re_subject', '主题 (Re)', required=True, placeholder='船名/项目'),
                f_input('recipient_name', '收件人姓名', required=False, placeholder='邮件称呼用'),
                _f_email('recipient_email', '收件人邮箱', required=True),
                _f_email('recipient_email_cc', '抄送邮箱', required=False),
                f_select(
                    'email_language',
                    '邮件语言',
                    [
                        opt('English', 'en'),
                        opt('中文', 'zh'),
                    ],
                    required=True,
                ),
            ],
        },
        {
            'id': 'sec_doc',
            'title': '单据信息',
            'collapsed': False,
            'fields': [
                _f_serial('debit_note_no', 'Debit Note 编号', pattern='R-CS-{YYYY}{MM}{SEQ:3}'),
                f_date('issue_date', '开票日期', required=True),
                f_select(
                    'currency',
                    '币种',
                    [
                        opt('USD', 'USD'),
                        opt('CNY', 'CNY'),
                        opt('EUR', 'EUR'),
                    ],
                    required=True,
                ),
                f_input('vessel_name', '船名', required=False),
            ],
        },
        {
            'id': 'sec_items',
            'title': '费用明细 (Particulars)',
            'collapsed': False,
            'fields': [
                {
                    'id': _fid('particulars'),
                    'key': 'particulars',
                    'type': 'detail',
                    'label': '费用明细',
                    'required': True,
                    'visible': True,
                    'printable': True,
                    'span': SPAN_FULL,
                    'props': {
                        'minRows': 1,
                        'maxRows': 50,
                        'columns': [
                            {
                                'id': 'col_desc',
                                'key': 'description',
                                'type': 'input',
                                'label': 'Description',
                                'required': True,
                                'visible': True,
                                'printable': True,
                                'span': SPAN_HALF,
                                'props': {},
                            },
                            {
                                'id': 'col_period',
                                'key': 'period_month',
                                'type': 'input',
                                'label': 'Period/Month',
                                'required': True,
                                'visible': True,
                                'printable': True,
                                'span': SPAN_HALF,
                                'props': {},
                            },
                            {
                                'id': 'col_code',
                                'key': 'account_code',
                                'type': 'input',
                                'label': 'Code',
                                'required': False,
                                'visible': True,
                                'printable': True,
                                'span': SPAN_HALF,
                                'props': {},
                            },
                            {
                                'id': 'col_amount',
                                'key': 'amount',
                                'type': 'plain_amount',
                                'label': 'Amount',
                                'required': True,
                                'visible': True,
                                'printable': True,
                                'span': SPAN_HALF,
                                'props': {'precision': 2, 'showSummary': True},
                            },
                        ],
                    },
                },
                _f_formula_total(),
            ],
        },
        {
            'id': 'sec_internal',
            'title': '内部备注',
            'collapsed': True,
            'fields': [
                {
                    'id': _fid('internal_remark'),
                    'key': 'internal_remark',
                    'type': 'textarea',
                    'label': '内部备注',
                    'required': False,
                    'visible': True,
                    'printable': False,
                    'span': SPAN_FULL,
                    'props': {'rows': 3},
                },
            ],
        },
    ]
    errs = validate_schema(schema)
    if errs:
        raise ValueError('借项通知单 schema 无效：' + '；'.join(errs))
    return schema


def build_debit_note_workflow_settings() -> dict:
    settings = copy.deepcopy(DEFAULT_WORKFLOW_SETTINGS)
    settings['require_comment'] = True
    settings['require_handwritten_sign'] = False
    settings['document_delivery'] = {
        'enabled': True,
        'template_code': BUILTIN_DEBIT_NOTE_CODE,
        'recipient_email_field': 'recipient_email',
        'recipient_name_field': 'recipient_name',
        'email_language_field': 'email_language',
        'cc_email_field': 'recipient_email_cc',
    }
    return settings


def build_debit_note_template_payload(admin_user_id: int | None = None) -> dict:
    return {
        'key': TEMPLATE_KEY,
        'name': TEMPLATE_NAME,
        'description': TEMPLATE_DESCRIPTION,
        'icon': 'invoice',
        'schema': build_debit_note_schema(),
        'workflow': {
            'key': TEMPLATE_KEY,
            'name': TEMPLATE_NAME,
            'scope_type': 'global',
            'process_graph': build_standard_process_graph(admin_user_id),
            'settings': build_debit_note_workflow_settings(),
        },
    }
