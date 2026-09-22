/** 日期区间（含上午/下午）解析与 0.5 天计算。 */

export type HalfDay = 'am' | 'pm'

export interface DateRangeValue {
  start: string
  end: string
  startHalf?: HalfDay
  endHalf?: HalfDay
  days?: number
}

const DATE_RE = /^(\d{4})[-/](\d{2})[-/](\d{2})/

export function toDateOnly(raw: unknown): string {
  if (raw == null || raw === '') return ''
  if (typeof raw === 'string') {
    const m = raw.trim().match(DATE_RE)
    return m ? `${m[1]}-${m[2]}-${m[3]}` : ''
  }
  if (raw instanceof Date && !Number.isNaN(raw.getTime())) {
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${raw.getFullYear()}-${pad(raw.getMonth() + 1)}-${pad(raw.getDate())}`
  }
  if (typeof raw === 'object') {
    const o = raw as { format?: (s: string) => string; $d?: Date; toDate?: () => Date }
    if (typeof o.format === 'function') {
      try {
        const text = String(o.format('YYYY-MM-DD') || '')
        const m = text.match(DATE_RE)
        if (m) return `${m[1]}-${m[2]}-${m[3]}`
      } catch {
        /* ignore */
      }
    }
    if (typeof o.toDate === 'function') {
      try {
        return toDateOnly(o.toDate())
      } catch {
        /* ignore */
      }
    }
    if (o.$d instanceof Date) return toDateOnly(o.$d)
  }
  return ''
}

export function normalizeHalf(raw: unknown, fallback: HalfDay = 'am'): HalfDay {
  const text = String(raw || '').trim().toLowerCase()
  if (text === 'pm' || text === 'afternoon' || text === '下午') return 'pm'
  if (text === 'am' || text === 'morning' || text === '上午') return 'am'
  return fallback
}

export function parseDateRange(raw: unknown): DateRangeValue | null {
  if (raw == null || raw === '') return null
  if (Array.isArray(raw) && raw.length >= 2) {
    const start = toDateOnly(raw[0])
    const end = toDateOnly(raw[1])
    if (!start || !end) return null
    return { start, end }
  }
  if (typeof raw === 'object') {
    const o = raw as Record<string, unknown>
    const start = toDateOnly(o.start ?? o.from ?? o.begin ?? o[0])
    const end = toDateOnly(o.end ?? o.to ?? o[1])
    if (!start || !end) return null
    const startHalf = o.startHalf != null || o.start_half != null
      ? normalizeHalf(o.startHalf ?? o.start_half, 'am')
      : undefined
    const endHalf = o.endHalf != null || o.end_half != null
      ? normalizeHalf(o.endHalf ?? o.end_half, 'pm')
      : undefined
    const daysRaw = o.days
    const days = typeof daysRaw === 'number' && Number.isFinite(daysRaw) ? daysRaw : undefined
    return { start, end, startHalf, endHalf, days }
  }
  const single = toDateOnly(raw)
  if (!single) return null
  return { start: single, end: single }
}

function dateUtc(ymd: string): number | null {
  const m = ymd.match(DATE_RE)
  if (!m) return null
  return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
}

export interface WorkdayHints {
  offDays?: Iterable<string>
  makeupWorkdays?: Iterable<string>
}

function asSet(values?: Iterable<string> | unknown): Set<string> {
  if (!values) return new Set()
  if (values instanceof Set) return values as Set<string>
  if (Array.isArray(values)) return new Set(values.map(String))
  if (typeof values === 'object' && values !== null && Array.isArray((values as { value?: unknown }).value)) {
    return new Set(((values as { value: unknown[] }).value).map(String))
  }
  try {
    return new Set(values as Iterable<string>)
  } catch {
    return new Set()
  }
}

export function isWorkdayYmd(ymd: string, hints?: WorkdayHints): boolean {
  if (!ymd) return true
  const makeup = asSet(hints?.makeupWorkdays)
  if (makeup.has(ymd)) return true
  const off = asSet(hints?.offDays)
  if (off.has(ymd)) return false
  const t = dateUtc(ymd)
  if (t == null) return true
  const dow = new Date(t).getUTCDay()
  return dow !== 0 && dow !== 6
}

export function eachYmd(start: string, end: string): string[] {
  const a = dateUtc(start)
  const b = dateUtc(end)
  if (a == null || b == null || b < a) return []
  const out: string[] = []
  const pad = (n: number) => String(n).padStart(2, '0')
  for (let t = a; t <= b; t += 86400000) {
    const d = new Date(t)
    out.push(`${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`)
  }
  return out
}

/** 含首尾；halfDay 精确到 0.5；countWorkdays 时跳过周末/法定假（调休计为工作日）。 */
export function calcRangeDays(
  start: string,
  end: string,
  startHalf?: HalfDay,
  endHalf?: HalfDay,
  halfDay = false,
  opts?: { countWorkdays?: boolean } & WorkdayHints,
): number | null {
  const a = dateUtc(start)
  const b = dateUtc(end)
  if (a == null || b == null || b < a) return null
  const sh = startHalf || 'am'
  const eh = endHalf || 'pm'
  if (halfDay && start === end && sh === 'pm' && eh === 'am') return null
  const countWorkdays = !!opts?.countWorkdays
  const daysList = eachYmd(start, end)
  let total = 0
  for (const d of daysList) {
    if (countWorkdays && !isWorkdayYmd(d, opts)) continue
    if (!halfDay) {
      total += 1
      continue
    }
    if (d === start && d === end) {
      total += sh === eh ? 0.5 : 1
      continue
    }
    if (d === start && sh === 'pm') total += 0.5
    else if (d === end && eh === 'am') total += 0.5
    else total += 1
  }
  return Math.round(total * 2) / 2
}

export function countSkippedDays(
  start: string,
  end: string,
  opts?: WorkdayHints,
): number {
  return eachYmd(start, end).filter((d) => !isWorkdayYmd(d, opts)).length
}

export function buildDateRangeValue(
  start: string,
  end: string,
  opts?: {
    halfDay?: boolean
    startHalf?: HalfDay
    endHalf?: HalfDay
    countWorkdays?: boolean
  } & WorkdayHints,
): DateRangeValue | null {
  if (!start || !end) return null
  const halfDay = !!opts?.halfDay
  const startHalf = halfDay ? (opts?.startHalf || 'am') : undefined
  const endHalf = halfDay ? (opts?.endHalf || 'pm') : undefined
  const days = calcRangeDays(start, end, startHalf, endHalf, halfDay, opts)
  if (days == null) return null
  const out: DateRangeValue = { start, end, days }
  if (halfDay) {
    out.startHalf = startHalf
    out.endHalf = endHalf
  }
  return out
}

export function isDateRangeEmpty(raw: unknown): boolean {
  const parsed = parseDateRange(raw)
  return !parsed
}

export function autoDaysKeyOf(
  field: { key?: string; props?: Record<string, unknown> },
  numberKeys: string[],
): string {
  const explicit = String(field.props?.autoDaysKey || '').trim()
  if (explicit) return explicit
  if (numberKeys.includes('leave_days')) return 'leave_days'
  const key = String(field.key || '')
  if ((key === 'leave_period' || key === 'date_range') && numberKeys.includes('days')) {
    return 'days'
  }
  return ''
}

export function usesHalfDay(
  field: { key?: string; props?: Record<string, unknown> },
  numberKeys: string[] = [],
): boolean {
  const props = field.props || {}
  if (props.halfDay === true) return true
  if (props.halfDay === false) return false
  const key = String(field.key || '')
  if (key === 'leave_period') return true
  if (key === 'date_range' && autoDaysKeyOf(field, numberKeys)) return true
  return false
}

export function usesCountWorkdays(
  field: { key?: string; props?: Record<string, unknown> },
  numberKeys: string[] = [],
): boolean {
  const props = field.props || {}
  if (props.countWorkdays === true) return true
  if (props.countWorkdays === false) return false
  return usesHalfDay(field, numberKeys)
}

export function numberFieldKeysFromSchema(schema?: {
  sections?: { fields?: { type?: string; key?: string }[] }[]
}): string[] {
  const keys: string[] = []
  for (const sec of schema?.sections || []) {
    for (const field of sec.fields || []) {
      if (field.type === 'number' && field.key) keys.push(field.key)
    }
  }
  return keys
}

export function formatDateRangeDisplay(
  raw: unknown,
  labels: { am: string; pm: string; sep: string; days?: (n: number) => string },
  halfDay = false,
): string {
  const parsed = parseDateRange(raw)
  if (!parsed) return ''
  const sh = parsed.startHalf
  const eh = parsed.endHalf
  const showHalf = halfDay || !!sh || !!eh
  const halfText = (h?: HalfDay, fallback: HalfDay = 'am') =>
    (h || fallback) === 'pm' ? labels.pm : labels.am
  const left = showHalf ? `${parsed.start} ${halfText(sh, 'am')}` : parsed.start
  const right = showHalf ? `${parsed.end} ${halfText(eh, 'pm')}` : parsed.end
  let text = `${left} ${labels.sep} ${right}`
  const days = parsed.days ?? calcRangeDays(
    parsed.start,
    parsed.end,
    sh,
    eh,
    showHalf,
  )
  if (days != null && labels.days) {
    text += labels.days(days)
  }
  return text
}
