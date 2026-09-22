# -*- coding: utf-8 -*-
"""内置借项通知单打印模板配置。"""

BUILTIN_DEBIT_NOTE_CODE = 'debit_note_imc'
BUILTIN_DEBIT_NOTE_NAME = '借项通知单 (Debit Note)'

DEFAULT_DEBIT_NOTE_SCHEMA = {
    'version': 1,
    'page': {
        'size': 'A4',
        'orientation': 'portrait',
        'marginMm': 10,
    },
    'layout': 'debit_note_v1',
    'assets': {
        'logo': {'url': '', 'widthMm': 42, 'align': 'left'},
        'seal': {'url': '', 'widthMm': 36, 'opacity': 0.95},
    },
    'regions': {
        'headerLeft': {'blocks': ['logo']},
        'headerRight': {'blocks': ['company_info']},
        'metaRow': {'blocks': ['to_block', 'doc_meta']},
        'body': {'blocks': ['particulars_table']},
        'signature': {'blocks': ['seal_sign']},
        'footer': {'blocks': ['payment_advice']},
    },
    'blocks': {
        'logo': {'type': 'logo'},
        'company_info': {
            'type': 'richtext',
            'content': (
                'IMC Ship Management (Shanghai) Co., Ltd.\n'
                'Room 1003, No.6 China Overseas Building,\n'
                '76 Yan Ji Lu, Shi Bei District,\n'
                'Qingdao City, China 266024'
            ),
            'align': 'right',
        },
        'to_block': {
            'type': 'field_group',
            'items': [
                {'label': 'To:', 'fieldKey': 'recipient_company', 'subFieldKey': 'recipient_role'},
                {'label': 'Attn:', 'fieldKey': 'attn_name'},
                {'label': 'Re:', 'fieldKey': 're_subject'},
            ],
        },
        'doc_meta': {
            'type': 'field_group',
            'align': 'right',
            'items': [
                {'label': 'Debit Note:', 'fieldKey': 'debit_note_no'},
                {'label': 'Date:', 'fieldKey': 'issue_date', 'format': 'date_slash'},
            ],
        },
        'particulars_table': {
            'type': 'detail_table',
            'fieldKey': 'particulars',
            'title': 'PARTICULARS',
            'currencyLabel': 'USD ($)',
            'currencyFieldKey': 'currency',
            'columns': [
                {'key': 'description', 'header': 'Description', 'width': '42%'},
                {'key': 'period_month', 'header': 'Period/Month', 'width': '18%'},
                {'key': 'account_code', 'header': 'Code', 'width': '18%'},
                {
                    'key': 'amount',
                    'header': 'Amount',
                    'width': '22%',
                    'align': 'right',
                    'format': 'money_plain',
                },
            ],
            'showTotal': True,
            'totalLabel': 'Total',
            'totalFieldKey': 'total_amount',
        },
        'seal_sign': {
            'type': 'signature',
            'showSeal': True,
            'lines': [
                'Authorized Signature',
                'For IMC Ship Management (Shanghai) Co., Ltd.',
            ],
        },
        'payment_advice': {
            'type': 'kv_section',
            'showDivider': True,
            'left': [
                {'label': 'Beneficiary', 'value': 'IMC Ship Management (Shanghai) Co., Ltd.'},
                {'label': 'Account No.', 'value': '121902492332032'},
                {
                    'label': 'Bank',
                    'value': 'China Merchants Bank Shanghai Zhangyang Sub-Branch',
                },
                {'label': 'Swift Code', 'value': 'CMBCCNBS051'},
            ],
            'right': [
                {'label': 'Debit Note', 'fieldKey': 'debit_note_no'},
                {'label': 'Date', 'fieldKey': 'issue_date', 'format': 'date_slash'},
                {'label': 'Total Amount(USD)', 'fieldKey': 'total_amount', 'format': 'money_plain'},
            ],
        },
    },
    'styles': {
        'fontFamily': 'Arial, Helvetica, "Liberation Sans", sans-serif',
        'baseFontSizePt': 10,
        'tableBorderColor': '#333333',
    },
    'emailTemplates': {
        'en': {
            'subject': 'Debit Note {{debit_note_no}} - {{re_subject}}',
            'greeting': 'Dear {{recipient_name}},',
            'body': (
                'Please find the Debit Note {{debit_note_no}} dated {{issue_date}}.\n'
                'Total amount: {{currency}} {{total_amount}}.\n\n'
                'Payment details are included in the attached document.\n'
                'Should you have any questions, please do not hesitate to contact us.\n\n'
                'Best regards,\n{{company_name}}'
            ),
        },
        'zh': {
            'subject': '借项通知单 {{debit_note_no}} - {{re_subject}}',
            'greeting': '尊敬的 {{recipient_name}}：',
            'body': (
                '随信附上借项通知单 {{debit_note_no}}，开票日期 {{issue_date}}。\n'
                '合计金额：{{currency}} {{total_amount}}。\n\n'
                '付款信息详见附件单据。\n'
                '如有疑问，请随时与我们联系。\n\n'
                '此致\n{{company_name}}'
            ),
        },
    },
}


def build_builtin_debit_note_row() -> dict:
    import json

    return {
        'code': BUILTIN_DEBIT_NOTE_CODE,
        'name': BUILTIN_DEBIT_NOTE_NAME,
        'description': '内置借项通知单打印模板，可在管理后台调整文案、Logo、银行信息与字段绑定。',
        'category': 'invoice',
        'is_builtin': True,
        'is_active': True,
        'schema_json': json.dumps(DEFAULT_DEBIT_NOTE_SCHEMA, ensure_ascii=False),
    }
