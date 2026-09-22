# -*- coding: utf-8 -*-
"""用友 YonSuite BIP 凭证导入：流程类型与导出参数配置。"""
from __future__ import annotations

from copy import deepcopy

# 导出弹窗中的可配置项（运行时填写，会写入凭证模板对应列）
OPTION_FIELD = dict  # key, label, type, required, default, placeholder, hint

FINANCE_EXPORT_PROFILES: list[dict] = [
    {
        'id': 'expense_reimburse',
        'name': '报销单凭证',
        'description': '将标准报销单按费用明细生成借方分录，并汇总贷方应付职工薪酬/其他应付款。',
        'definition_keys': ['std_expense_reimburse'],
        'definition_names': ['报销申请', '标准报销单', '报销单'],
        'mode': 'expense_detail',
        'options': [
            {
                'key': 'org_code',
                'label': '会计主体编码',
                'type': 'text',
                'required': True,
                'default': '',
                'placeholder': '如：004',
            },
            {
                'key': 'accBook_code',
                'label': '账簿编码',
                'type': 'text',
                'required': True,
                'default': '',
                'placeholder': '如：004-01',
            },
            {
                'key': 'voucherType_voucherstr',
                'label': '凭证类型',
                'type': 'text',
                'required': True,
                'default': '记',
                'placeholder': '如：记',
            },
            {
                'key': 'debit_accSubject_code',
                'label': '费用科目（默认）',
                'type': 'text',
                'required': True,
                'default': '6602',
                'placeholder': '明细行借方科目，未单独映射时使用',
            },
            {
                'key': 'credit_accSubject_code',
                'label': '贷方科目',
                'type': 'text',
                'required': True,
                'default': '224102',
                'placeholder': '汇总贷方科目，如其他应付款',
            },
            {
                'key': 'dept_aux_code',
                'label': '部门辅助核算编码',
                'type': 'text',
                'required': False,
                'default': '',
                'placeholder': '留空则使用费用承担部门名称',
                'hint': '对应模板「部门_编码」列；留空时写入部门名称供手工对照',
            },
            {
                'key': 'bank_accSubject_code',
                'label': '银行存款科目',
                'type': 'text',
                'required': False,
                'default': '100201',
                'placeholder': '启用付款行时使用',
            },
            {
                'key': 'include_bank_line',
                'label': '增加银行存款付款行',
                'type': 'switch',
                'required': False,
                'default': False,
                'hint': '在贷方应付后追加一行：借应付、贷银行存款（带银行账号）',
            },
            {
                'key': 'approved_only',
                'label': '仅导出已通过流程',
                'type': 'switch',
                'required': False,
                'default': True,
            },
        ],
        'expense_account_map': {
            'traffic': '6601',
            'meal': '6602',
            'hotel': '6603',
            'office': '6602',
            'telecom': '6602',
            'travel': '6601',
            'training': '6602',
            'other': '6602',
        },
    },
    {
        'id': 'payment_request',
        'name': '付款申请凭证',
        'description': '将付款申请单生成一借一贷凭证分录。',
        'definition_keys': ['std_payment'],
        'definition_names': ['付款申请', '付款申请单'],
        'mode': 'payment_single',
        'options': [
            {
                'key': 'org_code',
                'label': '会计主体编码',
                'type': 'text',
                'required': True,
                'default': '',
                'placeholder': '如：004',
            },
            {
                'key': 'accBook_code',
                'label': '账簿编码',
                'type': 'text',
                'required': True,
                'default': '',
                'placeholder': '如：004-01',
            },
            {
                'key': 'voucherType_voucherstr',
                'label': '凭证类型',
                'type': 'text',
                'required': True,
                'default': '记',
            },
            {
                'key': 'debit_accSubject_code',
                'label': '借方科目',
                'type': 'text',
                'required': True,
                'default': '122105',
                'placeholder': '如预付/成本类科目',
            },
            {
                'key': 'credit_accSubject_code',
                'label': '贷方科目',
                'type': 'text',
                'required': True,
                'default': '224102',
            },
            {
                'key': 'dept_aux_code',
                'label': '部门辅助核算编码',
                'type': 'text',
                'required': False,
                'default': '',
            },
            {
                'key': 'approved_only',
                'label': '仅导出已通过流程',
                'type': 'switch',
                'required': False,
                'default': True,
            },
        ],
    },
]


def list_finance_export_profiles() -> list[dict]:
    out = []
    for p in FINANCE_EXPORT_PROFILES:
        item = {
            'id': p['id'],
            'name': p['name'],
            'description': p.get('description', ''),
            'definition_keys': p.get('definition_keys') or [],
            'definition_names': p.get('definition_names') or [],
            'mode': p.get('mode'),
            'options': deepcopy(p.get('options') or []),
        }
        out.append(item)
    return out


def get_finance_export_profile(profile_id: str) -> dict | None:
    for p in FINANCE_EXPORT_PROFILES:
        if p['id'] == profile_id:
            return p
    return None


def instance_matches_profile(inst, profile: dict) -> bool:
    definition = inst.definition
    if not definition:
        return False
    def_ids = profile.get('definition_ids') or []
    if def_ids:
        return definition.id in def_ids
    keys = set(profile.get('definition_keys') or [])
    if definition.key in keys:
        return True
    names = profile.get('definition_names') or []
    def_name = (definition.name or '').strip()
    return any(def_name == n or n in def_name for n in names if n)
