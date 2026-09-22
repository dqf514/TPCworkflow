/** 列表金额展示（数字格式，不含大写） */
export function formatInstanceListAmount(
  amount?: number | null,
  currency?: string | null,
): string {
  if (amount == null || Number.isNaN(amount)) return '—'
  const formatted = amount.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  const curr = (currency || 'CNY').toUpperCase()
  if (curr === 'CNY' || curr === 'RMB') return `￥${formatted}`
  return `${formatted} ${currency}`
}
