import type { FormFieldDef, FormSchema } from '@/types/form'
import {
  buildLinkageContext,
  shouldDisplayField,
  shouldDisplaySection,
} from '@/composables/useFieldLinkage'

export interface NodeFieldRuleConfig {
  field_permissions?: Record<string, 'hidden' | 'read' | 'edit'>
  field_node_required?: Record<string, boolean>
  field_must_modify?: Record<string, boolean>
}

function normValue(val: unknown): string {
  if (val === null || val === undefined) return ''
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val).trim()
}

function isEmptyValue(field: FormFieldDef, val: unknown): boolean {
  if (val === null || val === undefined || val === '') return true
  if (Array.isArray(val) && val.length === 0) return true
  if (field.type === 'money' && typeof val === 'object' && val !== null) {
    const o = val as { amount?: unknown; rmb_amount?: unknown }
    const amt = o.amount
    const rmb = o.rmb_amount
    return (amt === null || amt === undefined || amt === '') &&
      (rmb === null || rmb === undefined || rmb === '')
  }
  if (field.type === 'date_range') {
    if (Array.isArray(val)) return val.length < 2 || !val[0] || !val[1]
    if (typeof val === 'object' && val !== null) {
      const o = val as { start?: unknown; end?: unknown }
      return !o.start || !o.end
    }
    return true
  }
  if ((field.type === 'attachment' || field.type === 'image') && Array.isArray(val)) {
    return val.length === 0
  }
  return false
}

function findField(schema: FormSchema, key: string): FormFieldDef | undefined {
  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (field.key === key) return field
      if (field.type === 'detail') {
        for (const col of (field.props?.columns as FormFieldDef[]) || []) {
          if (col.key === key) return col
        }
      }
    }
  }
  return undefined
}

function findDetailParent(schema: FormSchema, colKey: string): { parent: FormFieldDef; col: FormFieldDef } | null {
  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (field.type !== 'detail') continue
      for (const col of (field.props?.columns as FormFieldDef[]) || []) {
        if (col.key === colKey) return { parent: field, col }
      }
    }
  }
  return null
}

export function validateNodeFieldRequirements(
  schema: FormSchema,
  formData: Record<string, unknown>,
  nodeConfig: NodeFieldRuleConfig | undefined,
  originalForm: Record<string, unknown>,
): string[] {
  if (!nodeConfig) return []
  const perms = nodeConfig.field_permissions || {}
  const requiredMap = nodeConfig.field_node_required || {}
  const mustModifyMap = nodeConfig.field_must_modify || {}
  const keys = new Set([...Object.keys(requiredMap), ...Object.keys(mustModifyMap)])
  if (!keys.size) return []

  const errors: string[] = []
  const linkageCtx = buildLinkageContext(schema)

  for (const key of keys) {
    if (perms[key] !== 'edit') continue
    const needRequired = !!requiredMap[key]
    const needModify = !!mustModifyMap[key]
    if (!needRequired && !needModify) continue

    const detailMeta = findDetailParent(schema, key)
    if (detailMeta) {
      const { parent, col } = detailMeta
      const sec = schema.sections?.find((s) => (s.fields || []).some((f) => f.key === parent.key))
      if (sec && !shouldDisplaySection(sec, schema, formData, linkageCtx)) {
        continue
      }
      if (!shouldDisplayField(parent, schema, formData, linkageCtx, { fieldPerm: perms[key] })) {
        continue
      }
      const parentKey = parent.key!
      const rows = formData[parentKey]
      const colLabel = col.label || key
      const detailLabel = parent.label || parentKey
      if (!Array.isArray(rows) || !rows.length) {
        if (needRequired) errors.push(`「${detailLabel}」至少填写一行，且「${colLabel}」为必填`)
        continue
      }
      rows.forEach((row, ri) => {
        if (!row || typeof row !== 'object') {
          if (needRequired) errors.push(`「${detailLabel}」第 ${ri + 1} 行·${colLabel} 为必填项`)
          return
        }
        const val = (row as Record<string, unknown>)[key]
        const origRows = originalForm[parentKey]
        let orig: unknown
        if (Array.isArray(origRows) && origRows[ri] && typeof origRows[ri] === 'object') {
          orig = (origRows[ri] as Record<string, unknown>)[key]
        }
        if (needRequired && isEmptyValue(col, val)) {
          errors.push(`「${detailLabel}」第 ${ri + 1} 行·${colLabel} 为必填项`)
        } else if (needModify && normValue(val) === normValue(orig)) {
          errors.push(`「${detailLabel}」第 ${ri + 1} 行·${colLabel} 须修改后方可同意`)
        }
      })
      continue
    }

    const field = findField(schema, key)
    if (!field) continue
    const sec = schema.sections?.find((s) => (s.fields || []).some((f) => f.key === key))
    if (sec && !shouldDisplaySection(sec, schema, formData, linkageCtx)) continue
    if (!shouldDisplayField(field, schema, formData, linkageCtx, { fieldPerm: perms[key] })) continue

    const label = field.label || key
    const val = formData[key]
    const orig = originalForm[key]
    if (needRequired && isEmptyValue(field, val)) {
      errors.push(`「${label}」为必填项，请在本节点填写`)
    } else if (needModify && normValue(val) === normValue(orig)) {
      errors.push(`「${label}」须修改后方可同意`)
    }
  }

  return errors
}

export function nodeHasFieldRequirements(nodeConfig?: NodeFieldRuleConfig): boolean {
  if (!nodeConfig) return false
  const perms = nodeConfig.field_permissions || {}
  const maps = [nodeConfig.field_node_required || {}, nodeConfig.field_must_modify || {}]
  return maps.some((m) => Object.entries(m).some(([k, v]) => v && perms[k] === 'edit'))
}
