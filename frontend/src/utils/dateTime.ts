/**
 * 界面统一时间：本地时间 YYYY-MM-DD HH:mm（无秒、无 ISO 的 T）
 */
export function formatDateTime(value?: string | null): string {
  if (!value) return '—'
  const s = String(value).trim()
  const matched = s.match(/^(\d{4})[-/](\d{2})[-/](\d{2})[ T](\d{2}):(\d{2})/)
  if (matched) {
    return `${matched[1]}-${matched[2]}-${matched[3]} ${matched[4]}:${matched[5]}`
  }
  const normalized = s.includes('T') ? s : s.replace(' ', 'T')
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return s
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 仅日期 YYYY-MM-DD */
export function formatDate(value?: string | null): string {
  if (!value) return '—'
  const dt = formatDateTime(value)
  if (dt === '—') return dt
  return dt.slice(0, 10)
}
