import type { PrintFieldItem, PrintTemplateBlock, PrintTemplateSchema } from '@/types/printTemplate'

function toNumber(val: unknown): number | null {
  if (val == null || val === '') return null
  if (typeof val === 'number' && Number.isFinite(val)) return val
  if (typeof val === 'object' && val !== null) {
    const o = val as Record<string, unknown>
    for (const k of ['amount', 'rmb_amount']) {
      const n = Number(o[k])
      if (Number.isFinite(n)) return n
    }
  }
  const n = Number(val)
  return Number.isFinite(n) ? n : null
}

export function formatPrintMoney(val: unknown, currency = 'USD'): string {
  const n = toNumber(val)
  if (n == null) return '—'
  const formatted = n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return currency === 'USD' ? formatted : `${formatted} ${currency}`
}

export function formatPrintDateSlash(val: unknown): string {
  if (val == null || val === '') return '—'
  const s = String(val).trim()
  if (s.length >= 10 && s[4] === '-' && s[7] === '-') {
    const y = s.slice(0, 4)
    const m = String(Number(s.slice(5, 7)))
    const d = String(Number(s.slice(8, 10)))
    return `${y}/${m}/${d}`
  }
  return s
}

export function formatPrintFieldValue(val: unknown, format?: string, currency = 'USD'): string {
  if (val == null || val === '') return '—'
  if (format === 'date_slash') return formatPrintDateSlash(val)
  if (format === 'money_plain') return formatPrintMoney(val, currency)
  if (typeof val === 'object') {
    const n = toNumber(val)
    if (n != null) return formatPrintMoney(n, currency)
  }
  return String(val)
}

export function resolveFormField(form: Record<string, unknown>, key?: string): unknown {
  if (!key) return undefined
  return form[key]
}

export function resolveFieldItemText(
  item: PrintFieldItem,
  form: Record<string, unknown>,
  currency = 'USD',
): { label: string; value: string; sub?: string } {
  const label = item.label || ''
  if (item.value != null && item.value !== '') {
    return { label, value: item.value }
  }
  const main = formatPrintFieldValue(resolveFormField(form, item.fieldKey), item.format, currency)
  const subRaw = item.subFieldKey ? resolveFormField(form, item.subFieldKey) : undefined
  const sub = subRaw != null && subRaw !== '' ? String(subRaw) : undefined
  return { label, value: main, sub }
}

export function computeDetailTotal(block: PrintTemplateBlock, form: Record<string, unknown>): number {
  const totalKey = block.totalFieldKey
  if (totalKey) {
    const preset = toNumber(form[totalKey])
    if (preset != null) return preset
  }
  const rows = form[block.fieldKey || '']
  if (!Array.isArray(rows)) return 0
  const amountKey =
    block.columns?.find((c) => c.format === 'money_plain' || c.key === 'amount')?.key || 'amount'
  let sum = 0
  for (const row of rows) {
    if (row && typeof row === 'object') {
      const n = toNumber((row as Record<string, unknown>)[amountKey])
      if (n != null) sum += n
    }
  }
  return sum
}

export function resolveTemplateCurrency(schema: PrintTemplateSchema, form: Record<string, unknown>): string {
  const tableBlock = Object.values(schema.blocks || {}).find((b) => b.type === 'detail_table')
  const key = tableBlock?.currencyFieldKey || 'currency'
  const fromForm = form[key]
  if (fromForm) return String(fromForm)
  const label = tableBlock?.currencyLabel || 'USD'
  const m = label.match(/[A-Z]{3}/)
  return m ? m[0] : 'USD'
}

export function resolveAssetUrl(url?: string): string {
  if (!url) return ''
  if (url.startsWith('http') || url.startsWith('data:') || url.startsWith('/api/')) return url
  const clean = url.replace(/^\/+/, '')
  return `/api/v1/files/${clean}`
}

export function getBlock(schema: PrintTemplateSchema, blockId: string) {
  return schema.blocks?.[blockId]
}
