import type { AttachmentFileItem } from '@/components/form/AttachmentField.vue'
import type { FormFieldDef, FormSchema } from '@/types/form'
import { createEmptyMoney } from '@/composables/useMoneyField'
import type { ReceiptFillSuggestions, SmartReceiptRecognitionConfig } from '@/constants/receiptExtractKeys'

function findFieldByKey(schema: FormSchema, key: string): FormFieldDef | null {
  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (field.key === key) return field
    }
  }
  return null
}

function findDetailField(schema: FormSchema, detailKey: string): FormFieldDef | null {
  const field = findFieldByKey(schema, detailKey)
  return field?.type === 'detail' ? field : null
}

function detailColumns(field: FormFieldDef): FormFieldDef[] {
  return ((field.props?.columns as FormFieldDef[]) || []).filter((c) => c.key)
}

function newDetailRow(field: FormFieldDef): Record<string, unknown> {
  const row: Record<string, unknown> = {}
  for (const col of detailColumns(field)) {
    if (col.type === 'money') {
      row[col.key] = col.defaultValue ?? createEmptyMoney()
    } else if (col.type === 'attachment' || col.type === 'image') {
      row[col.key] = col.defaultValue ?? []
    } else {
      row[col.key] = col.defaultValue ?? undefined
    }
  }
  return row
}

function mergeRow(
  base: Record<string, unknown>,
  patch: Record<string, unknown>,
): Record<string, unknown> {
  const out = { ...base }
  for (const [k, v] of Object.entries(patch)) {
    if (v !== undefined && v !== null && v !== '') {
      out[k] = v
    }
  }
  return out
}

/** 将识别结果填入当前明细行（不新增行） */
export function applyReceiptToDetailRow(
  row: Record<string, unknown>,
  suggestions: ReceiptFillSuggestions,
  attachColumnKey?: string,
): Record<string, unknown> {
  const patch = { ...(suggestions.detail_row || {}) }
  if (attachColumnKey && patch[attachColumnKey] !== undefined) {
    delete patch[attachColumnKey]
  }
  return mergeRow(row, patch)
}

function appendAttachment(
  target: unknown,
  file: AttachmentFileItem,
): AttachmentFileItem[] {
  const list = Array.isArray(target) ? [...(target as AttachmentFileItem[])] : []
  list.push(file)
  return list
}

/** 将识别建议写入表单 model */
export function applySmartReceiptFill(
  model: Record<string, unknown>,
  schema: FormSchema,
  config: SmartReceiptRecognitionConfig,
  suggestions: ReceiptFillSuggestions,
  attachment?: AttachmentFileItem,
): void {
  const fillMode = config.fillMode || 'detail_row'
  const mainPatch = suggestions.main || {}
  const detailPatch = suggestions.detail_row || {}

  if (fillMode === 'main_fields' || fillMode === 'both') {
    for (const [k, v] of Object.entries(mainPatch)) {
      if (v !== undefined && v !== null && v !== '') {
        model[k] = v
      }
    }
    if (attachment && config.attachToScope === 'main' && config.attachToFieldKey) {
      model[config.attachToFieldKey] = appendAttachment(model[config.attachToFieldKey], attachment)
    }
  }

  if (fillMode === 'detail_row' || fillMode === 'both') {
    const detailKey = config.targetDetailKey
    if (!detailKey) return
    const detailField = findDetailField(schema, detailKey)
    if (!detailField) return

    const rows = Array.isArray(model[detailKey])
      ? [...(model[detailKey] as Record<string, unknown>[])]
      : []

    let row = newDetailRow(detailField)
    row = mergeRow(row, detailPatch)

    if (attachment && config.attachToFieldKey && config.attachToScope !== 'main') {
      row[config.attachToFieldKey] = appendAttachment(row[config.attachToFieldKey], attachment)
    }

    rows.push(row)
    model[detailKey] = rows
  }
}

/** 从 schema 收集可映射的主表字段 */
export function listMainMappableFields(schema: FormSchema): FormFieldDef[] {
  const skip = new Set([
    'divider',
    'text_block',
    'section_title',
    'detail',
    'related_form',
    'smart_receipt',
  ])
  const out: FormFieldDef[] = []
  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (!field.key || skip.has(field.type)) continue
      out.push(field)
    }
  }
  return out
}

/** 明细表及其列 */
export function listDetailTargets(schema: FormSchema): {
  detailKey: string
  detailLabel: string
  columns: FormFieldDef[]
}[] {
  const out: {
    detailKey: string
    detailLabel: string
    columns: FormFieldDef[]
  }[] = []
  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (field.type !== 'detail' || !field.key) continue
      out.push({
        detailKey: field.key,
        detailLabel: field.label || field.key,
        columns: detailColumns(field),
      })
    }
  }
  return out
}

export function collectCategoryOptions(
  schema: FormSchema,
  categoryFieldKey: string,
  scope: 'main' | 'detail',
  detailKey?: string,
): { label: string; value: string; name?: string; code?: string }[] {
  if (!categoryFieldKey) return []
  if (scope === 'main') {
    const field = findFieldByKey(schema, categoryFieldKey)
    return extractOptionsFromField(field)
  }
  const detail = findDetailField(schema, detailKey || '')
  if (!detail) return []
  const col = detailColumns(detail).find((c) => c.key === categoryFieldKey)
  return extractOptionsFromField(col || null)
}

function extractOptionsFromField(field: FormFieldDef | null) {
  if (!field) return []
  const opts = (field.props?.options as { label?: string; name?: string; value?: string; code?: string }[]) || []
  return opts.map((o) => ({
    label: o.label || o.name || String(o.value || ''),
    value: String(o.value ?? o.code ?? ''),
    name: o.name,
    code: o.code,
  }))
}
