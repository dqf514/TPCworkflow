import { createEmptyMoney } from '@/composables/useMoneyField'

export type DeviceMode = 'desktop' | 'mobile'

export interface FieldSpan {
  desktop: number
  mobile: number
  /** 旧数据兼容，读写时等同 mobile */
  tablet?: number
}

export interface FormFieldDef {
  id: string
  key: string
  type: string
  label: string
  required?: boolean
  visible?: boolean
  printable?: boolean
  readonly?: boolean
  placeholder?: string
  description?: string
  span?: FieldSpan
  props?: Record<string, unknown>
  defaultValue?: unknown
  /** 按其他控件选项显示；与 props.linkage 可并存，需同时满足 */
  showWhen?: FieldShowWhenRule | FieldShowWhenRule[]
  showWhenLogic?: 'and' | 'or'
}

export interface FieldShowWhenRule {
  fieldKey: string
  values: string[]
  match?: 'any' | 'all'
}

export interface FieldLinkageRule {
  optionValue: string
  showFieldIds: string[]
  showSectionIds?: string[]
}

export interface FieldLinkageConfig {
  rules: FieldLinkageRule[]
}

export interface FormSection {
  id: string
  title: string
  collapsed?: boolean
  fields: FormFieldDef[]
  showWhen?: FieldShowWhenRule | FieldShowWhenRule[]
  showWhenLogic?: 'and' | 'or'
}

export interface FormPrintConfig {
  enabled?: boolean
  templateMode?: 'default' | 'custom'
  templateCode?: string
  templateOverrides?: Record<string, unknown>
  pageSize?: 'A4' | 'A3'
  orientation?: 'portrait' | 'landscape'
  showTitle?: boolean
  showDescription?: boolean
  showInitiator?: boolean
  showCompany?: boolean
  showPrintTime?: boolean
  showApprovalHistory?: boolean
  marginMm?: number
}

/** 明细表内的列定义（不可嵌套明细/关联表单） */
export type DetailColumnType = Exclude<
  FormFieldDef['type'],
  'detail' | 'related_form' | 'divider' | 'text_block' | 'section_title' | 'leave_calendar'
>

export interface FormSchemaSettings {
  /** 本表单允许关联的其他申请表单 key（多选） */
  relatedFormKeys?: string[]
}

export interface FormSchema {
  version: number
  title: string
  description?: string
  layout: {
    labelPosition: 'top' | 'left'
    gridCols: number
    gutter: number
  }
  sections: FormSection[]
  print: FormPrintConfig
  settings?: FormSchemaSettings
}

export const DEFAULT_FORM_SCHEMA = (): FormSchema => ({
  version: 1,
  title: '未命名表单',
  description: '',
  layout: { labelPosition: 'top', gridCols: 24, gutter: 16 },
  sections: [{ id: 'section_1', title: '基本信息', collapsed: false, fields: [] }],
  print: {
    enabled: true,
    pageSize: 'A4',
    orientation: 'portrait',
    showTitle: true,
    showDescription: false,
    showInitiator: true,
    showCompany: true,
    showPrintTime: true,
    showApprovalHistory: true,
    marginMm: 12,
  },
  settings: { relatedFormKeys: [] },
})

export const FIELD_CATALOG: { group: string; items: { type: string; label: string; icon?: string }[] }[] = [
  {
    group: '基础',
    items: [
      { type: 'input', label: '单行文本' },
      { type: 'textarea', label: '多行文本' },
      { type: 'number', label: '数字' },
      { type: 'money', label: '金额' },
      { type: 'plain_amount', label: '单金额' },
      { type: 'phone', label: '手机号' },
      { type: 'email', label: '邮箱' },
    ],
  },
  {
    group: '日期时间',
    items: [
      { type: 'date', label: '日期' },
      { type: 'datetime', label: '日期时间' },
      { type: 'time', label: '时间' },
      { type: 'date_range', label: '日期区间' },
      { type: 'leave_calendar', label: '日历' },
    ],
  },
  {
    group: '选择',
    items: [
      { type: 'select', label: '下拉单选' },
      { type: 'multi_select', label: '下拉多选' },
      { type: 'radio', label: '单选' },
      { type: 'checkbox_group', label: '多选' },
      { type: 'switch', label: '开关' },
      { type: 'record_set', label: '控件配置表' },
    ],
  },
  {
    group: '组织与附件',
    items: [
      { type: 'user_picker', label: '成员' },
      { type: 'dept_picker', label: '部门' },
      { type: 'contact', label: '联系人' },
      { type: 'attachment', label: '附件' },
      { type: 'image', label: '图片' },
      { type: 'smart_receipt', label: '智能票据' },
      { type: 'location', label: '地点' },
    ],
  },
  {
    group: '高级',
    items: [
      { type: 'detail', label: '明细' },
      { type: 'related_form', label: '关联申请单' },
      { type: 'serial_no', label: '流水号' },
      { type: 'formula', label: '公式' },
    ],
  },
  {
    group: '布局',
    items: [
      { type: 'section_title', label: '小标题' },
      { type: 'text_block', label: '说明文字' },
      { type: 'divider', label: '分割线' },
    ],
  },
]

export function newField(type: string): FormFieldDef {
  const id = `f_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
  const key = `field_${id.slice(-6)}`
  const base: FormFieldDef = {
    id,
    key,
    type,
    label: FIELD_CATALOG.flatMap((g) => g.items).find((i) => i.type === type)?.label || type,
    required: false,
    visible: true,
    printable: type !== 'divider',
    readonly: false,
    span: { desktop: 12, mobile: 24 },
    props: {},
  }
  if (['select', 'multi_select', 'radio', 'checkbox_group'].includes(type)) {
    base.props = {
      optionSource: 'manual',
      options: [
        { name: '选项一', code: '1', label: '选项一（1）', value: '1' },
        { name: '选项二', code: '2', label: '选项二（2）', value: '2' },
      ],
    }
  }
  if (type === 'money') {
    base.props = { precision: 2 }
    base.defaultValue = createEmptyMoney()
  }
  if (type === 'plain_amount') {
    base.props = { precision: 2 }
    base.defaultValue = null
  }
  if (type === 'formula') {
    base.readonly = true
    base.props = { expression: '', precision: 2 }
    base.placeholder = '自动计算'
  }
  if (type === 'serial_no') {
    base.readonly = true
    base.placeholder = '提交后自动生成'
    base.props = {
      serial: {
        prefix: '',
        suffix: '',
        seqDigits: 4,
        datePart: 'YYYYMMDD',
        separator: '-',
        resetCycle: 'day',
        scope: 'company',
        pattern: '',
      },
    }
  }
  if (type === 'text_block') {
    base.props = { content: '请在此填写说明' }
    base.key = ''
  }
  if (type === 'divider' || type === 'section_title') base.key = ''
  if (type === 'leave_calendar') {
    base.key = ''
    base.label = '日历'
    base.printable = false
    base.readonly = true
    base.span = { desktop: 24, mobile: 24 }
    base.props = {
      formKeys: ['auto'],
      periodFieldKeys: ['leave_period', 'date_range'],
      leaveTypeFieldKey: 'leave_type',
      includeRunning: false,
      showReason: false,
      height: 520,
    }
  }
  if (type === 'detail') {
    const col1 = newField('input')
    col1.key = 'item_name'
    col1.label = '费用项目'
    col1.span = { desktop: 12, mobile: 24 }
    const col2 = newField('money')
    col2.key = 'amount'
    col2.label = '金额'
    col2.span = { desktop: 12, mobile: 24 }
    base.props = {
      columns: [col1, col2],
      showSummary: true,
      minRows: 0,
      maxRows: 50,
    }
    base.span = { desktop: 24, mobile: 24 }
  }
  if (type === 'related_form') {
    base.props = { multiple: false, placeholder: '选择已提交的关联申请' }
    base.span = { desktop: 24, mobile: 24 }
  }
  if (type === 'user_picker') {
    base.props = { multiple: false, defaultSelf: false }
  }
  if (type === 'dept_picker') {
    base.props = { multiple: false, defaultPrimaryDept: false }
  }
  if (type === 'email') {
    base.placeholder = '请输入有效邮箱地址'
  }
  if (type === 'record_set') {
    base.props = {
      recordSetCode: '',
      labelField: '',
      showCompanyRecords: true,
      showPersonalRecords: true,
    }
    base.span = { desktop: 24, mobile: 24 }
  }
  if (type === 'smart_receipt') {
    base.props = {
      accept: 'image/jpeg,image/png,image/webp,image/gif,.pdf',
      maxCount: 20,
      recognition: {
        enabled: true,
        scene: 'expense',
        providerId: null,
        fillMode: 'detail_row',
        targetDetailKey: '',
        mappings: [
          { extractKey: 'total_amount', targetKey: '', targetScope: 'detail' },
          { extractKey: 'expense_category', targetKey: '', targetScope: 'detail' },
          { extractKey: 'transaction_date', targetKey: '', targetScope: 'detail' },
          { extractKey: 'merchant_name', targetKey: '', targetScope: 'detail' },
        ],
        categoryFieldKey: '',
        autoFill: true,
        attachToFieldKey: '',
        attachToScope: 'detail',
      },
    }
    base.span = { desktop: 24, mobile: 24 }
    base.description = '上传票据、收据、发票等，自动识别金额与类别并填入表单'
  }
  return base
}

/** 明细内可添加的控件（排除布局与嵌套类型） */
export const DETAIL_FIELD_CATALOG = FIELD_CATALOG.map((g) => ({
  group: g.group,
  items: g.items.filter(
    (i) => !['detail', 'related_form', 'divider', 'text_block', 'section_title'].includes(i.type),
  ),
})).filter((g) => g.items.length > 0)

export function isDetailRowArray(val: unknown): val is Record<string, unknown>[] {
  return Array.isArray(val)
}

export interface RelatedFormValue {
  instance_id: number
  public_uuid?: string
  title: string
  form_key?: string
  status?: string
  current_node_label?: string | null
  started_at?: string
}

/** 桌面端始终占满一行的字段类型 */
const DESKTOP_FULL_WIDTH_FIELD_TYPES = new Set([
  'textarea',
  'detail',
  'related_form',
  'attachment',
  'image',
  'smart_receipt',
  'record_set',
  'divider',
  'text_block',
  'section_title',
])

export function getSpan(field: FormFieldDef, device: DeviceMode): number {
  const span = field.span
  if (device === 'mobile') {
    if (!span) return 24
    return span.mobile ?? span.tablet ?? 24
  }
  if (DESKTOP_FULL_WIDTH_FIELD_TYPES.has(field.type)) {
    return span?.desktop ?? 24
  }
  const desktop = span?.desktop ?? 12
  /* 短字段桌面默认两列，即使用户模板设为 24 也半宽以提升密度 */
  return desktop >= 24 ? 12 : desktop
}

/** 打印时是否占满整行（标签一列 + 内容占剩余三列） */
export function isPrintFullWidthField(field: FormFieldDef, gridCols = 24): boolean {
  const desktop = field.span?.desktop
  if (desktop != null) return desktop >= gridCols
  return DESKTOP_FULL_WIDTH_FIELD_TYPES.has(field.type)
}
