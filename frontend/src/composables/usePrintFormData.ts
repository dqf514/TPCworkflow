import type { FormFieldDef, FormSchema } from '@/types/form'
import { isPrintFullWidthField } from '@/types/form'
import { resolveFieldOptions, resolveOptionLabel, type FieldOptionItem } from '@/composables/useFieldOptions'
import { buildLinkageContext, shouldDisplayField, shouldDisplaySection } from '@/composables/useFieldLinkage'
import { getAmountColumnTotal, isAmountSummaryFieldType } from '@/composables/useMoneyField'
import { api, type ApiResponse } from '@/api/client'
import { formatMoneyPrint, formatPlainAmountPrint, formatPlainValue, formatPrintDate, formatPrintDateTime, formatAttachmentNamesForPrint } from '@/utils/printFormat'
import { formatRecordSetValueForPrint, loadRecordSetPayload } from '@/composables/useRecordSets'
import { printAttachmentListJoin, printListJoin, printT } from '@/utils/printI18n'
import { formatDateRangeDisplay, parseDateRange, usesHalfDay } from '@/utils/dateRangeValue'
import {
  collectDeptIdsFromModel,
  resolveDepartmentLabels,
} from '@/composables/useOrgDeptOptions'

export type BuildPrintSectionsOptions = {
  companyId?: number
  departmentId?: number
}

export interface PrintFieldRow {
  label: string
  value: string
  fullWidth?: boolean
  alignRight?: boolean
}

export interface PrintDetailColumn {
  key: string
  label: string
}

export interface PrintDetailTable {
  title: string
  columns: PrintDetailColumn[]
  rows: Record<string, string>[]
  summaryRows?: PrintFieldRow[]
  moneyColumnKeys?: string[]
}

export interface PrintSectionBlock {
  title: string
  rows: PrintFieldRow[]
  details: PrintDetailTable[]
  textBlocks: { label: string; content: string }[]
}

function labelForOption(val: unknown, opts: FieldOptionItem[]): string {
  return resolveOptionLabel(val, opts)
}

function pickerLabel(
  val: unknown,
  userMap: Record<number, string>,
  deptMap: Record<number, string>,
  isDept: boolean,
): string {
  if (val === undefined || val === null || val === '') return '—'
  const map = isDept ? deptMap : userMap
  const one = (id: unknown) => map[Number(id)] || String(id)
  if (Array.isArray(val)) return printListJoin(val.map(one)) || '—'
  return one(val)
}

function localYmd(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function resolveLeaveCalendarPrintWindow(
  model: Record<string, unknown>,
  periodKeys: string[],
): { from: string; to: string } {
  let min = ''
  let max = ''
  for (const key of periodKeys) {
    if (!key) continue
    const parsed = parseDateRange(model[key])
    if (!parsed) continue
    if (!min || parsed.start < min) min = parsed.start
    if (!max || parsed.end > max) max = parsed.end
  }
  if (min && max) {
    const from = new Date(`${min}T00:00:00`)
    from.setDate(1)
    const to = new Date(`${max}T00:00:00`)
    to.setMonth(to.getMonth() + 1, 0)
    return { from: localYmd(from), to: localYmd(to) }
  }
  const now = new Date()
  const from = new Date(now.getFullYear(), now.getMonth(), 1)
  const to = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return { from: localYmd(from), to: localYmd(to) }
}

function formatLeaveEventPeriod(startRaw: string, endRaw: string): string {
  const start = String(startRaw || '').slice(0, 10)
  let endDay = String(endRaw || '').slice(0, 10)
  // FullCalendar 风格的 end 常为次日（不含），打印时回退一天更直观
  if (start && endDay && endDay > start) {
    const d = new Date(`${endDay}T00:00:00`)
    d.setDate(d.getDate() - 1)
    const exclusiveEnd = localYmd(d)
    if (exclusiveEnd >= start) endDay = exclusiveEnd
  }
  if (!start) return '—'
  if (!endDay || endDay === start) return start
  return `${start} ${printT('print.date_range_sep')} ${endDay}`
}

function toLeaveCalQueryCsv(keys: string[] | undefined, fallback: string): string {
  const list = (keys || []).map((x) => String(x || '').trim()).filter(Boolean)
  return list.length ? list.join(',') : fallback
}

async function buildLeaveCalendarPrintTable(
  field: FormFieldDef,
  model: Record<string, unknown>,
  options?: BuildPrintSectionsOptions,
): Promise<PrintDetailTable> {
  const periodKeys = ((field.props?.periodFieldKeys as string[]) || [
    'leave_period',
    'date_range',
  ])
    .map((x) => String(x || '').trim())
    .filter(Boolean)
  const { from, to } = resolveLeaveCalendarPrintWindow(model, periodKeys)
  const title = field.label || printT('print.leave_calendar')
  const columns: PrintDetailColumn[] = [
    { key: 'user', label: printT('print.leave_cal_user') },
    { key: 'type', label: printT('print.leave_cal_type') },
    { key: 'period', label: printT('print.leave_cal_period') },
    { key: 'form', label: printT('print.leave_cal_form') },
    { key: 'no', label: printT('print.leave_cal_no') },
  ]
  const titled = `${title}（${from} ${printT('print.date_range_sep')} ${to}）`
  const emptyTable = (): PrintDetailTable => ({
    title: titled,
    columns,
    rows: [{ user: printT('print.leave_cal_empty'), type: '', period: '', form: '', no: '' }],
  })

  try {
    const res = await api.get<
      ApiResponse<{
        events: Array<{
          user_name?: string
          leave_type_label?: string
          leave_type?: string
          start: string
          end: string
          form_name?: string
          form_key?: string
          display_no?: string
          title?: string
        }>
      }>
    >('/leave-calendar/events', {
      params: {
        from,
        to,
        company_id: options?.companyId || undefined,
        department_id: options?.departmentId || undefined,
        form_keys: toLeaveCalQueryCsv(field.props?.formKeys as string[] | undefined, 'auto'),
        period_field_keys: toLeaveCalQueryCsv(periodKeys, 'leave_period,date_range'),
        leave_type_field_key: String(field.props?.leaveTypeFieldKey || 'leave_type'),
        include_running: field.props?.includeRunning === true ? '1' : '0',
        show_reason: field.props?.showReason === true ? '1' : '0',
      },
    })
    const rows = res.data.ok ? res.data.data?.events || [] : []
    if (!rows.length) return emptyTable()
    return {
      title: titled,
      columns,
      rows: rows.map((row) => ({
        user: String(row.user_name || row.title || '—'),
        type: String(row.leave_type_label || row.leave_type || '—'),
        period: formatLeaveEventPeriod(row.start, row.end),
        form: String(row.form_name || row.form_key || '—'),
        no: String(row.display_no || '—'),
      })),
    }
  } catch {
    return emptyTable()
  }
}

async function formatFieldValue(
  field: FormFieldDef,
  raw: unknown,
  optionMap: Record<string, FieldOptionItem[]>,
  userMap: Record<number, string>,
  deptMap: Record<number, string>,
  opts?: { moneyUppercase?: boolean },
): Promise<string> {
  if (raw === undefined || raw === null || raw === '') return '—'
  switch (field.type) {
    case 'money':
      return formatMoneyPrint(raw, opts?.moneyUppercase !== false)
    case 'plain_amount':
      return formatPlainAmountPrint(raw, Number(field.props?.precision ?? 2))
    case 'date':
      return formatPrintDate(String(raw))
    case 'datetime':
      return formatPrintDateTime(String(raw))
    case 'date_range':
      return formatDateRangeDisplay(
        raw,
        {
          am: printT('print.half_am'),
          pm: printT('print.half_pm'),
          sep: printT('print.date_range_sep'),
          days: (n) => printT('print.date_range_days', { n }),
        },
        usesHalfDay(field),
      ) || formatPlainValue(raw)
    case 'select':
    case 'radio':
    case 'multi_select':
    case 'checkbox_group':
      return labelForOption(raw, optionMap[field.id] || [])
    case 'user_picker':
    case 'contact':
      return pickerLabel(raw, userMap, deptMap, false)
    case 'dept_picker':
      return pickerLabel(raw, userMap, deptMap, true)
    case 'switch':
      return raw ? printT('print.yes') : printT('print.no')
    case 'record_set': {
      const code = String(field.props?.recordSetCode || '').trim()
      let cols
      if (code) {
        const payload = await loadRecordSetPayload(code)
        cols = payload?.columns
      }
      return formatRecordSetValueForPrint(raw, cols)
    }
    case 'related_form': {
      if (Array.isArray(raw)) {
        const titles = raw
          .map((r) => {
            if (r && typeof r === 'object') {
              const o = r as Record<string, unknown>
              return String(o.title || o.instance_id || o.id || '')
            }
            return String(r)
          })
          .filter(Boolean)
        return titles.length ? printAttachmentListJoin(titles) : '—'
      }
      if (raw && typeof raw === 'object') {
        const o = raw as Record<string, unknown>
        return String(o.title || o.instance_id || '—')
      }
      return formatPlainValue(raw)
    }
    case 'attachment':
    case 'image':
    case 'smart_receipt':
      return formatAttachmentNamesForPrint(raw)
    case 'formula':
      return formatPlainValue(raw)
    default:
      return formatPlainValue(raw)
  }
}

export async function buildPrintSections(
  schema: FormSchema,
  model: Record<string, unknown>,
  userOpts: { label: string; value: number }[],
  deptOpts: { label: string; value: number }[],
  options?: BuildPrintSectionsOptions,
): Promise<PrintSectionBlock[]> {
  const optionMap: Record<string, FieldOptionItem[]> = {}
  const userMap = Object.fromEntries(userOpts.map((o) => [o.value, o.label]))
  const deptMap: Record<number, string> = Object.fromEntries(deptOpts.map((o) => [o.value, o.label]))
  const missingDeptIds = collectDeptIdsFromModel(schema, model).filter((id) => !deptMap[id])
  if (missingDeptIds.length) {
    const extra = await resolveDepartmentLabels(missingDeptIds)
    for (const o of extra) deptMap[o.value] = o.label
  }

  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (['select', 'multi_select', 'radio', 'checkbox_group'].includes(field.type)) {
        optionMap[field.id] = await resolveFieldOptions(field)
      }
      if (field.type === 'detail') {
        for (const col of (field.props?.columns as FormFieldDef[]) || []) {
          if (['select', 'multi_select', 'radio', 'checkbox_group'].includes(col.type)) {
            optionMap[col.id] = await resolveFieldOptions(col)
          }
        }
      }
    }
  }

  const blocks: PrintSectionBlock[] = []

  const linkageCtx = buildLinkageContext(schema)
  const gridCols = schema.layout?.gridCols ?? 24

  for (const sec of schema.sections || []) {
    if (!shouldDisplaySection(sec, schema, model, linkageCtx)) continue
    const block: PrintSectionBlock = {
      title: sec.title || printT('print.section_default'),
      rows: [],
      details: [],
      textBlocks: [],
    }

    for (const field of sec.fields || []) {
      if (field.visible === false || field.printable === false) continue
      if (!shouldDisplayField(field, schema, model, linkageCtx)) continue
      if (!field.key && !['detail', 'text_block', 'section_title', 'divider', 'leave_calendar'].includes(field.type)) {
        continue
      }

      if (field.type === 'divider') continue

      if (field.type === 'leave_calendar') {
        block.details.push(await buildLeaveCalendarPrintTable(field, model, options))
        continue
      }

      if (field.type === 'section_title') {
        block.rows.push({ label: field.label, value: '', fullWidth: true })
        continue
      }

      if (field.type === 'text_block') continue

      if (field.type === 'detail') {
        const cols = ((field.props?.columns as FormFieldDef[]) || []).filter(
          (c) => c.key && c.printable !== false,
        )
        const rawRows = Array.isArray(model[field.key!]) ? (model[field.key!] as Record<string, unknown>[]) : []
        const table: PrintDetailTable = {
          title: field.label || printT('print.detail_default'),
          columns: cols.map((c) => ({ key: c.key, label: c.label || c.key })),
          rows: [],
          moneyColumnKeys: cols.filter((c) => isAmountSummaryFieldType(c.type)).map((c) => c.key),
        }
        for (const row of rawRows) {
          const out: Record<string, string> = {}
          for (const col of cols) {
            out[col.key] = await formatFieldValue(
              col,
              row[col.key],
              optionMap,
              userMap,
              deptMap,
              { moneyUppercase: false },
            )
          }
          table.rows.push(out)
        }
        if (field.props?.showSummary !== false) {
          const summary: PrintFieldRow[] = []
          for (const col of cols) {
            if (isAmountSummaryFieldType(col.type) && col.key) {
              let total = 0
              for (const row of rawRows) {
                total += getAmountColumnTotal(row[col.key], col.type)
              }
              if (total) {
                summary.push({
                  label: printT('print.detail_total', { label: col.label }),
                  value:
                    col.type === 'money'
                      ? formatMoneyPrint({ rmb_amount: total, amount: total, currency: 'CNY' })
                      : formatPlainAmountPrint(total, Number(col.props?.precision ?? 2)),
                  fullWidth: true,
                  alignRight: true,
                })
              }
            }
          }
          if (summary.length) table.summaryRows = summary
        }
        block.details.push(table)
        continue
      }

      if (!field.key) continue
      const value = await formatFieldValue(
        field,
        model[field.key],
        optionMap,
        userMap,
        deptMap,
      )
      block.rows.push({
        label: field.label || field.key,
        value,
        fullWidth: isPrintFullWidthField(field, gridCols),
        alignRight: field.type === 'money' || field.type === 'plain_amount',
      })
    }

    if (block.rows.length || block.details.length || block.textBlocks.length) {
      blocks.push(block)
    }
  }

  return blocks
}

/** 将字段行配对为双列表格行 */
export function pairPrintRows(rows: PrintFieldRow[]): { left?: PrintFieldRow; right?: PrintFieldRow }[] {
  const pairs: { left?: PrintFieldRow; right?: PrintFieldRow }[] = []
  let buf: PrintFieldRow | undefined
  for (const row of rows) {
    if (row.fullWidth) {
      if (buf) {
        pairs.push({ left: buf })
        buf = undefined
      }
      pairs.push({ left: row })
      continue
    }
    if (!buf) {
      buf = row
    } else {
      pairs.push({ left: buf, right: row })
      buf = undefined
    }
  }
  if (buf) pairs.push({ left: buf })
  return pairs
}
