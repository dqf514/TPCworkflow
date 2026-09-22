import { api, type ApiResponse } from '@/api/client'
import type {
  FormFieldHint,
  ReceiptRecognitionResult,
  SmartReceiptMapping,
  SmartReceiptRecognitionConfig,
} from '@/constants/receiptExtractKeys'
import type { FormFieldDef, FormSchema } from '@/types/form'
import { collectCategoryOptions, listDetailTargets, listMainMappableFields } from '@/composables/useSmartReceiptFill'

const SKIP_SMART_FILL_TYPES = new Set([
  'attachment',
  'image',
  'detail',
  'smart_receipt',
  'related_form',
  'divider',
  'text_block',
  'section_title',
  'record_set',
  'user_picker',
  'dept_picker',
])

function fieldOptions(field: FormFieldDef) {
  const opts =
    (field.props?.options as {
      label?: string
      name?: string
      value?: string
      code?: string
    }[]) || []
  return opts.slice(0, 50).map((o) => ({
    label: o.label || o.name || String(o.value || ''),
    value: String(o.value ?? o.code ?? ''),
    name: o.name,
    code: o.code,
  }))
}

function columnToHints(
  columns: FormFieldDef[],
  scope: 'main' | 'detail',
  excludeKey?: string,
): FormFieldHint[] {
  return columns
    .filter((c) => c.key && c.key !== excludeKey && !SKIP_SMART_FILL_TYPES.has(c.type))
    .map((c) => ({
      key: c.key!,
      label: String(c.label || c.key),
      type: c.type,
      scope,
      options: ['select', 'radio', 'multi_select'].includes(c.type) ? fieldOptions(c) : undefined,
    }))
}

/** 收集需智能填写的表单字段（含 label / type / 下拉选项） */
export function collectFormFieldHints(input: {
  schema?: FormSchema
  columns?: FormFieldDef[]
  attachColumnKey?: string
  fillMode?: string
  targetDetailKey?: string
}): FormFieldHint[] {
  const hints: FormFieldHint[] = []
  const fillMode = input.fillMode || 'detail_row'

  if (input.columns?.length) {
    hints.push(...columnToHints(input.columns, 'detail', input.attachColumnKey))
  }

  if (input.schema && fillMode !== 'detail_row') {
    hints.push(...columnToHints(listMainMappableFields(input.schema), 'main', input.attachColumnKey))
  }

  if (input.schema && fillMode !== 'main_fields' && input.targetDetailKey) {
    const detail = listDetailTargets(input.schema).find((d) => d.detailKey === input.targetDetailKey)
    if (detail) {
      hints.push(...columnToHints(detail.columns, 'detail', input.attachColumnKey))
    }
  }

  const seen = new Set<string>()
  return hints.filter((h) => {
    if (seen.has(h.key)) return false
    seen.add(h.key)
    return true
  })
}

export async function requestReceiptRecognition(input: {
  filePath: string
  scene?: string
  providerId?: number | null
  mappings?: SmartReceiptMapping[]
  schema?: FormSchema
  categoryFieldKey?: string
  detailKey?: string
  columns?: FormFieldDef[]
  attachColumnKey?: string
  fillMode?: string
  targetDetailKey?: string
  companyId?: number
  excludeInstanceRef?: string
}): Promise<ReceiptRecognitionResult> {
  const categoryOptions =
    input.schema && input.categoryFieldKey && input.detailKey
      ? collectCategoryOptions(input.schema, input.categoryFieldKey, 'detail', input.detailKey)
      : []

  const formFields = collectFormFieldHints({
    schema: input.schema,
    columns: input.columns,
    attachColumnKey: input.attachColumnKey,
    fillMode: input.fillMode,
    targetDetailKey: input.targetDetailKey || input.detailKey,
  })

  const res = await api.post<ApiResponse<ReceiptRecognitionResult>>('/ai/recognize-receipt', {
    file_path: input.filePath,
    scene: input.scene || 'expense',
    provider_id: input.providerId ?? null,
    mappings: input.mappings || [],
    category_options: categoryOptions,
    form_fields: formFields,
    company_id: input.companyId ?? null,
    exclude_instance_ref: input.excludeInstanceRef || null,
  })
  if (!res.data.ok) throw new Error(res.data.message || '识别失败')
  return res.data.data
}

export function getColumnRecognitionConfig(
  column: FormFieldDef,
): SmartReceiptRecognitionConfig | null {
  const rec = column.props?.recognition as SmartReceiptRecognitionConfig | undefined
  if (!rec || rec.enabled === false) return null
  return rec
}

export function buildDefaultDetailMappings(
  columns: FormFieldDef[],
  attachColumnKey: string,
): SmartReceiptMapping[] {
  const candidates = columns.filter((c) => c.key && c.key !== attachColumnKey)

  const findCol = (
    keys: string[],
    labelPatterns: RegExp[],
    typePrefer?: (type: string) => boolean,
  ) => {
    const byKey = candidates.find((c) => keys.includes(c.key!))
    if (byKey) return byKey
    const byLabel = candidates.filter((c) =>
      labelPatterns.some((p) => p.test(String(c.label || ''))),
    )
    if (typePrefer) {
      return byLabel.find((c) => typePrefer(c.type)) || byLabel[0]
    }
    return byLabel[0]
  }

  const mappings: SmartReceiptMapping[] = []

  const amountCol =
    candidates.find((c) => c.type === 'money') ||
    findCol(['amount', 'money', 'total_amount'], [/金额/, /合计/])
  if (amountCol?.key) {
    mappings.push({ extractKey: 'total_amount', targetKey: amountCol.key, targetScope: 'detail' })
  }

  const catCol = findCol(
    ['expense_type', 'category', 'cost_type', 'fee_type', 'expense_item', 'item_type', 'item_name'],
    [/费用/, /类别/, /项目/, /消费/, /科目/],
    (t) => t === 'select' || t === 'radio' || t === 'multi_select',
  )
  if (catCol?.key) {
    mappings.push({ extractKey: 'expense_category', targetKey: catCol.key, targetScope: 'detail' })
  }

  const dateCol =
    candidates.find((c) => c.type === 'date') ||
    findCol(['occur_date', 'transaction_date', 'date', 'biz_date'], [/日期/, /发生/])
  if (dateCol?.key) {
    mappings.push({ extractKey: 'transaction_date', targetKey: dateCol.key, targetScope: 'detail' })
  }

  const merchantCol = findCol(
    ['remark', 'merchant', 'vendor', 'supplier', 'company_merchant', 'merchant_name', 'company'],
    [/商户/, /公司/, /供应商/, /vendor/i, /备注/],
    (t) => t === 'input' || t === 'textarea',
  )
  if (merchantCol?.key) {
    mappings.push({ extractKey: 'merchant_name', targetKey: merchantCol.key, targetScope: 'detail' })
  }

  const voucherCol = findCol(
    ['voucher_no', 'invoice_no', 'ticket_no', 'document_number'],
    [/票号/, /订单/, /发票号/],
  )
  if (voucherCol?.key) {
    mappings.push({ extractKey: 'document_number', targetKey: voucherCol.key, targetScope: 'detail' })
  }

  return mappings
}

export function resolveDetailRecognitionConfig(
  column: FormFieldDef,
  columns: FormFieldDef[],
): SmartReceiptRecognitionConfig | null {
  const base = getColumnRecognitionConfig(column)
  if (!base || !column.key) return null
  const mappings =
    base.mappings && base.mappings.length > 0
      ? base.mappings
      : buildDefaultDetailMappings(columns, column.key)
  return {
    ...base,
    mappings,
    categoryFieldKey:
      base.categoryFieldKey ||
      mappings.find((m) => m.extractKey === 'expense_category')?.targetKey ||
      '',
  }
}
