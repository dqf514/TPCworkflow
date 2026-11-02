/** 列表金额展示（数字格式，不含大写） */
import { formatMoney } from '@/utils/currency'

export function formatInstanceListAmount(
  amount?: number | null,
  currency?: string | null,
): string {
  if (amount == null || Number.isNaN(amount)) return '—'
  const curr = (currency || 'CNY').toUpperCase()
  // 货币符号统一走 @/utils/currency：人民币 ￥(U+FFE5)，日元 ¥(U+00A5)
  return formatMoney(amount, curr)
}
