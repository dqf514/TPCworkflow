import type { FormFieldDef, FormSchema } from '@/types/form'
import { getMoneyRmbTotal, getPlainAmountNumber } from '@/composables/useMoneyField'

export interface FormulaContext {
  model: Record<string, unknown>
  schema?: FormSchema
  detailRow?: Record<string, unknown>
  detailKey?: string
}

export interface FormulaRefOption {
  label: string
  insert: string
}

function findDetailColumn(
  schema: FormSchema | undefined,
  detailKey: string,
  colKey: string,
): FormFieldDef | undefined {
  if (!schema) return undefined
  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (field.key !== detailKey || field.type !== 'detail') continue
      return ((field.props?.columns as FormFieldDef[]) || []).find((c) => c.key === colKey)
    }
  }
  return undefined
}

function findMainField(schema: FormSchema | undefined, key: string): FormFieldDef | undefined {
  if (!schema) return undefined
  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (field.key === key) return field
    }
  }
  return undefined
}

function cellToNumber(raw: unknown, field?: FormFieldDef): number {
  if (raw == null || raw === '') return 0
  if (field?.type === 'money') return getMoneyRmbTotal(raw)
  if (field?.type === 'plain_amount') return getPlainAmountNumber(raw)
  if (typeof raw === 'number') return Number.isFinite(raw) ? raw : 0
  if (typeof raw === 'boolean') return raw ? 1 : 0
  const n = Number(String(raw).replace(/,/g, ''))
  return Number.isFinite(n) ? n : 0
}

function detailColumnValues(
  rows: Record<string, unknown>[],
  colKey: string,
  schema: FormSchema | undefined,
  detailKey: string,
): number[] {
  const colDef = findDetailColumn(schema, detailKey, colKey)
  return rows.map((row) => cellToNumber(row[colKey], colDef))
}

function aggregateDetailRef(
  detailKey: string,
  colKey: string,
  fn: 'SUM' | 'AVG' | 'MIN' | 'MAX',
  ctx: FormulaContext,
): number {
  const rows = ctx.model[detailKey]
  if (!Array.isArray(rows) || !rows.length) return 0
  const vals = detailColumnValues(rows, colKey, ctx.schema, detailKey)
  if (!vals.length) return 0
  if (fn === 'SUM') return vals.reduce((a, b) => a + b, 0)
  if (fn === 'AVG') return vals.reduce((a, b) => a + b, 0) / vals.length
  if (fn === 'MIN') return Math.min(...vals)
  return Math.max(...vals)
}

function resolveRef(ref: string, ctx: FormulaContext): number {
  const key = ref.trim()
  if (!key) return 0
  if (key.includes('.')) {
    const [detailKey, colKey] = key.split('.', 2)
    return aggregateDetailRef(detailKey, colKey, 'SUM', ctx)
  }
  if (ctx.detailRow && Object.prototype.hasOwnProperty.call(ctx.detailRow, key)) {
    const colDef = findDetailColumn(ctx.schema, ctx.detailKey || '', key)
    return cellToNumber(ctx.detailRow[key], colDef)
  }
  const fieldDef = findMainField(ctx.schema, key)
  return cellToNumber(ctx.model[key], fieldDef)
}

function substituteRefs(expr: string, ctx: FormulaContext): string {
  return expr.replace(/\$\{([^}]+)\}/g, (_, ref: string) => String(resolveRef(ref, ctx)))
}

function parseExpression(expr: string): number {
  let pos = 0
  const s = expr

  function parseAddSub(): number {
    let left = parseMulDiv()
    while (pos < s.length && (s[pos] === '+' || s[pos] === '-')) {
      const op = s[pos++]
      const right = parseMulDiv()
      left = op === '+' ? left + right : left - right
    }
    return left
  }

  function parseMulDiv(): number {
    let left = parseUnary()
    while (pos < s.length && (s[pos] === '*' || s[pos] === '/')) {
      const op = s[pos++]
      const right = parseUnary()
      left = op === '*' ? left * right : right === 0 ? 0 : left / right
    }
    return left
  }

  function parseUnary(): number {
    if (s[pos] === '-') {
      pos++
      return -parseUnary()
    }
    if (s[pos] === '+') {
      pos++
      return parseUnary()
    }
    return parsePrimary()
  }

  function parsePrimary(): number {
    if (s[pos] === '(') {
      pos++
      const v = parseAddSub()
      if (s[pos] === ')') pos++
      return v
    }
    const start = pos
    while (pos < s.length && /[\d.]/.test(s[pos])) pos++
    return parseFloat(s.slice(start, pos)) || 0
  }

  pos = 0
  const result = parseAddSub()
  return Number.isFinite(result) ? result : 0
}

function evaluateMath(expr: string): number {
  const cleaned = expr.replace(/\s+/g, '')
  if (!cleaned) return 0
  if (!/^[\d.+\-*/()]+$/.test(cleaned)) return 0
  return parseExpression(cleaned)
}

function expandFunctions(expr: string, ctx: FormulaContext): string {
  let s = expr.trim()
  for (let guard = 0; guard < 64; guard++) {
    let changed = false

    s = s.replace(/\b(SUM|AVG|MIN|MAX)\(\s*(\$\{[^}]+\})\s*\)/gi, (match, fnName, refToken) => {
      changed = true
      const ref = String(refToken).slice(2, -1).trim()
      const fn = String(fnName).toUpperCase() as 'SUM' | 'AVG' | 'MIN' | 'MAX'
      if (ref.includes('.')) {
        const [detailKey, colKey] = ref.split('.', 2)
        return String(aggregateDetailRef(detailKey, colKey, fn, ctx))
      }
      return String(resolveRef(ref, ctx))
    })

    s = s.replace(/\bROUND\(\s*([^,()]+(?:\([^)]*\))?)\s*,\s*(\d+)\s*\)/gi, (match, inner, digits) => {
      changed = true
      const val = evaluateMath(substituteRefs(String(inner), ctx))
      const d = parseInt(String(digits), 10)
      const factor = 10 ** (Number.isFinite(d) ? d : 2)
      return String(Math.round(val * factor) / factor)
    })

    if (!changed) break
  }
  return s
}

export function evaluateFormFormula(expression: string, ctx: FormulaContext): number | null {
  const raw = (expression || '').trim()
  if (!raw) return null
  try {
    const expanded = expandFunctions(raw, ctx)
    const substituted = substituteRefs(expanded, ctx)
    return evaluateMath(substituted)
  } catch {
    return null
  }
}

export function formatFormulaResult(value: number | null, field: FormFieldDef): string | number {
  if (value == null || Number.isNaN(value)) return ''
  const precisionRaw = field.props?.precision
  if (precisionRaw !== undefined && precisionRaw !== null && precisionRaw !== '') {
    const precision = Number(precisionRaw)
    if (Number.isFinite(precision) && precision >= 0) {
      return value.toFixed(precision)
    }
  }
  if (Number.isInteger(value)) return value
  return Math.round(value * 100) / 100
}

export function applyFormFormulas(schema: FormSchema, model: Record<string, unknown>): void {
  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (field.type !== 'detail' || !field.key) continue
      const cols = ((field.props?.columns as FormFieldDef[]) || []).filter(
        (c) => c.type === 'formula' && c.key && c.props?.expression,
      )
      if (!cols.length) continue
      const rows = model[field.key]
      if (!Array.isArray(rows)) continue
      for (const row of rows) {
        if (!row || typeof row !== 'object') continue
        for (const col of cols) {
          const expr = String(col.props?.expression || '')
          const val = evaluateFormFormula(expr, {
            model,
            schema,
            detailRow: row as Record<string, unknown>,
            detailKey: field.key,
          })
          const formatted = formatFormulaResult(val, col)
          ;(row as Record<string, unknown>)[col.key] = formatted
        }
      }
    }
  }

  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (field.type !== 'formula' || !field.key) continue
      const expr = String(field.props?.expression || '')
      if (!expr) {
        if (model[field.key] !== '') model[field.key] = ''
        continue
      }
      const val = evaluateFormFormula(expr, { model, schema })
      model[field.key] = formatFormulaResult(val, field)
    }
  }
}

export function collectFormulaRefOptions(
  schema: FormSchema,
  opts?: { excludeKey?: string; detailOnly?: boolean; detailKey?: string },
): FormulaRefOption[] {
  const out: FormulaRefOption[] = []
  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (field.type === 'detail' && field.key) {
        for (const col of (field.props?.columns as FormFieldDef[]) || []) {
          if (!col.key || col.type === 'formula') continue
          if (opts?.detailOnly) {
            if (field.key !== opts.detailKey) continue
            if (['divider', 'text_block', 'section_title', 'attachment', 'image', 'smart_receipt'].includes(col.type)) {
              continue
            }
            out.push({
              label: col.label || col.key,
              insert: `\${${col.key}}`,
            })
            continue
          }
          if (['divider', 'text_block', 'section_title', 'attachment', 'image', 'smart_receipt'].includes(col.type)) {
            continue
          }
          out.push({
            label: `${field.label || field.key} · ${col.label || col.key}`,
            insert: `\${${field.key}.${col.key}}`,
          })
        }
        continue
      }
      if (!field.key || field.type === 'formula') continue
      if (opts?.detailOnly) continue
      if (field.key === opts?.excludeKey) continue
      if (['divider', 'text_block', 'section_title', 'detail', 'related_form', 'attachment', 'image', 'smart_receipt'].includes(field.type)) {
        continue
      }
      out.push({
        label: field.label || field.key,
        insert: `\${${field.key}}`,
      })
    }
  }
  return out
}
