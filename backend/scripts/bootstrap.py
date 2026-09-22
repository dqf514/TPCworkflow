# -*- coding: utf-8 -*-
import json
from datetime import datetime

from werkzeug.security import generate_password_hash

from app.extensions import db
from decimal import Decimal

from app.models import (
    BusinessSector,
    Company,
    Department,
    ExchangeRate,
    FlowRole,
    FlowRoleMember,
    I18nBundleMeta,
    I18nLocale,
    I18nMessage,
    User,
    UserOrgMembership,
    FormDefinition,
    WorkflowDefinition,
)
from app.models.settings import SystemSetting
from app.services.company_branding import SETTING_COMPANY_NAME, sync_company_name
from app.services.form_schema import DEFAULT_SCHEMA
from app.services.i18n import bump_bundle_version
from scripts.seed_i18n import seed_all_locales
from scripts.seed_i18n_zh_cn import SEED_MESSAGES


def ensure_bootstrap() -> None:
    """首次安装/升级时的基础数据；不覆盖用户已改词典，不反复创建综合部。"""
    _ensure_locales()
    _ensure_company_branding()
    _ensure_business_sectors()
    _ensure_exchange_rates()
    _ensure_admin()
    _ensure_admin_org_membership()
    _ensure_sample_org_and_workflow()
    _repair_form_workflow_publish_mismatch()
    _ensure_builtin_published_templates()
    _refresh_expense_reimbursement_template_schema()


def _repair_form_workflow_publish_mismatch() -> None:
    """表单标记已发布但关联流程未发布时，降级为草稿，与设计中心/发起列表一致。"""
    changed = False
    for f in FormDefinition.query.filter_by(status='published').all():
        wf = (
            WorkflowDefinition.query.get(f.workflow_definition_id)
            if f.workflow_definition_id
            else None
        )
        if wf and wf.status == 'published':
            continue
        f.status = 'draft'
        changed = True
    if changed:
        db.session.commit()


def _ensure_builtin_published_templates() -> None:
    """首次安装时：为所有内置模板创建已发布表单（已存在则仅补全发布状态，不覆盖 schema）。"""
    from app.services.form_templates.registry import BUILTIN_FORM_TEMPLATES, get_builtin_template

    admin = User.query.filter_by(username='admin').first()
    admin_id = admin.id if admin else None

    for key in BUILTIN_FORM_TEMPLATES:
        form_def = (
            FormDefinition.query.filter_by(key=key)
            .order_by(FormDefinition.version.desc())
            .first()
        )
        if form_def:
            # 用户已在设计中心删除（归档）的内置模板，不再自动恢复
            if form_def.status == 'archived':
                continue

            wf = None
            if form_def.workflow_definition_id:
                wf = WorkflowDefinition.query.get(form_def.workflow_definition_id)
            if wf and wf.status == 'archived':
                if form_def.status == 'published':
                    form_def.status = 'draft'
                    db.session.commit()
                continue

            changed = False
            if form_def.status != 'published':
                form_def.status = 'published'
                changed = True
            if not form_def.published_at:
                form_def.published_at = datetime.now()
                changed = True

            if wf and wf.status != 'published':
                wf.status = 'published'
                changed = True

            if not form_def.workflow_definition_id or not wf:
                payload = get_builtin_template(key, admin_user_id=admin_id)
                if payload:
                    if not wf:
                        wf = WorkflowDefinition.query.filter_by(
                            key=key,
                            version=form_def.version,
                        ).first()
                    if not wf and payload.get('workflow'):
                        wf_data = payload['workflow']
                        wf = WorkflowDefinition(
                            key=key,
                            name=form_def.name,
                            version=form_def.version,
                            status='published',
                            scope_type=wf_data.get('scope_type') or 'global',
                            form_definition_id=form_def.id,
                            form_schema=form_def.schema_json,
                            process_graph=json.dumps(
                                wf_data.get('process_graph') or {},
                                ensure_ascii=False,
                            ),
                            settings=json.dumps(
                                wf_data.get('settings') or {},
                                ensure_ascii=False,
                            ),
                            created_by=admin_id,
                        )
                        db.session.add(wf)
                        db.session.flush()
                    if wf:
                        wf.form_definition_id = form_def.id
                        if wf.status != 'published':
                            wf.status = 'published'
                        form_def.workflow_definition_id = wf.id
                        changed = True
            if changed:
                db.session.commit()
            continue

        payload = get_builtin_template(key, admin_user_id=admin_id)
        if not payload:
            continue
        _create_published_form_from_payload(payload, admin_id)


def _ensure_admin_org_membership() -> None:
    """仅当管理员尚无任何组织任职时，为其挂到主公司（不反复创建综合部）。"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        return
    if UserOrgMembership.query.filter_by(user_id=admin.id).first():
        return
    from app.services.company_branding import get_primary_company

    company = get_primary_company()
    dept = Department.query.filter_by(company_id=company.id, is_active=True).order_by(
        Department.sort_order,
        Department.id,
    ).first()
    if not dept:
        return
    db.session.add(
        UserOrgMembership(
            user_id=admin.id,
            company_id=company.id,
            department_id=dept.id,
            is_primary=True,
            role_in_dept='manager',
            job_title='管理员',
        ),
    )
    db.session.commit()


def _ensure_exchange_rates() -> None:
    """预置常用外币汇率（管理员可在系统设置中修改）。"""
    defaults = (
        ('USD', '美元', Decimal('7.200000'), 10),
        ('EUR', '欧元', Decimal('7.800000'), 20),
        ('HKD', '港币', Decimal('0.920000'), 30),
        ('JPY', '日元', Decimal('0.048000'), 40),
    )
    for code, name, rate, order in defaults:
        if not ExchangeRate.query.filter_by(currency_code=code).first():
            db.session.add(
                ExchangeRate(
                    currency_code=code,
                    currency_name=name,
                    rate_to_cny=rate,
                    sort_order=order,
                    is_active=True,
                )
            )
    db.session.commit()


def _ensure_business_sectors() -> None:
    defaults = (
        ('hr', '人事', 10),
        ('admin', '行政', 20),
        ('finance', '财务', 30),
        ('business', '业务', 40),
    )
    for code, name, order in defaults:
        if not BusinessSector.query.filter_by(code=code).first():
            db.session.add(BusinessSector(code=code, name=name, sort_order=order))
    db.session.commit()


def _ensure_company_branding() -> None:
    if not SystemSetting.query.get(SETTING_COMPANY_NAME):
        sync_company_name('合肥汽车检测认证技术中心')
        db.session.commit()


def _ensure_locales() -> None:
    if I18nLocale.query.count():
        return
    for code, name, native, default, order in (
        ('zh-CN', '简体中文', '简体中文', True, 0),
        ('en-US', 'English', 'English', False, 1),
    ):
        db.session.add(
            I18nLocale(
                code=code,
                name=name,
                native_name=native,
                is_default=default,
                is_enabled=True,
                sort_order=order,
            ),
        )
        db.session.add(I18nBundleMeta(locale=code, version=1))
    for namespace, msg_key, msg_value in SEED_MESSAGES:
        db.session.add(
            I18nMessage(
                namespace=namespace,
                msg_key=msg_key,
                locale='zh-CN',
                msg_value=msg_value,
            ),
        )
    db.session.commit()
    seed_all_locales()


def _ensure_admin() -> None:
    if User.query.filter_by(username='admin').first():
        return
    user = User(
        username='admin',
        display_name='系统管理员',
        email='admin@local',
        phone='13800000000',
        is_system_admin=True,
        locale='zh-CN',
    )
    user.password_hash = generate_password_hash('admin123')
    db.session.add(user)
    db.session.commit()


def _ensure_sample_org_and_workflow() -> None:
    admin = User.query.filter_by(username='admin').first()
    if FormDefinition.query.filter_by(key='demo_leave').first():
        return

    legacy_wf = WorkflowDefinition.query.filter_by(key='demo_leave').first()
    if legacy_wf:
        legacy_wf.key = 'demo_leave_legacy'
        legacy_wf.status = 'archived'
        db.session.flush()

    from app.services.company_branding import get_primary_company

    company = get_primary_company()
    if company.code == 'DEMO':
        company.code = 'SYSTEM'

    dept = Department.query.filter_by(company_id=company.id, name='综合部').first()
    if not dept:
        dept = Department(company_id=company.id, name='综合部', sort_order=0)
        db.session.add(dept)
        db.session.flush()

    if admin and not UserOrgMembership.query.filter_by(user_id=admin.id, company_id=company.id).first():
        db.session.add(
            UserOrgMembership(
                user_id=admin.id,
                company_id=company.id,
                department_id=dept.id,
                is_primary=True,
                role_in_dept='manager',
                job_title='管理员',
            ),
        )

    role = FlowRole.query.filter_by(code='dept_leader').first()
    if not role:
        role = FlowRole(code='dept_leader', name='部门负责人')
        db.session.add(role)
        db.session.flush()
    if admin and not FlowRoleMember.query.filter_by(flow_role_id=role.id, user_id=admin.id).first():
        db.session.add(
            FlowRoleMember(
                flow_role_id=role.id,
                user_id=admin.id,
                company_id=company.id,
            ),
        )

    span = {'desktop': 12, 'mobile': 24}
    leave_schema = json.loads(json.dumps(DEFAULT_SCHEMA))
    leave_schema['title'] = '请假申请'
    leave_schema['description'] = '示例：条件分支（天数>3 走部门负责人审批）'
    leave_schema['sections'][0]['title'] = '请假信息'
    leave_schema['sections'][0]['fields'] = [
        {
            'id': 'fld_title',
            'key': 'title',
            'type': 'input',
            'label': '请假事由',
            'required': True,
            'printable': True,
            'span': span,
        },
        {
            'id': 'fld_type',
            'key': 'leave_type',
            'type': 'select',
            'label': '请假类型',
            'required': True,
            'printable': True,
            'span': span,
            'props': {
                'options': [
                    {'label': '事假', 'value': 'personal'},
                    {'label': '病假', 'value': 'sick'},
                    {'label': '年假', 'value': 'annual'},
                ],
            },
        },
        {
            'id': 'fld_range',
            'key': 'date_range',
            'type': 'date_range',
            'label': '请假时间',
            'required': True,
            'printable': True,
            'span': {'desktop': 24, 'mobile': 24},
        },
        {
            'id': 'fld_days',
            'key': 'days',
            'type': 'number',
            'label': '请假天数',
            'required': True,
            'printable': True,
            'span': span,
        },
        {
            'id': 'fld_amount',
            'key': 'amount',
            'type': 'money',
            'label': '相关费用（元）',
            'required': False,
            'printable': True,
            'span': span,
        },
        {
            'id': 'fld_reason',
            'key': 'reason',
            'type': 'textarea',
            'label': '详细说明',
            'required': False,
            'printable': True,
            'span': {'desktop': 24, 'mobile': 24},
        },
    ]

    graph = {
        'nodes': [
            {'id': 'start', 'type': 'start'},
            {
                'id': 'cond1',
                'type': 'condition',
                'branches': [
                    {
                        'expr': {'field': 'form.days', 'op': 'gt', 'value': 3},
                        'target': 'approve_leader',
                    },
                    {'expr': 'default', 'target': 'approve_auto'},
                ],
            },
            {
                'id': 'approve_leader',
                'type': 'approver',
                'config': {
                    'assignee_type': 'flow_role',
                    'flow_role_code': 'dept_leader',
                    'apv_rel': 'and',
                },
            },
            {
                'id': 'approve_auto',
                'type': 'approver',
                'config': {
                    'assignee_type': 'fixed_users',
                    'user_ids': [admin.id] if admin else [],
                    'apv_rel': 'or',
                },
            },
            {'id': 'cc_hr', 'type': 'cc', 'config': {'assignee_type': 'fixed_users', 'user_ids': [admin.id] if admin else []}},
            {'id': 'end', 'type': 'end'},
        ],
        'edges': [
            {'source': 'start', 'target': 'cond1'},
            {'source': 'approve_leader', 'target': 'cc_hr'},
            {'source': 'approve_auto', 'target': 'cc_hr'},
            {'source': 'cc_hr', 'target': 'end'},
        ],
    }

    from app.services.workflow_settings import DEFAULT_WORKFLOW_SETTINGS

    settings = dict(DEFAULT_WORKFLOW_SETTINGS)
    settings['require_handwritten_sign'] = False

    form_def = FormDefinition(
        key='demo_leave',
        name='示例请假',
        version=1,
        status='published',
        description='内置演示：表单 + 流程一体化',
        schema_json=json.dumps(leave_schema, ensure_ascii=False),
        created_by=admin.id if admin else None,
    )
    db.session.add(form_def)
    db.session.flush()

    wf = WorkflowDefinition(
        key='demo_leave',
        name='示例请假',
        version=1,
        status='published',
        scope_type='global',
        form_definition_id=form_def.id,
        form_schema=json.dumps(leave_schema, ensure_ascii=False),
        process_graph=json.dumps(graph, ensure_ascii=False),
        settings=json.dumps(settings, ensure_ascii=False),
        created_by=admin.id if admin else None,
    )
    db.session.add(wf)
    db.session.flush()
    form_def.workflow_definition_id = wf.id
    db.session.commit()


def _create_published_form_from_payload(payload: dict, admin_id: int | None) -> None:
    """根据内置模板 payload 创建已发布的表单与流程（仅当 key 不存在时调用）。"""
    key = payload['key']
    name = payload['name']
    description = payload.get('description') or ''
    icon = payload.get('icon') or 'general'
    schema_json = json.dumps(payload['schema'], ensure_ascii=False)
    wf_data = payload.get('workflow') or {}
    graph_json = json.dumps(wf_data.get('process_graph') or {}, ensure_ascii=False)
    settings_json = json.dumps(wf_data.get('settings') or {}, ensure_ascii=False)

    form_def = FormDefinition(
        key=key,
        name=name,
        version=1,
        status='published',
        description=description,
        schema_json=schema_json,
        icon=icon,
        created_by=admin_id,
        published_at=datetime.now(),
    )
    db.session.add(form_def)
    db.session.flush()

    wf = WorkflowDefinition(
        key=key,
        name=name,
        version=1,
        status='published',
        scope_type=wf_data.get('scope_type') or 'global',
        form_definition_id=form_def.id,
        form_schema=schema_json,
        process_graph=graph_json,
        settings=settings_json,
        created_by=admin_id,
    )
    db.session.add(wf)
    db.session.flush()
    form_def.workflow_definition_id = wf.id
    db.session.commit()


def _refresh_expense_reimbursement_template_schema() -> None:
    """已发布的标准报销单：同步最新 schema（含明细内票据识别配置）。"""
    from app.services.form_templates.expense_reimbursement import (
        TEMPLATE_KEY,
        TEMPLATE_DESCRIPTION,
        build_expense_reimbursement_schema,
    )

    form_def = (
        FormDefinition.query.filter_by(key=TEMPLATE_KEY)
        .order_by(FormDefinition.version.desc())
        .first()
    )
    if not form_def:
        return
    schema = build_expense_reimbursement_schema()
    schema_json = json.dumps(schema, ensure_ascii=False)
    form_def.schema_json = schema_json
    form_def.description = TEMPLATE_DESCRIPTION
    if form_def.workflow_definition_id:
        wf = WorkflowDefinition.query.get(form_def.workflow_definition_id)
        if wf:
            wf.form_schema = schema_json
    db.session.commit()
