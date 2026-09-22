/** 打印用格式化（随当前语言切换标签与格式） */

import { formatDateTime } from '@/utils/dateTime'
import type { ProcessGraph } from '@/utils/workflowFlowGraph'
import {
  isPrintLocaleEn,
  printAttachmentListJoin,
  printListJoin,
  printNumberLocale,
  printT,
} from '@/utils/printI18n'

const CN_DIGITS = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
const CN_UNITS = ['', '拾', '佰', '仟']
const CN_BIG = ['', '万', '亿']

const CURRENCY_SYMBOL: Record<string, string> = {
  CNY: '￥',
  RMB: '￥',
  USD: 'US$',
  EUR: '€',
  GBP: '£',
  HKD: 'HK$',
  JPY: '￥',
}

const CURRENCY_NAME_KEY: Record<string, string> = {
  CNY: 'print.currency_cny',
  RMB: 'print.currency_cny',
  USD: 'print.currency_usd',
  EUR: 'print.currency_eur',
  GBP: 'print.currency_gbp',
  HKD: 'print.currency_hkd',
  JPY: 'print.currency_jpy',
}

const STATUS_KEYS: Record<string, string> = {
  running: 'print.status_running',
  approved: 'print.status_approved',
  rejected: 'print.status_rejected',
  cancelled: 'print.status_cancelled',
  draft: 'print.status_draft',
}

const ACTION_KEYS: Record<string, string> = {
  submit: 'print.action_submit',
  approve: 'print.action_approve',
  reject: 'print.action_reject',
  transfer: 'print.action_transfer',
  add_sign: 'print.action_add_sign',
  cc: 'print.action_cc',
  auto_approve: 'print.action_auto_approve',
  cancel: 'print.action_cancel',
}

const NODE_TYPE_KEYS: Record<string, string> = {
  start: 'print.node_start',
  approver: 'print.node_approver',
  handler: 'print.node_handler',
  cc: 'print.node_cc',
  condition: 'print.node_condition',
  end: 'print.node_end',
}

export function formatPrintDateTime(iso?: string | null): string {
  return formatDateTime(iso)
}

export function formatPrintDate(iso?: string | null): string {
  if (!iso) return '—'
  const dt = formatDateTime(iso)
  if (dt === '—') return dt
  return dt.slice(0, 10).replace(/-/g, '/')
}

export function instanceStatusLabel(status: string): string {
  const key = STATUS_KEYS[status]
  if (key) return printT(key)
  return status || '—'
}

export function timelineActionLabel(action: string): string {
  const key = ACTION_KEYS[action]
  if (key) return printT(key)
  return action || '—'
}

/** 从流程图解析节点展示名（与设计器节点名称一致） */
export function resolveWorkflowNodeTitle(nodeId: string, graph?: ProcessGraph | null): string {
  const id = (nodeId || '').trim()
  if (!id || !graph?.nodes?.length) return id
  const node = graph.nodes.find((n) => String(n.id) === id)
  if (!node) return id
  const config = (node.config || {}) as { title?: string }
  const title = config.title?.trim()
  if (title) return title
  const legacy = String(node.text || node.name || '').trim()
  if (legacy) return legacy
  const type = String(node.type || '')
  const key = NODE_TYPE_KEYS[type]
  return key ? printT(key) : id
}

/** 审批流程「操作记录」列：避免与节点列重复显示「提交申请」 */
export function timelineOperationText(item: {
  action: string
  comment?: string | null
}): string {
  const comment = (item.comment || '').trim()
  if (comment) return comment
  if (item.action === 'submit') return printT('print.submitted')
  return timelineActionLabel(item.action)
}

/** 金额中文大写（元角分，仅中文环境使用） */
export function amountToChineseUpper(amount: number): string {
  if (isPrintLocaleEn()) return ''
  if (amount == null || Number.isNaN(amount)) return ''
  const fixed = Math.round(amount * 100) / 100
  const [intPart, decPart] = fixed.toFixed(2).split('.')
  const intStr = convertIntegerPart(parseInt(intPart, 10))
  const jiao = parseInt(decPart[0], 10)
  const fen = parseInt(decPart[1], 10)
  let tail = '元'
  if (jiao === 0 && fen === 0) tail += '整'
  else {
    if (jiao) tail += `${CN_DIGITS[jiao]}角`
    if (fen) tail += `${CN_DIGITS[fen]}分`
    else if (jiao) tail += '整'
  }
  if (!intStr) return `零${tail}`
  return `${intStr}${tail}`
}

function convertIntegerPart(n: number): string {
  if (n === 0) return ''
  const s = String(n)
  const groups: string[] = []
  for (let i = s.length; i > 0; i -= 4) {
    groups.unshift(s.slice(Math.max(0, i - 4), i))
  }
  return groups
    .map((g, gi) => {
      const part = convertUnder10000(parseInt(g, 10))
      if (!part) return ''
      return part + CN_BIG[groups.length - 1 - gi]
    })
    .join('')
}

function convertUnder10000(n: number): string {
  if (n === 0) return ''
  let s = ''
  const str = String(n).padStart(4, '0')
  let zero = false
  for (let i = 0; i < 4; i++) {
    const d = parseInt(str[i], 10)
    const unit = CN_UNITS[3 - i]
    if (d === 0) {
      zero = true
      continue
    }
    if (zero) {
      s += '零'
      zero = false
    }
    if (d === 1 && unit === '拾' && !s) s += '拾'
    else s += CN_DIGITS[d] + unit
  }
  return s.replace(/零+$/g, '')
}

function formatAmountNumber(n: number): string {
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString(printNumberLocale(), { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function currencySymbol(code: string): string {
  return CURRENCY_SYMBOL[code] || `${code} `
}

function currencyDisplayName(code: string): string {
  const key = CURRENCY_NAME_KEY[code]
  return key ? printT(key) : code
}

function moneyUpperSuffix(currencyCode: string, upper: string): string {
  if (!upper) return ''
  if (currencyCode === 'CNY' || currencyCode === 'RMB') {
    return printT('print.money_in_cny', { upper })
  }
  return printT('print.money_in_currency', { upper, currency: currencyDisplayName(currencyCode) })
}

export function formatMoneyPrint(raw: unknown, includeUppercase = true): string {
  if (raw == null || raw === '') return '—'
  const useUpper = includeUppercase && !isPrintLocaleEn()
  if (typeof raw === 'number') {
    const upper = useUpper ? amountToChineseUpper(raw) : ''
    return `￥${formatAmountNumber(raw)}${moneyUpperSuffix('CNY', upper)}`
  }
  if (typeof raw === 'object' && !Array.isArray(raw)) {
    const o = raw as Record<string, unknown>
    const cur = String(o.currency || 'CNY').toUpperCase()
    const amt = o.amount != null ? Number(o.amount) : NaN
    const rmb = o.rmb_amount != null ? Number(o.rmb_amount) : amt
    if (Number.isNaN(amt) && Number.isNaN(rmb)) return '—'

    const sym = currencySymbol(cur)
    const amtText = !Number.isNaN(amt) ? `${sym}${formatAmountNumber(amt)}` : '—'

    if (cur === 'CNY' || cur === 'RMB') {
      const base = !Number.isNaN(rmb) ? rmb : amt
      const upper = useUpper ? amountToChineseUpper(base) : ''
      return `${sym}${formatAmountNumber(base)}${moneyUpperSuffix('CNY', upper)}`
    }

    const parts = [amtText]
    if (!Number.isNaN(rmb) && rmb !== amt) {
      parts.push(printT('print.money_converted', { amount: formatAmountNumber(rmb) }))
      if (useUpper) {
        const rmbUpper = amountToChineseUpper(rmb)
        if (rmbUpper) parts.push(moneyUpperSuffix('CNY', rmbUpper))
      }
    }
    if (useUpper) {
      const foreignUpper = !Number.isNaN(amt) ? amountToChineseUpper(amt) : ''
      if (foreignUpper) {
        parts.push(moneyUpperSuffix(cur, foreignUpper))
      }
    }
    return parts.join(' ')
  }
  return String(raw)
}

export function formatPlainAmountPrint(raw: unknown, precision = 2): string {
  if (raw == null || raw === '') return '—'
  const n = typeof raw === 'number' ? raw : Number(String(raw).replace(/,/g, ''))
  if (Number.isNaN(n)) return '—'
  const formatted = n.toLocaleString(printNumberLocale(), {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  })
  return `￥${formatted}`
}

export function formatPlainValue(v: unknown): string {
  if (v === undefined || v === null || v === '') return '—'
  if (Array.isArray(v)) {
    if (!v.length) return '—'
    return printListJoin(v.map((x) => formatPlainValue(x)))
  }
  if (typeof v === 'boolean') return v ? printT('print.yes') : printT('print.no')
  if (typeof v === 'object') {
    try {
      return JSON.stringify(v)
    } catch {
      return '—'
    }
  }
  return String(v)
}

/** 打印用附件名：保留前 5 个字符 + ... + 扩展名，避免长文件名撑高页面。 */
export function truncatePrintFilename(name: string, headLen = 5): string {
  const raw = (name || '').trim()
  if (!raw) return ''
  const base = raw.replace(/\\/g, '/').split('/').pop() || raw
  const dot = base.lastIndexOf('.')
  if (dot <= 0) {
    return base.length > headLen ? `${base.slice(0, headLen)}...` : base
  }
  const stem = base.slice(0, dot)
  const ext = base.slice(dot)
  if (stem.length <= headLen) return base
  return `${stem.slice(0, headLen)}...${ext}`
}

function attachmentDisplayName(item: unknown): string {
  if (item && typeof item === 'object') {
    const o = item as Record<string, unknown>
    return String(o.name || o.filename || o.url || '').trim()
  }
  return String(item || '').trim()
}

export function formatAttachmentNamesForPrint(raw: unknown): string {
  const names: string[] = []
  const push = (item: unknown) => {
    const name = attachmentDisplayName(item)
    if (!name) return
    names.push(truncatePrintFilename(name))
  }
  if (Array.isArray(raw)) {
    raw.forEach(push)
  } else if (raw !== undefined && raw !== null && raw !== '') {
    push(raw)
  }
  return names.filter(Boolean).length ? printAttachmentListJoin(names.filter(Boolean)) : '—'
}

export function signatureImageSrc(item: {
  signature_data?: string
  signature_path?: string
}): string | null {
  if (item.signature_data?.startsWith('data:image')) return item.signature_data
  if (item.signature_path) {
    const p = item.signature_path.replace(/^\//, '')
    return `/api/v1/files/${p.startsWith('uploads/') ? p : `uploads/${p}`}`
  }
  return null
}
