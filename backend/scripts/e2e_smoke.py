# -*- coding: utf-8 -*-
"""端到端冒烟：全控件表单 schema、校验、发布、发起、审批、完结。"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.extensions import db
from app.models import Company, Department, FormDefinition, User, WorkflowDefinition, WorkflowInstance
from app.services.company_branding import get_primary_company
from app.services.form_schema import FIELD_TYPES, validate_form_data, validate_schema
from scripts.bootstrap import ensure_bootstrap
from scripts.upgrade_db import _ensure_columns, _migrate_department_unique_constraint

E2E_FORM_KEY = f'e2e_all_fields_{int(time.time())}'

LAYOUT_ONLY = frozenset({'divider', 'text_block', 'section_title'})

OPTION_TYPES = frozenset({'select', 'multi_select', 'radio', 'checkbox_group'})

MANUAL_OPTS = [
    {'name': '选项一', 'code': '1', 'label': '选项一（1）', 'value': '1'},
    {'name': '选项二', 'code': '2', 'label': '选项二（2）', 'value': '2'},
]


def _field_def(ftype: str, idx: int) -> dict:
    key = '' if ftype in LAYOUT_ONLY else f'e2e_{ftype}_{idx}'
    label = FIELD_TYPES.get(ftype, ftype)
    field = {
        'id': f'e2e_{ftype}_{idx}',
        'key': key,
        'type': ftype,
        'label': label,
        'required': ftype in ('input', 'email', 'phone'),
        'visible': True,
        'printable': ftype not in ('divider',),
        'span': {'desktop': 12, 'mobile': 24},
        'props': {},
    }
    if ftype in OPTION_TYPES:
        field['props'] = {'optionSource': 'manual', 'options': MANUAL_OPTS}
    if ftype == 'money':
        field['props'] = {'precision': 2}
    if ftype == 'text_block':
        field['props'] = {'content': '这是一段说明文字，用于 E2E 测试连续输入不会失焦。'}
    if ftype == 'section_title':
        field['props'] = {'title': '分组小标题'}
    if ftype == 'detail':
        field['span'] = {'desktop': 24, 'mobile': 24}
        field['props'] = {
            'columns': [
                {
                    'id': 'e2e_detail_col_1',
                    'key': 'item_name',
                    'type': 'input',
                    'label': '项目',
                    'required': True,
                    'span': {'desktop': 12, 'mobile': 24},
                    'props': {},
                },
                {
                    'id': 'e2e_detail_col_2',
                    'key': 'amount',
                    'type': 'money',
                    'label': '金额',
                    'required': False,
                    'span': {'desktop': 12, 'mobile': 24},
                    'props': {'precision': 2},
                },
            ],
            'showSummary': True,
            'minRows': 0,
            'maxRows': 20,
        }
    if ftype == 'related_form':
        field['span'] = {'desktop': 24, 'mobile': 24}
        field['props'] = {'multiple': False, 'placeholder': '选择关联申请'}
        field['required'] = False
    return field


def build_e2e_schema() -> dict:
    fields = [_field_def(t, i) for i, t in enumerate(FIELD_TYPES)]
    return {
        'version': 1,
        'title': 'E2E 全控件测试',
        'description': '自动化冒烟测试表单',
        'layout': {'labelPosition': 'top', 'gridCols': 24, 'gutter': 16},
        'sections': [{'id': 'sec_e2e', 'title': '全控件', 'collapsed': False, 'fields': fields}],
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
        'settings': {'relatedFormKeys': []},
    }


def build_sample_form_data(admin_id: int, dept_id: int | None) -> dict:
    today = datetime.now().strftime('%Y-%m-%d')
    money = {
        'currency': 'CNY',
        'amount': 99.5,
        'exchange_rate': 1,
        'rmb_amount': 99.5,
    }
    samples: dict[str, object] = {
        'input': '单行文本样例',
        'textarea': '多行\n文本',
        'number': 12,
        'money': money,
        'phone': '13800138000',
        'email': 'e2e@example.com',
        'date': today,
        'datetime': f'{today} 10:00:00',
        'time': '10:30',
        'date_range': [today, today],
        'select': '1',
        'multi_select': ['1', '2'],
        'radio': '1',
        'checkbox_group': ['1'],
        'switch': True,
        'user_picker': admin_id,
        'dept_picker': dept_id,
        'contact': admin_id,
        'attachment': [],
        'image': [],
        'location': '合肥市',
        'detail': [{'item_name': '测试项', 'amount': money}],
        'serial_no': 'SN-E2E-001',
        'formula': '100',
    }
    data: dict = {}
    for i, ftype in enumerate(FIELD_TYPES):
        if ftype in LAYOUT_ONLY:
            continue
        key = f'e2e_{ftype}_{i}'
        val = samples.get(ftype)
        if val is not None:
            data[key] = val
    return data


def simple_workflow(admin_id: int) -> dict:
    return {
        'key': E2E_FORM_KEY,
        'name': 'E2E 全控件审批',
        'scope_type': 'global',
        'process_graph': {
            'nodes': [
                {'id': 'start', 'type': 'start'},
                {
                    'id': 'approve1',
                    'type': 'approver',
                    'config': {
                        'assignee_type': 'fixed_users',
                        'user_ids': [admin_id],
                        'apv_rel': 'or',
                    },
                },
                {'id': 'end', 'type': 'end'},
            ],
            'edges': [
                {'source': 'start', 'target': 'approve1'},
                {'source': 'approve1', 'target': 'end'},
            ],
        },
        'settings': {'require_handwritten_sign': False},
    }


def _login(client) -> None:
    with client.session_transaction() as sess:
        sess['login_captcha'] = {
            'id': 'e2e-captcha',
            'hash': generate_password_hash('e2e'),
            'exp': (datetime.now() + timedelta(minutes=10)).isoformat(),
        }
    r = client.post(
        '/api/v1/auth/login',
        json={
            'username': 'admin',
            'password': 'admin123',
            'captcha_id': 'e2e-captcha',
            'captcha_code': 'e2e',
        },
    )
    body = r.get_json()
    assert r.status_code == 200 and body.get('ok'), f'登录失败: {body}'


def _assert_ok(resp, step: str):
    body = resp.get_json()
    if resp.status_code != 200 or not body.get('ok'):
        raise AssertionError(f'{step} 失败 ({resp.status_code}): {body}')
    return body.get('data')


def run() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        _ensure_columns()
        _migrate_department_unique_constraint()
        ensure_bootstrap()

        client = app.test_client()
        _login(client)

        admin = User.query.filter_by(username='admin').first()
        company = get_primary_company()
        dept = Department.query.filter_by(company_id=company.id).first()
        assert admin and company, '缺少 admin 或公司'

        schema = build_e2e_schema()
        schema_errs = validate_schema(schema)
        if schema_errs:
            raise AssertionError(f'schema 校验失败: {schema_errs}')

        sample = build_sample_form_data(admin.id, dept.id if dept else None)
        data_errs = validate_form_data(schema, sample)
        if data_errs:
            raise AssertionError(f'样例数据校验失败: {data_errs}')

        payload = {
            'key': E2E_FORM_KEY,
            'name': 'E2E 全控件测试',
            'schema': schema,
            'workflow': simple_workflow(admin.id),
        }
        r = client.post('/api/v1/forms/definitions', json=payload)
        form = _assert_ok(r, '创建表单')
        form_id = form['id']
        wf_id = form.get('workflow_definition_id') or form.get('workflow', {}).get('id')

        r = client.post(f'/api/v1/forms/definitions/{form_id}/validate-data', json={'form': sample})
        _assert_ok(r, '校验填报数据')

        r = client.post(f'/api/v1/forms/definitions/{form_id}/publish', json={})
        _assert_ok(r, '发布表单与流程')

        if not wf_id:
            f = FormDefinition.query.get(form_id)
            wf_id = f.workflow_definition_id if f else None
        assert wf_id, '未关联流程'

        r = client.post(
            '/api/v1/workflow/instances',
            json={
                'definition_id': wf_id,
                'company_id': company.id,
                'department_id': dept.id if dept else None,
                'form': sample,
            },
        )
        inst = _assert_ok(r, '发起流程')
        instance_id = inst['id']

        r = client.get('/api/v1/workflow/tasks/todo')
        todo_page = _assert_ok(r, '待办列表')
        todos = todo_page.get('items') if isinstance(todo_page, dict) else todo_page
        pending = [t for t in todos if t.get('instance_id') == instance_id and t.get('task_status', t.get('status')) == 'pending']
        assert pending, f'未找到实例 {instance_id} 的待办'

        task_id = pending[0].get('task_id') or pending[0]['id']
        r = client.post(
            f'/api/v1/workflow/tasks/{task_id}/complete',
            json={'action': 'approve', 'comment': 'E2E 自动通过'},
        )
        _assert_ok(r, '审批通过')

        r = client.get(f'/api/v1/workflow/instances/{instance_id}')
        detail = _assert_ok(r, '流程详情')
        status = detail.get('status')
        assert status in ('approved', 'completed', 'finished'), f'流程未完结，状态={status}'

        print_config = (detail.get('form_schema') or {}).get('print') or {}
        assert print_config.get('enabled') is not False, '打印配置应启用'

        print(f'[OK] E2E 冒烟通过 form_key={E2E_FORM_KEY} instance_id={instance_id} status={status}')


if __name__ == '__main__':
    try:
        run()
    except Exception as exc:
        print(f'[FAIL] {exc}', file=sys.stderr)
        sys.exit(1)
