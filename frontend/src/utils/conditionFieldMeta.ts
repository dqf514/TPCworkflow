import type { FormFieldDef, FormSchema } from '@/types/form'
import type { FormFieldTreeRow } from '@/utils/formFieldTree'

const NUMERIC_FIELD_TYPES = new Set(['money', 'plain_amount', 'number', 'integer', 'formula'])

export const SWITCH_CONDITION_OPTS = [
  { label: '开启', value: 'true' },
  { label: '关闭', value: 'false' },
] as const

export function fieldKeyFromConditionPath(fieldPath: string): string {
  return fieldPath.startsWith('form.') ? fieldPath.slice(5) : fieldPath
}

export function findFormFieldDef(schema: FormSchema | undefined, key: string): FormFieldDef | undefined {
  if (!schema?.sections?.length || !key) return undefined
  for (const sec of schema.sections) {
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

export function fieldTypeForConditionPath(
  fieldPath: string,
  permRows: FormFieldTreeRow[],
): string | undefined {
  const key = fieldKeyFromConditionPath(fieldPath)
  return permRows.find((r) => r.key === key)?.type
}

export function defaultOpForFieldType(type?: string): string {
  if (!type || type === 'switch' || type === 'select' || type === 'radio') return 'eq'
  if (NUMERIC_FIELD_TYPES.has(type)) return 'gte'
  return 'eq'
}

export function opsForFieldType(type?: string): string[] {
  if (type === 'switch') return ['eq', 'ne']
  if (type === 'select' || type === 'radio') return ['eq', 'ne']
  if (NUMERIC_FIELD_TYPES.has(type || '')) return ['eq', 'ne', 'gt', 'gte', 'lt', 'lte']
  return ['eq', 'ne', 'gt', 'gte', 'lt', 'lte']
}

export function isNumericConditionField(type?: string): boolean {
  return NUMERIC_FIELD_TYPES.has(type || '')
}

export function formatConditionValueLabel(type: string | undefined, value: unknown): string {
  if (type === 'switch') {
    const on =
      value === true || value === 'true' || value === 1 || value === '1'
    return on ? '开启' : '关闭'
  }
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

export function parseConditionEditorValue(type: string | undefined, value: unknown): string {
  if (type === 'switch') {
    const on = value === true || value === 'true' || value === 1 || value === '1'
    return on ? 'true' : 'false'
  }
  if (value === null || value === undefined) return ''
  return String(value)
}

export function coerceConditionStoredValue(type: string | undefined, raw: string | unknown): unknown {
  if (type === 'switch') {
    return raw === true || raw === 'true' || raw === 1 || raw === '1'
  }
  if (raw === '' || raw === null || raw === undefined) return raw
  if (NUMERIC_FIELD_TYPES.has(type || '')) {
    const num = Number(raw)
    if (!Number.isNaN(num)) return num
  }
  if (typeof raw === 'string' && raw.trim() !== '' && !Number.isNaN(Number(raw))) {
    return Number(raw)
  }
  return raw
}

export function staticFieldOptionItems(field?: FormFieldDef): { label: string; value: string }[] {
  if (!field) return []
  const props = field.props || {}
  const code = String(props.optionSetCode || '').trim()
  if ((props.optionSource === 'option_set' || code) && code) {
    return []
  }
  const rows = (props.options as { name?: string; code?: string; label?: string; value?: string }[]) || []
  return rows
    .map((item) => {
      if (!item || typeof item !== 'object') return null
      const name = String(item.name || item.label || '').trim()
      const codeVal = String(item.code || item.value || name).trim()
      if (!codeVal) return null
      const label = name && codeVal && name !== codeVal ? `${name}（${codeVal}）` : name || codeVal
      return { label, value: codeVal }
    })
    .filter((x): x is { label: string; value: string } => !!x)
}

export function normalizeConditionScalar(val: unknown): unknown {
  if (val === null || val === undefined || val === '') return val
  if (typeof val === 'boolean') return val
  if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
    const o = val as Record<string, unknown>
    if ('amount' in o || 'rmb_amount' in o || 'currency' in o) {
      const rmb = o.rmb_amount
      if (rmb != null && rmb !== '' && !Number.isNaN(Number(rmb))) return Number(rmb)
      const amt = o.amount
      if (amt != null && amt !== '' && !Number.isNaN(Number(amt))) return Number(amt)
      return null
    }
    return val
  }
  if (typeof val === 'string') {
    const s = val.trim()
    if (s.toLowerCase() === 'true') return true
    if (s.toLowerCase() === 'false') return false
    if (s === '1') return true
    if (s === '0') return false
    if (s !== '' && !Number.isNaN(Number(s))) return Number(s)
    return s
  }
  return val
}

export function conditionValuesEqual(actual: unknown, expected: unknown): boolean {
  const a = normalizeConditionScalar(actual)
  const b = normalizeConditionScalar(expected)
  if (typeof a === 'boolean' || typeof b === 'boolean') return Boolean(a) === Boolean(b)
  return a === b
}
