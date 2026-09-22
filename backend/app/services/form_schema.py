# -*- coding: utf-8 -*-
"""表单 schema 校验与字段类型注册（对齐钉钉/飞书/企业微信主流控件）。"""
import copy
import json
import re

FIELD_TYPES = {
    'input': '单行文本',
    'textarea': '多行文本',
    'number': '数字',
    'money': '金额',
    'plain_amount': '单金额',
    'date': '日期',
    'datetime': '日期时间',
    'time': '时间',
    'date_range': '日期区间',
    'select': '下拉单选',
    'multi_select': '下拉多选',
    'radio': '单选',
    'checkbox_group': '多选',
    'switch': '开关',
    'user_picker': '成员',
    'dept_picker': '部门',
    'contact': '联系人',
    'phone': '手机号',
    'email': '邮箱',
    'attachment': '附件',
    'image': '图片',
    'smart_receipt': '智能票据',
    'location': '地点',
    'serial_no': '流水号',
    'formula': '公式',
    'divider': '分割线',
    'text_block': '说明文字',
    'section_title': '分组标题',
    'leave_calendar': '日历',
    'detail': '明细',
    'related_form': '关联申请单',
    'record_set': '控件配置表',
}

_LAYOUT_ONLY = frozenset({'divider', 'text_block', 'section_title', 'leave_calendar'})
_NESTING_FORBIDDEN = frozenset({'detail', 'related_form', 'leave_calendar'})

DEFAULT_SCHEMA = {
    'version': 1,
    'title': '未命名表单',
    'description': '',
    'layout': {
        'labelPosition': 'top',
        'gridCols': 24,
        'gutter': 16,
    },
    'sections': [
        {
            'id': 'section_default',
            'title': '基本信息',
            'collapsed': False,
            'fields': [],
        },
    ],
    'print': {
        'enabled': True,
        'pageSize': 'A4',
        'orientation': 'portrait',
        'showTitle': True,
        'showDescription': True,
        'showInitiator': True,
        'showCompany': True,
        'showPrintTime': True,
        'showApprovalHistory': True,
        'marginMm': 12,
    },
}


def parse_schema(raw: str | None) -> dict:
    if not raw:
        return json.loads(json.dumps(DEFAULT_SCHEMA))
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else DEFAULT_SCHEMA.copy()
    except (json.JSONDecodeError, TypeError):
        return json.loads(json.dumps(DEFAULT_SCHEMA))


def _collect_field_keys(field: dict, keys: set, errors: list, prefix: str = '') -> None:
    ftype = field.get('type')
    if ftype not in FIELD_TYPES:
        errors.append(f'未知字段类型: {ftype}')
    key = field.get('key')
    label = field.get('label') or key or ftype
    if not key and ftype not in _LAYOUT_ONLY:
        errors.append(f'字段「{label}」缺少 key')
    if key:
        if key in keys:
            errors.append(f'字段 key 重复: {key}')
        keys.add(key)
    if ftype in ('select', 'multi_select', 'radio', 'checkbox_group'):
        props = field.get('props') or {}
        if props.get('optionSource') == 'option_set' and not (props.get('optionSetCode') or '').strip():
            errors.append(f'字段「{label}」未选择关联的选项配置表')
    if ftype == 'record_set':
        if not (field.get('props') or {}).get('recordSetCode', '').strip():
            errors.append(f'字段「{label}」未选择控件配置表')
    if ftype == 'detail':
        cols = (field.get('props') or {}).get('columns') or []
        if not cols:
            errors.append(f'明细「{label}」至少需要一列')
        for col in cols:
            ct = col.get('type')
            if ct in _NESTING_FORBIDDEN or ct in _LAYOUT_ONLY:
                errors.append(f'明细列不支持类型: {ct}')
            _collect_field_keys(col, keys, errors, prefix=f'{label}.')


def validate_schema(schema: dict) -> list[str]:
    errors = []
    if not schema.get('sections'):
        errors.append('至少需要一个表单分区')
    keys = set()
    for sec in schema.get('sections') or []:
        for field in sec.get('fields') or []:
            _collect_field_keys(field, keys, errors)
    return errors


def _validate_field_value(field: dict, val, data_label: str, errors: list, schema: dict | None = None) -> None:
    ftype = field.get('type')
    if ftype in ('attachment', 'image', 'smart_receipt'):
        if field.get('required'):
            items = val if isinstance(val, list) else []
            if not items:
                errors.append(f'{data_label} 为必填项')
        return
    if ftype == 'money' and isinstance(val, dict):
        if field.get('required'):
            amt = val.get('amount')
            if amt is None or amt == '':
                errors.append(f'{data_label} 为必填项')
        return
    if ftype == 'plain_amount':
        if field.get('required') and (val is None or val == ''):
            errors.append(f'{data_label} 为必填项')
        return
    if field.get('required') and (val is None or val == '' or val == []):
        errors.append(f'{data_label} 为必填项')
        return
    if ftype == 'date_range' and val not in (None, '', []):
        from app.services.date_range_value import build_date_range_value, parse_date_range

        parsed = parse_date_range(val)
        if field.get('required') and not parsed:
            errors.append(f'{data_label} 为必填项')
            return
        if parsed and build_date_range_value(field, val, schema) is None:
            errors.append(f'{data_label} 结束时间不能早于开始时间')
            return
    if val is None or val == '':
        return
    if ftype == 'email' and val:
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', str(val)):
            errors.append(f'{data_label} 邮箱格式不正确')
    if ftype == 'phone' and val:
        digits = re.sub(r'\D', '', str(val))
        if len(digits) < 8:
            errors.append(f'{data_label} 手机号格式不正确')
    if ftype == 'detail':
        rows = val if isinstance(val, list) else []
        cols = (field.get('props') or {}).get('columns') or []
        for ri, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f'{data_label} 第 {ri + 1} 行数据无效')
                continue
            for col in cols:
                ck = col.get('key')
                if not ck:
                    continue
                _validate_field_value(
                    col,
                    row.get(ck),
                    f'{data_label} 第 {ri + 1} 行·{col.get("label") or ck}',
                    errors,
                    schema,
                )
    if ftype == 'related_form':
        items = val if isinstance(val, list) else ([val] if isinstance(val, dict) else [])
        for item in items:
            if not isinstance(item, dict) or not item.get('instance_id'):
                errors.append(f'{data_label} 请选择有效的关联申请')
def validate_form_data(schema: dict, data: dict) -> list[str]:
    errors = []
    data = data or {}
    from app.services.form_visibility import field_is_visible, section_is_visible, _build_linkage_index

    index = _build_linkage_index(schema)
    for sec in schema.get('sections') or []:
        if not section_is_visible(sec, schema, data, index):
            continue
        for field in sec.get('fields') or []:
            ftype = field.get('type')
            if ftype in _LAYOUT_ONLY:
                continue
            key = field.get('key')
            if not key:
                continue
            if not field_is_visible(field, schema, data, index):
                continue
            _validate_field_value(field, data.get(key), field.get('label') or key, errors, schema)
    return errors


def flatten_fields(schema: dict) -> list[dict]:
    out = []
    for sec in schema.get('sections') or []:
        for field in sec.get('fields') or []:
            out.append(field)
    return out


def apply_form_description(schema: dict | None, description: str | None) -> dict:
    """将表单级说明写入 schema，保证发起页/打印与流程卡片展示一致。"""
    out = copy.deepcopy(schema) if schema else parse_schema(None)
    if description is not None:
        out['description'] = description
    return out


def resolve_definition_schema(definition) -> dict:
    """从流程定义解析表单 schema（优先关联的 FormDefinition）。"""
    if not definition:
        return parse_schema(None)
    form_def_id = getattr(definition, 'form_definition_id', None)
    if form_def_id:
        from app.models import FormDefinition

        form_def = FormDefinition.query.get(form_def_id)
        if form_def and form_def.schema_json:
            schema = parse_schema(form_def.schema_json)
            return apply_form_description(schema, form_def.description)
    raw = getattr(definition, 'form_schema', None)
    if raw and str(raw).strip().startswith('{'):
        return parse_schema(raw)
    return parse_schema(None)


def legacy_schema_to_full(legacy: list) -> dict:
    """兼容旧版 form_schema 数组。"""
    schema = parse_schema(None)
    fields = []
    for item in legacy or []:
        fields.append({
            'id': f'f_{item.get("key", "field")}',
            'key': item.get('key'),
            'type': item.get('type', 'input'),
            'label': item.get('label', item.get('key')),
            'required': bool(item.get('required')),
            'visible': True,
            'printable': True,
            'span': {'desktop': 24, 'mobile': 24},
            'props': item.get('options') and {'options': item.get('options')} or {},
        })
    schema['sections'][0]['fields'] = fields
    return schema


_RESUBMIT_SKIP_TYPES = frozenset({'serial_no', 'formula'})


def _strip_resubmit_field(data: dict, field: dict) -> None:
    key = field.get('key')
    if not key:
        return
    ftype = field.get('type')
    if ftype in _RESUBMIT_SKIP_TYPES:
        data.pop(key, None)
        return
    if ftype == 'detail':
        rows = data.get(key)
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            for col in (field.get('props') or {}).get('columns') or []:
                _strip_resubmit_field(row, col)


def clone_form_for_resubmit(schema: dict, form: dict | None) -> dict:
    """再次提交：复制原表单数据，流水号/公式等由系统重新生成。"""
    data = copy.deepcopy(form or {})
    for field in flatten_fields(schema):
        _strip_resubmit_field(data, field)
    return data


def prepare_form_for_submit(
    schema: dict,
    form: dict | None,
    *,
    form_definition_id: int | None,
    definition_id: int | None,
    company_id: int | None,
    user_id: int | None = None,
) -> dict:
    """正式提交：清除客户端流水号并按规则重新生成。"""
    from app.services.form_serial_no import apply_form_serial_numbers, strip_client_serial_values

    data = copy.deepcopy(form or {})
    strip_client_serial_values(schema, data)
    apply_form_serial_numbers(
        schema,
        data,
        form_definition_id=form_definition_id,
        definition_id=definition_id,
        company_id=company_id,
    )
    from app.services.date_range_value import apply_date_range_auto_days

    apply_date_range_auto_days(schema, data, company_id, user_id)
    return data
