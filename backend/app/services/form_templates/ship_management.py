# -*- coding: utf-8 -*-
"""船舶管理公司常见业务流程内置模板。"""
from __future__ import annotations

from app.services.form_templates._builder import (
    build_template_payload,
    f_attachment,
    f_date,
    f_date_range,
    f_dept,
    f_input,
    f_leave_calendar,
    f_money,
    f_number,
    f_select,
    f_textarea,
    f_user,
    opt,
    vessel_fields,
)

# ---------------------------------------------------------------------------
# 人事行政
# ---------------------------------------------------------------------------

def build_std_leave_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_leave',
        name='请假申请',
        description='内置模板：员工请假申请，含假别、时段与事由；适用于岸基与船员休假安排。',
        icon='leave',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '请假信息',
                'fields': [
                    f_select('leave_type', '请假类型', [
                        opt('年假', 'annual'),
                        opt('事假', 'personal'),
                        opt('病假', 'sick'),
                        opt('调休', 'comp_off'),
                        opt('婚假', 'marriage'),
                        opt('产假/陪产假', 'maternity'),
                        opt('其他', 'other'),
                    ], required=True),
                    f_date_range(
                        'leave_period',
                        '请假时段',
                        required=True,
                        sync_to_calendar=True,
                        half_day=True,
                        count_workdays=True,
                        auto_days_key='leave_days',
                    ),
                    f_number(
                        'leave_days',
                        '请假天数',
                        required=True,
                        readonly=True,
                        placeholder='根据请假时段自动计算',
                        step=0.5,
                        precision=1,
                    ),
                    f_dept('cost_department', '所属部门', required=True),
                    f_textarea('reason', '请假事由', required=True, placeholder='请说明请假原因及工作安排'),
                ],
            },
            {
                'title': '附件',
                'fields': [
                    f_attachment('attachments', '证明材料', required=False),
                ],
            },
            {
                'title': '团队日历',
                'fields': [
                    f_leave_calendar('日历', include_running=True),
                ],
            },
        ],
    )


def build_std_travel_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_travel',
        name='出差申请',
        description='内置模板：岸基人员或跟船出差申请，含目的地、行程、预算与出差事由。',
        icon='travel',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '出差信息',
                'fields': [
                    *vessel_fields(required=False),
                    f_input('destination', '出差目的地', required=True, placeholder='城市/港口/国家'),
                    f_date_range('travel_period', '出差时段', required=True, sync_to_calendar=True),
                    f_select('travel_mode', '出行方式', [
                        opt('飞机', 'flight'),
                        opt('高铁/火车', 'train'),
                        opt('汽车', 'car'),
                        opt('船舶', 'ship'),
                        opt('其他', 'other'),
                    ], required=True),
                    f_money('budget_amount', '预算金额', required=False),
                    f_dept('cost_department', '费用承担部门', required=True),
                    f_textarea('purpose', '出差事由', required=True),
                ],
            },
        ],
    )


def build_std_overtime_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_overtime',
        name='加班申请',
        description='内置模板：岸基或项目组加班申请，记录加班时段、事由与补偿方式。',
        icon='overtime',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '加班信息',
                'fields': [
                    f_date('overtime_date', '加班日期', required=True),
                    f_input('time_range', '加班时段', required=True, placeholder='如 18:00-21:00'),
                    f_number('overtime_hours', '加班小时数', required=True),
                    f_select('compensation', '补偿方式', [
                        opt('调休', 'comp_off'),
                        opt('加班费', 'pay'),
                        opt('项目备案', 'record'),
                    ], required=True),
                    f_dept('department', '所属部门', required=True),
                    f_textarea('reason', '加班事由', required=True),
                ],
            },
        ],
    )


def build_std_recruitment_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_recruitment',
        name='人员需求申请',
        description='内置模板：部门提出岸基或船员岗位招聘/增补需求，含岗位、人数与到岗时间。',
        icon='recruitment',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '岗位需求',
                'fields': [
                    f_dept('request_department', '需求部门', required=True),
                    f_input('position_title', '岗位名称', required=True, placeholder='如：海务主管、机务助理'),
                    f_select('position_type', '岗位类型', [
                        opt('岸基管理', 'shore'),
                        opt('船员/海员', 'crew'),
                        opt('派遣/外包', 'contractor'),
                    ], required=True),
                    f_number('headcount', '需求人数', required=True),
                    f_date('expected_onboard', '期望到岗日期', required=True),
                    f_select('urgency', '紧急程度', [
                        opt('普通', 'normal'),
                        opt('紧急', 'urgent'),
                    ], required=True),
                    f_textarea('job_requirements', '岗位要求', required=True),
                    f_textarea('remark', '补充说明', required=False),
                ],
            },
        ],
    )


def build_std_training_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_training',
        name='培训申请',
        description='内置模板：船员或岸基人员参加内外部培训、考证、演练的申请。',
        icon='training',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '培训信息',
                'fields': [
                    f_input('training_name', '培训名称', required=True),
                    f_select('training_type', '培训类型', [
                        opt('安全/应急演练', 'safety'),
                        opt('体系/合规', 'compliance'),
                        opt('专业技能', 'skill'),
                        opt('证书考试', 'certificate'),
                        opt('其他', 'other'),
                    ], required=True),
                    f_date_range('training_period', '培训时段', required=True),
                    f_money('estimated_cost', '预计费用', required=False),
                    f_user('trainees', '参训人员', required=False),
                    f_dept('department', '申请部门', required=True),
                    f_textarea('purpose', '培训目的与预期收益', required=True),
                ],
            },
        ],
    )


def build_std_asset_requisition_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_asset_requisition',
        name='物品领用申请',
        description='内置模板：办公用品、劳保用品等行政物资领用。',
        icon='asset',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '领用明细',
                'fields': [
                    f_dept('department', '领用部门', required=True),
                    f_input('item_name', '物品名称', required=True),
                    f_number('quantity', '数量', required=True),
                    f_input('spec', '规格型号', required=False),
                    f_date('needed_date', '需求日期', required=True),
                    f_textarea('purpose', '用途说明', required=True),
                ],
            },
        ],
    )


def build_std_seal_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_seal',
        name='用印申请',
        description='内置模板：公司公章、合同章、财务章等用印审批。',
        icon='seal',
        admin_user_id=admin_user_id,
        require_sign=False,
        sections=[
            {
                'title': '用印信息',
                'fields': [
                    f_select('seal_type', '印章类型', [
                        opt('公章', 'official'),
                        opt('合同章', 'contract'),
                        opt('财务章', 'finance'),
                        opt('法人章', 'legal'),
                    ], required=True),
                    f_input('document_name', '文件名称', required=True),
                    f_number('copies', '份数', required=True),
                    f_date('use_date', '用印日期', required=True),
                    f_dept('department', '申请部门', required=True),
                    f_textarea('purpose', '用印事由', required=True),
                    f_attachment('attachments', '待用印文件', required=False),
                ],
            },
        ],
    )


# ---------------------------------------------------------------------------
# 财务采购
# ---------------------------------------------------------------------------

def build_std_payment_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_payment',
        name='付款申请',
        description='内置模板：对供应商、代理、服务商等的付款申请，含收款信息与附件。',
        icon='payment',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '付款信息',
                'fields': [
                    *vessel_fields(required=False),
                    f_input('payee', '收款方名称', required=True),
                    f_money('payment_amount', '付款金额', required=True),
                    f_select('payment_type', '付款类型', [
                        opt('供应商货款', 'supplier'),
                        opt('港口/代理费', 'agent'),
                        opt('船员费用', 'crew'),
                        opt('修船费用', 'repair'),
                        opt('其他', 'other'),
                    ], required=True),
                    f_date('expected_pay_date', '期望付款日', required=True),
                    f_dept('cost_department', '费用承担部门', required=True),
                    f_textarea('reason', '付款事由', required=True),
                    f_input('bank_name', '开户行', required=False, full_width=True),
                    f_input('bank_account', '银行账号', required=False),
                    f_attachment('attachments', '合同/发票/账单', required=False),
                ],
            },
        ],
    )


def build_std_purchase_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_purchase',
        name='采购申请',
        description='内置模板：岸基物资或服务采购申请，含预算、供应商建议与用途说明。',
        icon='purchase',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '采购信息',
                'fields': [
                    f_dept('request_department', '申请部门', required=True),
                    f_input('item_summary', '采购内容摘要', required=True, full_width=True),
                    f_money('budget_amount', '预算金额', required=True),
                    f_input('suggested_supplier', '建议供应商', required=False),
                    f_date('needed_date', '需求日期', required=True),
                    f_select('purchase_category', '采购类别', [
                        opt('办公行政', 'admin'),
                        opt('IT/软件', 'it'),
                        opt('服务外包', 'service'),
                        opt('其他', 'other'),
                    ], required=True),
                    f_textarea('spec_requirement', '规格/服务要求', required=True),
                    f_textarea('justification', '采购理由', required=True),
                ],
            },
        ],
    )


def build_std_contract_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_contract',
        name='合同审批',
        description='内置模板：供应商、租家、代理、船员派遣等合同评审与审批。',
        icon='contract',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '合同信息',
                'fields': [
                    f_input('contract_title', '合同名称', required=True, full_width=True),
                    f_input('counterparty', '签约对方', required=True),
                    f_select('contract_type', '合同类型', [
                        opt('采购/供应', 'supply'),
                        opt('服务/代理', 'service'),
                        opt('租船/运输', 'charter'),
                        opt('船员派遣', 'crew'),
                        opt('其他', 'other'),
                    ], required=True),
                    f_money('contract_amount', '合同金额', required=False),
                    f_date_range('valid_period', '合同有效期', required=True),
                    f_dept('owner_department', '主办部门', required=True),
                    f_textarea('summary', '合同要点摘要', required=True),
                    f_attachment('contract_file', '合同文本', required=False),
                ],
            },
        ],
    )


# ---------------------------------------------------------------------------
# 船舶营运
# ---------------------------------------------------------------------------

def build_std_spare_parts_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_spare_parts',
        name='船舶备件申领',
        description='内置模板：在船或岸基申请备件、物料，含设备信息、规格与紧急程度。',
        icon='inventory',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '备件信息',
                'fields': [
                    *vessel_fields(required=True),
                    f_input('equipment_name', '设备名称', required=True, placeholder='如：主空压机、舵机'),
                    f_input('part_name', '备件/物料名称', required=True),
                    f_input('part_no', '备件号/图号', required=False),
                    f_number('quantity', '数量', required=True),
                    f_input('unit', '单位', required=True, placeholder='件/套/升'),
                    f_select('urgency', '紧急程度', [
                        opt('常规', 'normal'),
                        opt('紧急', 'urgent'),
                        opt('坞修计划', 'drydock'),
                    ], required=True),
                    f_date('needed_date', '需求供船日期', required=True),
                    f_textarea('remark', '用途及备注', required=True),
                ],
            },
        ],
    )


def build_std_crew_dispatch_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_crew_dispatch',
        name='船员调配申请',
        description='内置模板：船员上船、下船、换班或临时调配申请。',
        icon='ship',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '调配信息',
                'fields': [
                    *vessel_fields(required=True),
                    f_select('dispatch_type', '调配类型', [
                        opt('上船', 'sign_on'),
                        opt('下船', 'sign_off'),
                        opt('换班', 'change'),
                        opt('临时调配', 'temp'),
                    ], required=True),
                    f_input('crew_name', '船员姓名', required=True),
                    f_input('rank', '职务/级别', required=True, placeholder='如：船长、大副、轮机长'),
                    f_date('effective_date', '生效/上船日期', required=True),
                    f_input('port', '港口/地点', required=False, placeholder='换班港口或登船地点'),
                    f_dept('request_department', '申请部门', required=True),
                    f_textarea('reason', '调配原因及说明', required=True),
                ],
            },
        ],
    )


def build_std_drydock_repair_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_drydock_repair',
        name='修船/坞修申请',
        description='内置模板：计划修船、坞修、航修或紧急修理的项目与预算申请。',
        icon='maintenance',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '修理信息',
                'fields': [
                    *vessel_fields(required=True),
                    f_select('repair_type', '修理类型', [
                        opt('坞修', 'drydock'),
                        opt('航修', 'voyage'),
                        opt('临时修理', 'emergency'),
                        opt('检验配合', 'survey'),
                    ], required=True),
                    f_input('repair_yard', '修理厂/服务商', required=False),
                    f_date_range('repair_period', '计划修理时段', required=True),
                    f_money('estimated_cost', '预估费用', required=True),
                    f_textarea('repair_scope', '修理范围与项目', required=True),
                    f_textarea('remark', '备注', required=False),
                    f_attachment('attachments', '报价/修理清单', required=False),
                ],
            },
        ],
    )


def build_std_bunker_supply_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_bunker_supply',
        name='燃油补给申请',
        description='内置模板：船舶燃油（重油/轻油/LSMGO等）补给计划与审批。',
        icon='logistics',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '补给信息',
                'fields': [
                    *vessel_fields(required=True),
                    f_input('supply_port', '补给港口', required=True),
                    f_date('supply_date', '计划补给日期', required=True),
                    f_select('fuel_type', '油种', [
                        opt('重油 HSFO', 'hsfo'),
                        opt('低硫重油 VLSFO', 'vlsfo'),
                        opt('轻柴油 MDO', 'mdo'),
                        opt('低硫轻油 LSMGO', 'lsmgo'),
                    ], required=True),
                    f_number('quantity', '补给数量(吨)', required=True),
                    f_input('supplier', '供应商/供油商', required=False),
                    f_money('estimated_amount', '预估金额', required=False),
                    f_textarea('remark', '备注', required=False),
                ],
            },
        ],
    )


def build_std_port_fee_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_port_fee',
        name='港口使费申请',
        description='内置模板：港口使费、代理费、引航费、拖轮费等申请与预付审批。',
        icon='finance',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '使费信息',
                'fields': [
                    *vessel_fields(required=True),
                    f_input('port_name', '港口', required=True),
                    f_input('agent_name', '代理公司', required=False),
                    f_select('fee_type', '费用类型', [
                        opt('港口使费', 'port_dues'),
                        opt('代理费', 'agency'),
                        opt('引航/拖轮', 'pilot_tug'),
                        opt('装卸/绑扎', 'cargo'),
                        opt('其他', 'other'),
                    ], required=True),
                    f_money('amount', '金额', required=True),
                    f_date('due_date', '付款/发生日期', required=True),
                    f_textarea('description', '费用说明', required=True),
                    f_attachment('attachments', '账单/报价', required=False),
                ],
            },
        ],
    )


def build_std_incident_report_template(admin_user_id: int | None = None) -> dict:
    return build_template_payload(
        key='std_incident_report',
        name='事件/不符合报告',
        description='内置模板：安全事故、险情、不符合、险情或体系事件报告（SMS/ISM）。',
        icon='safety',
        admin_user_id=admin_user_id,
        sections=[
            {
                'title': '事件信息',
                'fields': [
                    *vessel_fields(required=False),
                    f_select('incident_type', '事件类型', [
                        opt('安全事故', 'accident'),
                        opt('险情/Near Miss', 'near_miss'),
                        opt('不符合', 'nonconformity'),
                        opt('污染/溢油', 'pollution'),
                        opt('其他', 'other'),
                    ], required=True),
                    f_date('incident_date', '发生日期', required=True),
                    f_input('location', '发生地点', required=True, placeholder='港口/海域/岸基场所'),
                    f_select('severity', '严重程度', [
                        opt('一般', 'minor'),
                        opt('较大', 'major'),
                        opt('重大', 'critical'),
                    ], required=True),
                    f_textarea('description', '事件经过', required=True),
                    f_textarea('immediate_action', '已采取的措施', required=True),
                    f_attachment('attachments', '照片/证据', required=False),
                ],
            },
        ],
    )


# 供注册表使用的元数据与构建函数
SHIP_MANAGEMENT_TEMPLATES: list[dict] = [
    {
        'key': 'std_leave',
        'name': '请假申请',
        'description': '内置模板：员工请假申请，含假别、时段与事由；适用于岸基与船员休假安排。',
        'icon': 'leave',
        'build': build_std_leave_template,
    },
    {
        'key': 'std_travel',
        'name': '出差申请',
        'description': '内置模板：岸基人员或跟船出差申请，含目的地、行程、预算与出差事由。',
        'icon': 'travel',
        'build': build_std_travel_template,
    },
    {
        'key': 'std_overtime',
        'name': '加班申请',
        'description': '内置模板：岸基或项目组加班申请，记录加班时段、事由与补偿方式。',
        'icon': 'overtime',
        'build': build_std_overtime_template,
    },
    {
        'key': 'std_recruitment',
        'name': '人员需求申请',
        'description': '内置模板：部门提出岸基或船员岗位招聘/增补需求，含岗位、人数与到岗时间。',
        'icon': 'recruitment',
        'build': build_std_recruitment_template,
    },
    {
        'key': 'std_training',
        'name': '培训申请',
        'description': '内置模板：船员或岸基人员参加内外部培训、考证、演练的申请。',
        'icon': 'training',
        'build': build_std_training_template,
    },
    {
        'key': 'std_asset_requisition',
        'name': '物品领用申请',
        'description': '内置模板：办公用品、劳保用品等行政物资领用。',
        'icon': 'asset',
        'build': build_std_asset_requisition_template,
    },
    {
        'key': 'std_seal',
        'name': '用印申请',
        'description': '内置模板：公司公章、合同章、财务章等用印审批。',
        'icon': 'seal',
        'build': build_std_seal_template,
    },
    {
        'key': 'std_payment',
        'name': '付款申请',
        'description': '内置模板：对供应商、代理、服务商等的付款申请，含收款信息与附件。',
        'icon': 'payment',
        'build': build_std_payment_template,
    },
    {
        'key': 'std_purchase',
        'name': '采购申请',
        'description': '内置模板：岸基物资或服务采购申请，含预算、供应商建议与用途说明。',
        'icon': 'purchase',
        'build': build_std_purchase_template,
    },
    {
        'key': 'std_contract',
        'name': '合同审批',
        'description': '内置模板：供应商、租家、代理、船员派遣等合同评审与审批。',
        'icon': 'contract',
        'build': build_std_contract_template,
    },
    {
        'key': 'std_spare_parts',
        'name': '船舶备件申领',
        'description': '内置模板：在船或岸基申请备件、物料，含设备信息、规格与紧急程度。',
        'icon': 'inventory',
        'build': build_std_spare_parts_template,
    },
    {
        'key': 'std_crew_dispatch',
        'name': '船员调配申请',
        'description': '内置模板：船员上船、下船、换班或临时调配申请。',
        'icon': 'ship',
        'build': build_std_crew_dispatch_template,
    },
    {
        'key': 'std_drydock_repair',
        'name': '修船/坞修申请',
        'description': '内置模板：计划修船、坞修、航修或紧急修理的项目与预算申请。',
        'icon': 'maintenance',
        'build': build_std_drydock_repair_template,
    },
    {
        'key': 'std_bunker_supply',
        'name': '燃油补给申请',
        'description': '内置模板：船舶燃油补给计划与审批。',
        'icon': 'logistics',
        'build': build_std_bunker_supply_template,
    },
    {
        'key': 'std_port_fee',
        'name': '港口使费申请',
        'description': '内置模板：港口使费、代理费、引航费等申请与预付审批。',
        'icon': 'finance',
        'build': build_std_port_fee_template,
    },
    {
        'key': 'std_incident_report',
        'name': '事件/不符合报告',
        'description': '内置模板：安全事故、险情、不符合或体系事件报告（SMS/ISM）。',
        'icon': 'safety',
        'build': build_std_incident_report_template,
    },
]
