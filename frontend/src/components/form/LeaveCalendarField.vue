<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import zhCnLocale from '@fullcalendar/core/locales/zh-cn'
import enGbLocale from '@fullcalendar/core/locales/en-gb'
import type { CalendarOptions, DayCellContentArg, EventClickArg, EventHoveringArg, EventInput } from '@fullcalendar/core'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const props = withDefaults(
  defineProps<{
    companyId?: number
    departmentId?: number
    formKeys?: string[]
    periodFieldKeys?: string[]
    leaveTypeFieldKey?: string
    includeRunning?: boolean
    showReason?: boolean
    height?: number
    preview?: boolean
  }>(),
  {
    formKeys: () => ['auto'],
    periodFieldKeys: () => ['leave_period', 'date_range'],
    leaveTypeFieldKey: 'leave_type',
    includeRunning: false,
    showReason: true,
    height: 560,
    preview: false,
  },
)

const { t, locale } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const rangeHint = ref('')
const reloadToken = ref(0)
const canViewAll = ref(false)
const holidayRegionName = ref('')
const holidaySource = ref<'company' | 'user' | 'preview'>('company')

const tipVisible = ref(false)
const tipText = ref('')
const tipX = ref(0)
const tipY = ref(0)
const isZh = computed(() => String(locale.value).toLowerCase().startsWith('zh'))
const fcLocale = computed(() => (isZh.value ? zhCnLocale : enGbLocale))

interface HolidayMark {
  date: string
  kind: 'holiday' | 'weekend' | 'makeup'
  name: string
  name_en?: string
}

const holidayMarks = ref<Record<string, HolidayMark>>({})

interface LeaveEventRow {
  id: string
  public_uuid: string
  title: string
  tooltip?: string
  start: string
  end: string
  color?: string
  user_id?: number
  user_name?: string
  leave_type?: string
  leave_type_label?: string
  form_key?: string
  form_name?: string
  field_key?: string
  field_label?: string
  department_name?: string
  reason?: string
  status?: string
  display_no?: string
}

function trOr(key: string, fallback: string) {
  const text = String(t(key) || '').trim()
  if (!text || text === key) return fallback
  return text
}

function localizeUserName(name?: string, userId?: number) {
  const raw = String(name || '').trim()
  if (raw.startsWith('用户#')) {
    return t('leave_calendar.user_fallback', { id: raw.slice(3) })
  }
  if (raw) return raw
  if (userId) return t('leave_calendar.user_fallback', { id: userId })
  return ''
}

function localizeLeaveType(code?: string, fallback?: string) {
  const key = String(code || '').trim()
  if (key) {
    const labeled = trOr(`leave_calendar.leave_type.${key}`, '')
    if (labeled) return labeled
  }
  return String(fallback || key || '').trim()
}

function localizeFormName(formKey?: string, fallback?: string) {
  const key = String(formKey || '').trim()
  if (key) {
    const labeled = trOr(`leave_calendar.form.${key}`, '')
    if (labeled) return labeled
  }
  return String(fallback || key || '').trim()
}

function localizeFieldLabel(fieldKey?: string, fallback?: string) {
  const key = String(fieldKey || '').trim()
  if (key) {
    const labeled = trOr(`leave_calendar.field.${key}`, '')
    if (labeled) return labeled
  }
  return String(fallback || key || '').trim()
}

function formatCalendarTitle(row: Pick<
  LeaveEventRow,
  'user_id' | 'user_name' | 'leave_type' | 'leave_type_label' | 'form_key' | 'form_name' | 'field_key' | 'field_label'
>) {
  const userName = localizeUserName(row.user_name, row.user_id)
  const typeLabel = localizeLeaveType(row.leave_type, row.leave_type_label)
  const formName = localizeFormName(row.form_key, row.form_name)
  const fieldLabel = localizeFieldLabel(row.field_key, row.field_label)
  const fieldKey = String(row.field_key || '')
  const isLeavePeriod = fieldKey === 'leave_period' || fieldKey === 'date_range'
  const parts = typeLabel && isLeavePeriod
    ? [userName, typeLabel, formName || fieldLabel]
    : [userName, formName || row.form_key, fieldLabel]
  return parts.filter(Boolean).join(' · ')
}

function formatCalendarTooltip(row: LeaveEventRow) {
  const title = formatCalendarTitle(row)
  const lines = [title]
  const reason = String(row.reason || '').trim()
  if (reason) lines.push(reason)
  const displayNo = String(row.display_no || '').trim()
  if (displayNo) lines.push(t('leave_calendar.ticket_no', { no: displayNo }))
  return lines.join('\n')
}

function toQueryCsv(values: string[] | undefined, fallback: string) {
  const list = (values || []).map((v) => v.trim()).filter(Boolean)
  return list.length ? list.join(',') : fallback
}

function exclusiveEndToInclusive(endExclusive: string) {
  const endDate = new Date(`${endExclusive.slice(0, 10)}T00:00:00`)
  endDate.setDate(endDate.getDate() - 1)
  const y = endDate.getFullYear()
  const m = String(endDate.getMonth() + 1).padStart(2, '0')
  const d = String(endDate.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function toYmd(raw: Date | string) {
  if (raw instanceof Date) {
    const y = raw.getFullYear()
    const m = String(raw.getMonth() + 1).padStart(2, '0')
    const d = String(raw.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }
  return String(raw || '').slice(0, 10)
}

function escapeHtml(text: string) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function markLabel(mark?: HolidayMark) {
  if (!mark) return ''
  return isZh.value ? mark.name : (mark.name_en || mark.name)
}

function applyHolidayMarks(marks: HolidayMark[], regionName: string, source: 'company' | 'user' | 'preview') {
  const map: Record<string, HolidayMark> = {}
  for (const row of marks) {
    if (row?.date) map[row.date] = row
  }
  holidayMarks.value = map
  holidayRegionName.value = regionName
  holidaySource.value = source
}

async function loadHolidayMarks(from: string, to: string) {
  if (props.preview) {
    applyHolidayMarks(
      [
        { date: from, kind: 'holiday', name: '国庆节', name_en: 'National Day' },
        { date: to, kind: 'weekend', name: '周日', name_en: 'Sunday' },
      ],
      isZh.value ? '中国大陆' : 'Chinese Mainland',
      'preview',
    )
    return
  }
  try {
    const res = await api.get<
      ApiResponse<{
        marks?: HolidayMark[]
        region_name?: string
        region_name_en?: string
        source?: string
      }>
    >('/holidays/calendar', {
      params: {
        from,
        to,
        company_id: props.companyId || undefined,
        user_id: auth.user?.id || undefined,
      },
    })
    const data = res.data.data
    const name = isZh.value ? (data?.region_name || '') : (data?.region_name_en || data?.region_name || '')
    applyHolidayMarks(
      data?.marks || [],
      name,
      data?.source === 'user' ? 'user' : 'company',
    )
  } catch {
    holidayMarks.value = {}
  }
}

async function fetchEvents(from: string, to: string): Promise<EventInput[]> {
  if (props.preview) {
    rangeHint.value = t('leave_calendar.hint_preview', { from, to })
    await loadHolidayMarks(from, to)
    const start = from
    const endDate = new Date(`${from}T00:00:00`)
    endDate.setDate(endDate.getDate() + 3)
    const y = endDate.getFullYear()
    const m = String(endDate.getMonth() + 1).padStart(2, '0')
    const d = String(endDate.getDate()).padStart(2, '0')
    const title1 = t('leave_calendar.preview_title_1')
    const title2 = t('leave_calendar.preview_title_2')
    return [
      {
        id: 'preview-1',
        title: title1,
        start,
        end: `${y}-${m}-${d}`,
        backgroundColor: '#0f9d58',
        borderColor: '#0f9d58',
        allDay: true,
        extendedProps: { tooltip: `${title1}\n${t('leave_calendar.preview_tip_1')}` },
      },
      {
        id: 'preview-2',
        title: title2,
        start: from,
        end: `${y}-${m}-${d}`,
        backgroundColor: '#3b82f6',
        borderColor: '#3b82f6',
        allDay: true,
        extendedProps: { tooltip: `${title2}\n${t('leave_calendar.preview_tip_2')}` },
      },
    ]
  }

  loading.value = true
  try {
    const eventsReq = api.get<
      ApiResponse<{ events: LeaveEventRow[]; count: number; can_view_all?: boolean }>
    >('/leave-calendar/events', {
      params: {
        from,
        to,
        company_id: props.companyId || undefined,
        department_id: props.departmentId || undefined,
        form_keys: toQueryCsv(props.formKeys, 'auto'),
        period_field_keys: toQueryCsv(props.periodFieldKeys, 'leave_period,date_range'),
        leave_type_field_key: props.leaveTypeFieldKey || 'leave_type',
        include_running: props.includeRunning ? '1' : '0',
        show_reason: props.showReason ? '1' : '0',
        _t: reloadToken.value,
      },
    })
    const [res] = await Promise.all([eventsReq, loadHolidayMarks(from, to)])
    if (!res.data.ok) {
      throw new Error(t('leave_calendar.load_failed'))
    }
    const rows = res.data.data?.events || []
    canViewAll.value = !!res.data.data?.can_view_all
    const scope = canViewAll.value
      ? t('leave_calendar.scope_all')
      : t('leave_calendar.scope_related')
    rangeHint.value = t('leave_calendar.hint', { from, to, n: rows.length, scope })
    return rows.map((row: LeaveEventRow) => ({
      id: row.id,
      title: formatCalendarTitle(row),
      start: row.start,
      end: row.end,
      allDay: true,
      backgroundColor: row.color,
      borderColor: row.color,
      textColor: '#fff',
      extendedProps: { ...row, tooltip: formatCalendarTooltip(row) },
    }))
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('leave_calendar.load_failed'))
    return []
  } finally {
    loading.value = false
  }
}

function onEventClick(info: EventClickArg) {
  if (props.preview) return
  tipVisible.value = false
  const uuid = String(info.event.extendedProps?.public_uuid || '')
  if (!uuid) return
  void router.push({ name: 'instance-detail', params: { uuid } })
}

function onEventMouseEnter(info: EventHoveringArg) {
  const tip =
    String(info.event.extendedProps?.tooltip || info.event.title || '').trim()
  if (!tip) return
  tipText.value = tip
  const jsEvent = info.jsEvent
  tipX.value = jsEvent.clientX + 12
  tipY.value = jsEvent.clientY + 12
  tipVisible.value = true
}

function onEventMouseLeave() {
  tipVisible.value = false
}

function dayCellClassNames(arg: { date: Date }) {
  const mark = holidayMarks.value[toYmd(arg.date)]
  if (mark?.kind === 'holiday') return ['cal-cell-holiday']
  if (mark?.kind === 'makeup') return ['cal-cell-makeup']
  if (mark?.kind === 'weekend') return ['cal-cell-weekend']
  return []
}

function dayCellContent(arg: DayCellContentArg) {
  const mark = holidayMarks.value[toYmd(arg.date)]
  const num = String(arg.dayNumberText || '').replace(/[日号]/g, '')
  const tag = markLabel(mark)
  const kind = mark?.kind || ''
  return {
    html: `<div class="cal-day-head"${kind ? ` data-kind="${kind}"` : ''}>`
      + `<span class="cal-day-num">${escapeHtml(num)}</span>`
      + (tag ? `<span class="cal-day-tag">${escapeHtml(tag)}</span>` : '')
      + '</div>',
  }
}

const calendarOptions = computed<CalendarOptions>(() => ({
  plugins: [dayGridPlugin],
  initialView: 'dayGridMonth',
  locale: fcLocale.value,
  firstDay: 1,
  height: props.height,
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: '',
  },
  buttonText: {
    today: t('leave_calendar.today'),
  },
  editable: false,
  selectable: false,
  dayMaxEventRows: 4,
  moreLinkText: (n) => t('leave_calendar.more', { n }),
  eventDisplay: 'block',
  displayEventTime: false,
  eventOrder: 'start,-duration,title',
  dayCellClassNames,
  dayCellContent,
  eventClick: onEventClick,
  eventMouseEnter: onEventMouseEnter,
  eventMouseLeave: onEventMouseLeave,
  eventDidMount: (info) => {
    const tip = String(info.event.extendedProps?.tooltip || info.event.title || '')
    if (tip) info.el.setAttribute('title', tip.replace(/\n/g, ' | '))
  },
  events: (fetchInfo, successCallback, failureCallback) => {
    const from = fetchInfo.startStr.slice(0, 10)
    const to = exclusiveEndToInclusive(fetchInfo.endStr)
    void fetchEvents(from, to)
      .then((list) => successCallback(list))
      .catch((err) => failureCallback(err instanceof Error ? err : new Error(String(err))))
  },
}))

const calendarKey = computed(
  () =>
    [
      locale.value,
      props.companyId || 0,
      props.departmentId || 0,
      (props.formKeys || []).join(','),
      (props.periodFieldKeys || []).join(','),
      props.leaveTypeFieldKey,
      props.includeRunning ? 1 : 0,
      props.showReason ? 1 : 0,
      props.height,
      reloadToken.value,
    ].join('|'),
)

onBeforeUnmount(() => {
  tipVisible.value = false
})
</script>

<template>
  <div class="leave-calendar-field" :class="{ 'is-preview': preview }">
    <div v-if="loading" class="leave-calendar-loading">{{ t('leave_calendar.loading') }}</div>
    <div class="leave-calendar-meta">
      <p v-if="rangeHint" class="leave-calendar-hint">{{ rangeHint }}</p>
      <div class="cal-legend" :aria-label="t('leave_calendar.legend_title')">
        <span class="cal-legend-item is-holiday">{{ t('leave_calendar.legend_holiday') }}</span>
        <span class="cal-legend-item is-weekend">{{ t('leave_calendar.legend_weekend') }}</span>
        <span class="cal-legend-item is-makeup">{{ t('leave_calendar.legend_makeup') }}</span>
        <span v-if="holidayRegionName" class="cal-legend-region">
          {{ t('leave_calendar.holiday_region', { name: holidayRegionName }) }}
          <template v-if="holidaySource === 'user'"> · {{ t('leave_calendar.holiday_source_user') }}</template>
          <template v-else-if="holidaySource === 'company'"> · {{ t('leave_calendar.holiday_source_company') }}</template>
        </span>
      </div>
    </div>
    <FullCalendar :key="calendarKey" :options="calendarOptions" />
    <Teleport to="body">
      <div
        v-show="tipVisible"
        class="leave-calendar-tooltip"
        :style="{ left: `${tipX}px`, top: `${tipY}px` }"
      >
        <pre>{{ tipText }}</pre>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.leave-calendar-field {
  width: 100%;
  min-height: 280px;
  position: relative;
  background: #fff;
  border: 1px solid var(--color-border-2, #e5e6eb);
  border-radius: 8px;
  padding: 8px 10px 12px;
}

.leave-calendar-field.is-preview {
  pointer-events: none;
  opacity: 0.92;
}

.leave-calendar-loading {
  position: absolute;
  z-index: 2;
  top: 12px;
  right: 16px;
  font-size: 12px;
  color: var(--color-text-3, #86909c);
}

.leave-calendar-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 16px;
  margin-bottom: 10px;
}

.leave-calendar-hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-3, #86909c);
}

.cal-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 14px;
  font-size: 12px;
  color: var(--color-text-2, #4e5969);
}

.cal-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.cal-legend-item::before {
  content: '';
  width: 10px;
  height: 10px;
  border-radius: 2px;
  box-sizing: border-box;
}

.cal-legend-item.is-holiday::before {
  background: #fda29b;
  box-shadow: inset 0 0 0 1px #f04438;
}

.cal-legend-item.is-weekend::before {
  background: #eaecf0;
  box-shadow: inset 0 0 0 1px #98a2b3;
}

.cal-legend-item.is-makeup::before {
  background: #fedf89;
  box-shadow: inset 0 0 0 1px #f79009;
}

.cal-legend-region {
  color: var(--color-text-3, #86909c);
  font-weight: 500;
}

.leave-calendar-field :deep(.fc) {
  font-family: 'Noto Sans SC', 'Source Han Sans SC', 'PingFang SC', 'Microsoft YaHei',
    'WenQuanYi Micro Hei', 'DejaVu Sans', sans-serif;
  --fc-border-color: #eaecf0;
  --fc-today-bg-color: #eff6ff;
}

.leave-calendar-field :deep(.fc-toolbar) {
  margin-bottom: 10px;
}

.leave-calendar-field :deep(.fc-toolbar-title) {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: #1d2129;
}

.leave-calendar-field :deep(.fc-button) {
  font-weight: 600;
  border-radius: 6px !important;
  box-shadow: none !important;
}

.leave-calendar-field :deep(.fc-col-header-cell) {
  background: #f8fafc;
  padding: 8px 0;
}

.leave-calendar-field :deep(.fc-col-header-cell-cushion) {
  font-size: 12px;
  font-weight: 700;
  color: #475467;
  text-transform: none;
}

.leave-calendar-field :deep(.fc-daygrid-day-frame) {
  min-height: 112px;
  padding: 0;
}

.leave-calendar-field :deep(.fc-daygrid-day-top) {
  flex-direction: column;
  align-items: stretch;
  padding: 6px 7px 2px;
}

.leave-calendar-field :deep(.cal-day-head) {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 6px;
  min-height: 28px;
}

.leave-calendar-field :deep(.cal-day-num) {
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #1d2129;
  line-height: 1.2;
  min-width: 1.25em;
}

.leave-calendar-field :deep(.cal-day-tag) {
  flex: 1;
  text-align: right;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.25;
  max-width: 72%;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.leave-calendar-field :deep(.cal-cell-holiday .fc-daygrid-day-frame) {
  background: linear-gradient(180deg, #fff5f4 0%, #fff 58%);
  box-shadow: inset 3px 0 0 #f04438;
}

.leave-calendar-field :deep(.cal-cell-holiday .cal-day-tag) {
  color: #b42318;
}

.leave-calendar-field :deep(.cal-cell-weekend .fc-daygrid-day-frame) {
  background: #f8fafc;
}

.leave-calendar-field :deep(.cal-cell-weekend .cal-day-num),
.leave-calendar-field :deep(.cal-cell-weekend .cal-day-tag) {
  color: #667085;
}

.leave-calendar-field :deep(.cal-cell-makeup .fc-daygrid-day-frame) {
  background: linear-gradient(180deg, #fffaeb 0%, #fff 58%);
  box-shadow: inset 3px 0 0 #f79009;
}

.leave-calendar-field :deep(.cal-cell-makeup .cal-day-tag) {
  color: #b54708;
}

.leave-calendar-field :deep(.fc-day-today .fc-daygrid-day-frame) {
  box-shadow: inset 0 0 0 2px #2f6fed;
}

.leave-calendar-field :deep(.fc-day-today.cal-cell-holiday .fc-daygrid-day-frame) {
  box-shadow: inset 3px 0 0 #f04438, inset 0 0 0 2px #2f6fed;
}

.leave-calendar-field :deep(.fc-day-today.cal-cell-makeup .fc-daygrid-day-frame) {
  box-shadow: inset 3px 0 0 #f79009, inset 0 0 0 2px #2f6fed;
}

.leave-calendar-field :deep(.fc-day-other .fc-daygrid-day-frame) {
  opacity: 0.58;
}

.leave-calendar-field :deep(.fc-daygrid-day-events) {
  margin-top: 2px;
  padding: 0 3px 4px;
}

.leave-calendar-field :deep(.fc-daygrid-event) {
  margin: 1px 2px !important;
}

.leave-calendar-field :deep(.fc-event) {
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
  border-radius: 4px;
  padding: 2px 6px;
  border-width: 0;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.12);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.leave-calendar-field :deep(.fc-event:hover) {
  filter: brightness(1.06);
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.18);
}

.leave-calendar-field :deep(.fc-daygrid-event-dot) {
  display: none;
}

.leave-calendar-field :deep(.fc-daygrid-more-link) {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-2, #4e5969);
  margin: 2px 4px;
}
</style>

<style>
.leave-calendar-tooltip {
  position: fixed;
  z-index: 4000;
  max-width: 320px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(29, 33, 41, 0.94);
  color: #fff;
  font-size: 13px;
  line-height: 1.5;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  pointer-events: none;
  white-space: pre-wrap;
  word-break: break-word;
}

.leave-calendar-tooltip pre {
  margin: 0;
  font-family: inherit;
  white-space: pre-wrap;
}
</style>
