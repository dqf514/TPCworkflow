/**
 * 金额与货币符号的统一出口。
 *
 * 背景：站点里 `￥`(U+FFE5) 与 `¥`(U+00A5) 混用，DetailField 里还写成
 * `¥ 1,234.56`（半角符号 + 空格），日元更是被映射成 `￥`（与人民币同形），
 * 导致日元凭证金额被误读成人民币。
 *
 * 约定：
 * - 人民币用全角 `￥`(U+FFE5)，与中文记账习惯一致；
 * - 日元用半角 `¥`(U+00A5)，与人民币区分；
 * - 其余币种用通用缩写（US$ / € / £ / HK$ …），未知币种回退成「代码 」前缀。
 */

/** 货币符号表 */
const CURRENCY_SYMBOL: Record<string, string> = {
  CNY: '￥',
  RMB: '￥',
  JPY: '¥',
  USD: 'US$',
  EUR: '€',
  GBP: '£',
  HKD: 'HK$',
  TWD: 'NT$',
  SGD: 'S$',
  AUD: 'A$',
  CAD: 'C$',
  KRW: '₩',
}

/** 人民币符号（U+FFE5 全角） */
export const CNY_SYMBOL = '￥'

/** 归一化币种代码 */
export function normalizeCurrencyCode(code?: string | null): string {
  return String(code || '').trim().toUpperCase()
}

/**
 * 货币符号。
 * 未知币种回退成「代码 」前缀（例如 `XYZ 1,234.00`），保证金额不会丢失币种信息。
 */
export function currencySymbol(code?: string | null): string {
  const key = normalizeCurrencyCode(code)
  if (!key) return ''
  return CURRENCY_SYMBOL[key] || `${key} `
}

/** 纯数字金额格式化（千分位 + 固定小数位） */
export function formatMoneyNumber(
  value: number | string | null | undefined,
  fractionDigits = 2,
  locale = 'zh-CN',
): string {
  const n = typeof value === 'number' ? value : Number(String(value ?? '').replace(/,/g, ''))
  if (!Number.isFinite(n)) return '—'
  return n.toLocaleString(locale, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
}

/**
 * 带货币符号的金额。
 *
 * 不直接用 `Intl.NumberFormat({ style: 'currency' })`：ICU 会把人民币输出成半角 `¥`，
 * 且日元默认 0 位小数，与站内金额一律 2 位小数的口径不一致。
 * 这里用 Intl 只做数字分组，符号统一走 {@link currencySymbol}。
 */
export function formatMoney(
  value: number | string | null | undefined,
  code?: string | null,
  options?: { fractionDigits?: number; locale?: string },
): string {
  if (value == null || value === '') return ''
  const fractionDigits = options?.fractionDigits ?? 2
  const locale = options?.locale ?? 'zh-CN'
  const number = formatMoneyNumber(value, fractionDigits, locale)
  if (number === '—') return number
  return `${currencySymbol(code || 'CNY')}${number}`
}
