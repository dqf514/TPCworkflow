export type SerialDatePart = 'none' | 'YYYY' | 'YYYYMM' | 'YYYYMMDD'
export type SerialResetCycle = 'never' | 'day' | 'month' | 'year'
export type SerialScope = 'global' | 'company' | 'definition'

export interface SerialNoConfig {
  /** 高级：完整模板，非空时优先于简易项 */
  pattern?: string
  prefix?: string
  suffix?: string
  seqDigits?: number
  datePart?: SerialDatePart
  separator?: string
  resetCycle?: SerialResetCycle
  scope?: SerialScope
}

const SEQ_RE = /\{SEQ(?::(\d+))?\}/gi

function pad(n: number, width: number) {
  return String(n).padStart(width, '0')
}

function formatNow(now: Date) {
  const y = now.getFullYear()
  const m = pad(now.getMonth() + 1, 2)
  const d = pad(now.getDate(), 2)
  return {
    YYYY: String(y),
    YY: String(y).slice(-2),
    MM: m,
    DD: d,
    YYYYMMDD: `${y}${m}${d}`,
    YYYYMM: `${y}${m}`,
  }
}

export function normalizeSerialConfig(field: { props?: Record<string, unknown> }): SerialNoConfig {
  const props = field.props || {}
  const serial = (props.serial as SerialNoConfig) || {}
  const seqRaw = serial.seqDigits ?? props.seqDigits ?? 4
  let seqDigits = Number(seqRaw)
  if (!Number.isFinite(seqDigits)) seqDigits = 4
  seqDigits = Math.max(1, Math.min(10, Math.round(seqDigits)))

  let datePart = String(serial.datePart ?? props.datePart ?? 'YYYYMMDD').toUpperCase()
  if (datePart.toLowerCase() === 'none') datePart = 'none'
  if (!['none', 'YYYY', 'YYYYMM', 'YYYYMMDD'].includes(datePart)) datePart = 'YYYYMMDD'

  let resetCycle = String(serial.resetCycle ?? props.resetCycle ?? 'day').toLowerCase() as SerialResetCycle
  if (!['never', 'day', 'month', 'year'].includes(resetCycle)) resetCycle = 'day'

  let scope = String(serial.scope ?? props.scope ?? 'company').toLowerCase() as SerialScope
  if (!['global', 'company', 'definition'].includes(scope)) scope = 'company'

  const separator =
    serial.separator !== undefined
      ? String(serial.separator)
      : props.separator !== undefined
        ? String(props.separator)
        : '-'

  return {
    pattern: String(props.pattern || serial.pattern || '').trim() || undefined,
    prefix: String(serial.prefix ?? props.prefix ?? '').trim() || undefined,
    suffix: String(serial.suffix ?? props.suffix ?? '').trim() || undefined,
    seqDigits,
    datePart: datePart as SerialDatePart,
    separator,
    resetCycle,
    scope,
  }
}

export function buildSerialPattern(cfg: SerialNoConfig): string {
  if (cfg.pattern?.trim()) return cfg.pattern.trim()

  const prefix = cfg.prefix || ''
  const suffix = cfg.suffix || ''
  const sep = cfg.separator ?? '-'
  const seqDigits = cfg.seqDigits ?? 4
  const datePart = cfg.datePart ?? 'YYYYMMDD'

  let dateToken = ''
  if (datePart === 'YYYY') dateToken = '{YYYY}'
  else if (datePart === 'YYYYMM') dateToken = '{YYYYMM}'
  else if (datePart !== 'none') dateToken = '{YYYYMMDD}'

  const seqToken = `{SEQ:${seqDigits}}`

  if (dateToken) {
    return sep ? `${prefix}${dateToken}${sep}${seqToken}${suffix}` : `${prefix}${dateToken}${seqToken}${suffix}`
  }
  if (prefix && sep) return `${prefix}${sep}${seqToken}${suffix}`
  return `${prefix}${seqToken}${suffix}`
}

export function renderSerialPattern(pattern: string, seq = 1, now = new Date()): string {
  const parts = formatNow(now)
  const defaultDigits = (() => {
    const m = pattern.match(/\{SEQ:(\d+)\}/i)
    if (m) return Math.max(1, Math.min(10, Number(m[1]) || 4))
    return 4
  })()

  let text = pattern.replace(SEQ_RE, (_m, n) => pad(seq, n ? Number(n) : defaultDigits))
  text = text.replace(/\{YYYY\}/g, parts.YYYY)
  text = text.replace(/\{YY\}/g, parts.YY)
  text = text.replace(/\{MM\}/g, parts.MM)
  text = text.replace(/\{DD\}/g, parts.DD)
  text = text.replace(/\{YYYYMMDD\}/g, parts.YYYYMMDD)
  text = text.replace(/\{YYYYMM\}/g, parts.YYYYMM)
  return text
}

export function previewSerialNo(field: { props?: Record<string, unknown> }, seq = 1, now = new Date()) {
  const cfg = normalizeSerialConfig(field)
  return renderSerialPattern(buildSerialPattern(cfg), seq, now)
}

export function defaultSerialNoProps(): { serial: SerialNoConfig } {
  return {
    serial: {
      prefix: '',
      suffix: '',
      seqDigits: 4,
      datePart: 'YYYYMMDD',
      separator: '-',
      resetCycle: 'day',
      scope: 'company',
      pattern: '',
    },
  }
}
