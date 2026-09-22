<template>
  <div class="form-renderer" :class="[`device-${device}`, { 'is-readonly': readonly, 'is-print': printMode }]">
    <div v-if="printMode && schema.print?.showTitle !== false" class="print-head">
      <h1>{{ schema.title }}</h1>
      <p v-if="schema.print?.showDescription === true && schema.description">{{ schema.description }}</p>
      <div v-if="printMeta" class="print-meta text-sm text-gray-600">
        <span v-if="schema.print?.showInitiator !== false && printMeta.initiator">
          申请人：{{ printMeta.initiator }}
        </span>
        <span v-if="schema.print?.showCompany !== false && printMeta.company" class="ml-4">
          公司：{{ printMeta.company }}
        </span>
        <span v-if="schema.print?.showPrintTime !== false" class="ml-4">打印时间：{{ printMeta.time }}</span>
      </div>
    </div>

    <a-form :model="model" layout="vertical">
      <div
        v-for="sec in schema.sections"
        v-show="shouldShowSection(sec)"
        :key="sec.id"
        class="form-section"
      >
        <div v-if="sec.title" class="section-title">{{ sec.title }}</div>
        <a-row :gutter="rowGutter">
          <template v-for="field in visibleFields(sec)" :key="field.id">
            <a-col v-if="shouldShow(field)" :span="colSpan(field)">
              <template v-if="field.type === 'divider'">
                <a-divider />
              </template>
              <template v-else-if="field.type === 'text_block'">
                <div class="text-gray-600 text-sm mb-3">{{ field.props?.content }}</div>
              </template>
              <template v-else-if="field.type === 'section_title'">
                <div class="font-semibold text-base mb-2">{{ field.label }}</div>
              </template>
              <template v-else-if="field.type === 'leave_calendar'">
                <div class="leave-calendar-wrap mb-3">
                  <div v-if="field.label" class="font-medium text-sm mb-2">{{ field.label }}</div>
                  <LeaveCalendarField
                    :company-id="companyId"
                    :department-id="applyDepartmentId"
                    :form-keys="(field.props?.formKeys as string[]) || undefined"
                    :period-field-keys="(field.props?.periodFieldKeys as string[]) || undefined"
                    :leave-type-field-key="String(field.props?.leaveTypeFieldKey || 'leave_type')"
                    :include-running="field.props?.includeRunning === true"
                    :show-reason="field.props?.showReason === true"
                    :height="Number(field.props?.height || 520)"
                  />
                </div>
              </template>
              <a-form-item
                v-else
                :label="field.label"
                :required="isFieldRequired(field)"
                :extra="field.description"
              >
                <a-input
                  v-if="field.type === 'formula'"
                  :model-value="formulaDisplayValue(field)"
                  readonly
                  :placeholder="field.placeholder || '自动计算'"
                />
                <a-input
                  v-else-if="field.type === 'input' || field.type === 'serial_no'"
                  v-model="model[field.key]"
                  :placeholder="field.type === 'serial_no' ? (field.placeholder || '提交后自动生成') : field.placeholder"
                  :readonly="isFieldReadonly(field)"
                  allow-clear
                />
                <a-textarea
                  v-else-if="field.type === 'textarea'"
                  v-model="model[field.key]"
                  :placeholder="field.placeholder"
                  :readonly="isFieldReadonly(field)"
                  :auto-size="{ minRows: 3 }"
                />
                <a-input-number
                  v-else-if="field.type === 'number'"
                  v-model="model[field.key]"
                  :disabled="isFieldReadonly(field) || isAutoDaysTarget(field)"
                  :step="numberStep(field)"
                  :precision="numberPrecision(field)"
                  :placeholder="field.placeholder"
                  class="w-full"
                />
                <MoneyField
                  v-else-if="field.type === 'money'"
                  :model-value="model[field.key]"
                  :readonly="isFieldReadonly(field)"
                  :compact="device === 'mobile'"
                  @update:model-value="(v) => { model[field.key] = v }"
                />
                <PlainAmountField
                  v-else-if="field.type === 'plain_amount'"
                  :model-value="model[field.key]"
                  :readonly="isFieldReadonly(field)"
                  :precision="Number(field.props?.precision ?? 2)"
                  size="small"
                  @update:model-value="(v) => { model[field.key] = v }"
                />
                <span
                  v-else-if="isFieldReadonly(field) && isTemporalField(field.type)"
                  class="form-readonly-value"
                >{{ formatTemporalFieldValue(field, model[field.key]) }}</span>
                <a-date-picker
                  v-else-if="field.type === 'date'"
                  v-model="model[field.key]"
                  class="w-full"
                />
                <a-date-picker
                  v-else-if="field.type === 'datetime'"
                  v-model="model[field.key]"
                  show-time
                  class="w-full"
                />
                <a-time-picker
                  v-else-if="field.type === 'time'"
                  v-model="model[field.key]"
                  class="w-full"
                />
                <DateRangeField
                  v-else-if="field.type === 'date_range'"
                  :model-value="model[field.key]"
                  :half-day="fieldUsesHalfDay(field)"
                  :count-workdays="fieldCountsWorkdays(field)"
                  :off-days="holidayOffDays"
                  :makeup-workdays="holidayMakeupWorkdays"
                  :region-name="holidayRegionName"
                  :readonly="isFieldReadonly(field)"
                  @update:model-value="(v) => onDateRangeChange(field, v)"
                />
                <span
                  v-else-if="isFieldReadonly(field) && isOptionField(field.type)"
                  class="form-readonly-value"
                >{{ optionDisplayLabel(field, model[field.key]) }}</span>
                <a-select
                  v-else-if="field.type === 'select'"
                  v-model="model[field.key]"
                  :options="optionList(field)"
                  :disabled="isFieldReadonly(field)"
                  allow-clear
                  :placeholder="field.placeholder"
                />
                <a-select
                  v-else-if="field.type === 'multi_select'"
                  v-model="model[field.key]"
                  :options="optionList(field)"
                  :disabled="isFieldReadonly(field)"
                  multiple
                  allow-clear
                />
                <a-radio-group
                  v-else-if="field.type === 'radio'"
                  v-model="model[field.key]"
                  :options="optionList(field)"
                  :disabled="isFieldReadonly(field)"
                />
                <a-checkbox-group
                  v-else-if="field.type === 'checkbox_group'"
                  v-model="model[field.key]"
                  :options="optionList(field)"
                  :disabled="isFieldReadonly(field)"
                />
                <a-switch
                  v-else-if="field.type === 'switch'"
                  v-model="model[field.key]"
                  :disabled="isFieldReadonly(field)"
                />
                <a-input
                  v-else-if="field.type === 'phone'"
                  v-model="model[field.key]"
                  :readonly="isFieldReadonly(field)"
                />
                <a-input
                  v-else-if="field.type === 'email'"
                  v-model="model[field.key]"
                  type="email"
                  :placeholder="field.placeholder || '请输入有效邮箱地址，如 name@example.com'"
                  :readonly="isFieldReadonly(field)"
                />
                <a-input
                  v-else-if="field.type === 'location'"
                  v-model="model[field.key]"
                  :readonly="isFieldReadonly(field)"
                />
                <a-select
                  v-else-if="field.type === 'user_picker'"
                  v-model="model[field.key]"
                  :options="userOpts"
                  :disabled="isFieldReadonly(field)"
                  :multiple="isPickerMultiple(field)"
                  allow-search
                  allow-clear
                  :max-tag-count="isPickerMultiple(field) ? 3 : undefined"
                />
                <a-select
                  v-else-if="field.type === 'dept_picker'"
                  v-model="model[field.key]"
                  :options="deptOpts"
                  :disabled="isFieldReadonly(field)"
                  :multiple="isPickerMultiple(field)"
                  allow-search
                  allow-clear
                  :placeholder="field.placeholder || '请选择部门'"
                  :max-tag-count="isPickerMultiple(field) ? 3 : undefined"
                />
                <a-select
                  v-else-if="field.type === 'contact'"
                  v-model="model[field.key]"
                  :options="userOpts"
                  :disabled="isFieldReadonly(field)"
                  allow-search
                  allow-clear
                  :placeholder="field.placeholder || '请选择联系人'"
                />
                <AttachmentField
                  v-else-if="field.type === 'attachment' || field.type === 'image'"
                  :model-value="(model[field.key] as AttachmentFileItem[] | undefined)"
                  :readonly="isFieldReadonly(field)"
                  :image-only="field.type === 'image'"
                  :max-count="Number(field.props?.maxCount) || 20"
                  :field-label="field.label"
                  @update:model-value="(v) => { model[field.key] = v }"
                />
                <SmartReceiptField
                  v-else-if="field.type === 'smart_receipt'"
                  :model-value="(model[field.key] as AttachmentFileItem[] | undefined)"
                  :readonly="isFieldReadonly(field)"
                  :accept="String(field.props?.accept || '')"
                  :max-count="Number(field.props?.maxCount) || 20"
                  :field-label="field.label"
                  :recognition="(field.props?.recognition as import('@/constants/receiptExtractKeys').SmartReceiptRecognitionConfig)"
                  :schema="schema"
                  @update:model-value="(v) => { model[field.key] = v }"
                  @filled="emitModel"
                />
                <DetailField
                  v-else-if="field.type === 'detail'"
                  :columns="detailColumns(field)"
                  :detail-key="field.key"
                  :schema="schema"
                  :model-value="detailRows(field.key)"
                  :readonly="isFieldReadonly(field)"
                  :device="device"
                  :show-summary="field.props?.showSummary !== false"
                  :max-rows="Number(field.props?.maxRows) || 50"
                  @update:model-value="(v) => setDetailRows(field.key, v)"
                />
                <RecordSetField
                  v-else-if="field.type === 'record_set'"
                  :model-value="(model[field.key] as import('@/composables/useRecordSets').RecordSetValue | null)"
                  :record-set-code="String(field.props?.recordSetCode || '')"
                  :label-field="String(field.props?.labelField || '')"
                  :show-company-records="field.props?.showCompanyRecords !== false"
                  :show-personal-records="field.props?.showPersonalRecords !== false"
                  :readonly="isFieldReadonly(field)"
                  :device="device"
                  :placeholder="field.placeholder || '输入关键字筛选或选择'"
                  @update:model-value="(v) => { model[field.key] = v }"
                />
                <RelatedFormField
                  v-else-if="field.type === 'related_form'"
                  :model-value="model[field.key] as RelatedFormValue | RelatedFormValue[] | null"
                  :related-form-keys="schema.settings?.relatedFormKeys || []"
                  :multiple="!!field.props?.multiple"
                  :readonly="isFieldReadonly(field)"
                  @update:model-value="(v) => { model[field.key] = v }"
                />
                <a-input v-else v-model="model[field.key]" :readonly="isFieldReadonly(field)" />
              </a-form-item>
            </a-col>
          </template>
        </a-row>
      </div>
    </a-form>

    <div v-if="printMode && schema.print?.showApprovalHistory !== false && timeline?.length" class="print-timeline mt-6">
      <h3 class="font-semibold mb-2">审批记录</h3>
      <table class="w-full text-sm border-collapse">
        <thead>
          <tr class="border-b">
            <th class="text-left py-1">操作</th>
            <th class="text-left py-1">意见</th>
            <th class="text-left py-1">时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in timeline" :key="t.id" class="border-b">
            <td class="py-1">{{ t.action }}</td>
            <td class="py-1">{{ t.comment }}</td>
            <td class="py-1">{{ formatDateTime(t.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <AttachmentPreviewPanel />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, provide, reactive, ref, watch } from 'vue'
import { api, type ApiResponse } from '@/api/client'
import LeaveCalendarField from '@/components/form/LeaveCalendarField.vue'
import DateRangeField from '@/components/form/DateRangeField.vue'
import { loadFormFillerContext, type FormFillerContext } from '@/composables/useFormFillerDefaults'
import {
  collectDeptIdsFromModel,
  loadCompanyDeptOptions,
  resolveDepartmentLabels,
} from '@/composables/useOrgDeptOptions'
import AttachmentField, { type AttachmentFileItem } from '@/components/form/AttachmentField.vue'
import AttachmentPreviewPanel from '@/components/form/AttachmentPreviewPanel.vue'
import SmartReceiptField from '@/components/form/SmartReceiptField.vue'
import DetailField from '@/components/form/DetailField.vue'
import MoneyField from '@/components/form/MoneyField.vue'
import PlainAmountField from '@/components/form/PlainAmountField.vue'
import RelatedFormField from '@/components/form/RelatedFormField.vue'
import RecordSetField from '@/components/form/RecordSetField.vue'
import { resolveFieldOptions, resolveOptionLabel, type FieldOptionItem } from '@/composables/useFieldOptions'
import type {
  DeviceMode,
  FormFieldDef,
  FormSchema,
  FormSection,
  RelatedFormValue,
} from '@/types/form'
import { createEmptyMoney } from '@/composables/useMoneyField'
import { syncFormFormulas } from '@/composables/useFormFormula'
import {
  buildLinkageContext,
  clearHiddenFieldValues,
  shouldDisplayField,
  shouldDisplaySection,
} from '@/composables/useFieldLinkage'
import { getSpan, isDetailRowArray } from '@/types/form'
import { formatDate, formatDateTime } from '@/utils/dateTime'
import {
  autoDaysKeyOf,
  buildDateRangeValue,
  formatDateRangeDisplay,
  numberFieldKeysFromSchema,
  parseDateRange,
  usesCountWorkdays,
  usesHalfDay,
} from '@/utils/dateRangeValue'
import { useHolidayCalendar } from '@/composables/useHolidayCalendar'

const props = withDefaults(
  defineProps<{
    schema: FormSchema
    modelValue?: Record<string, unknown>
    device?: DeviceMode
    readonly?: boolean
    /** 按字段 key 控制：hidden 不展示，read 只读，edit 可编辑 */
    fieldPermissions?: Record<string, 'hidden' | 'read' | 'edit'>
    /** 本节点可编辑字段必填 */
    fieldNodeRequired?: Record<string, boolean>
    /** 本节点可编辑字段须修改 */
    fieldMustModify?: Record<string, boolean>
    /** 发起公司 ID，用于部门下拉与默认主部门 */
    companyId?: number
    /** 申请人用户 ID，用于按员工假期地区计算工作日 */
    holidayUserId?: number
    /** 填表时应用「默认本人/主部门」等选项 */
    applyFillerDefaults?: boolean
    /** 发起页顶部所选申请部门，联动表单内费用承担等部门字段 */
    applyDepartmentId?: number
    /** 草稿/再次提交时排除自身实例，避免误判重复 */
    excludeInstanceRef?: string
    printMode?: boolean
    printMeta?: { initiator?: string; company?: string; time?: string }
    timeline?: { id: number; action: string; comment: string; created_at: string }[]
  }>(),
  {
    device: 'desktop',
    readonly: false,
    printMode: false,
    applyFillerDefaults: false,
  },
)

const emit = defineEmits<{ 'update:modelValue': [Record<string, unknown>] }>()

const model = reactive<Record<string, unknown>>({ ...(props.modelValue || {}) })
const userOpts = ref<{ label: string; value: number }[]>([])
const deptOpts = ref<{ label: string; value: number }[]>([])
const fillerContext = ref<FormFillerContext>({ departmentIds: [] })
const fieldOptionsMap = ref<Record<string, FieldOptionItem[]>>({})

const linkageCtx = computed(() => buildLinkageContext(props.schema))
const {
  offDays: holidayOffDays,
  makeupWorkdays: holidayMakeupWorkdays,
  regionName: holidayRegionName,
  loaded: holidayLoaded,
} = useHolidayCalendar(() => props.companyId, () => props.holidayUserId)

provide('formPickerContext', {
  userOpts,
  deptOpts,
  fillerContext,
  applyFillerDefaults: () => props.applyFillerDefaults,
  isPickerMultiple: (field: FormFieldDef) => !!field.props?.multiple,
})

provide('smartReceiptFormModel', model)
provide('formSchema', props.schema)
provide(
  'formApplyContext',
  computed(() => ({
    companyId: props.companyId,
    excludeInstanceRef: props.excludeInstanceRef,
  })),
)

function emitModel() {
  emit('update:modelValue', { ...model })
}

const gutter = computed(() => props.schema.layout?.gutter ?? 12)
const rowGutter = computed(() => (props.device === 'mobile' ? 0 : gutter.value))

function visibleFields(sec: FormSection) {
  return (sec.fields || []).filter((f) => f.visible !== false)
}

function fieldPerm(key: string | undefined): 'hidden' | 'read' | 'edit' | undefined {
  if (!key || !props.fieldPermissions) return undefined
  return props.fieldPermissions[key]
}

function shouldShowSection(sec: FormSection) {
  return shouldDisplaySection(sec, props.schema, model, linkageCtx.value)
}

function shouldShow(field: FormFieldDef) {
  return shouldDisplayField(field, props.schema, model, linkageCtx.value, {
    printMode: props.printMode,
    fieldPerm: fieldPerm(field.key),
  })
}

function isPickerMultiple(field: FormFieldDef) {
  return !!field.props?.multiple
}

function hasFieldValue(key: string) {
  const v = model[key]
  if (v === undefined || v === null || v === '') return false
  if (Array.isArray(v) && v.length === 0) return false
  return true
}

function deptPickerSyncsWithApplyHeader(field: FormFieldDef) {
  return (
    field.type === 'dept_picker' &&
    (field.props?.syncApplyOrg === true || field.props?.defaultPrimaryDept === true)
  )
}

function resolveApplyDepartmentId() {
  if (props.applyDepartmentId) return props.applyDepartmentId
  return fillerContext.value.primaryDepartmentId
}

function applyFillerDefaultForField(field: FormFieldDef, forceApplyDept = false) {
  if (!props.applyFillerDefaults || props.readonly || !field.key) return
  const multiple = isPickerMultiple(field)
  if (field.type === 'user_picker' && field.props?.defaultSelf && fillerContext.value.userId) {
    if (hasFieldValue(field.key) && !forceApplyDept) return
    model[field.key] = multiple
      ? [fillerContext.value.userId]
      : fillerContext.value.userId
    return
  }
  if (deptPickerSyncsWithApplyHeader(field)) {
    const deptId = resolveApplyDepartmentId()
    if (!deptId) return
    if (hasFieldValue(field.key) && !forceApplyDept && !props.applyDepartmentId) return
    model[field.key] = multiple ? [deptId] : deptId
  }
}

function syncApplyDepartmentFields() {
  if (!props.applyFillerDefaults || props.readonly || !props.applyDepartmentId) return
  for (const sec of props.schema.sections || []) {
    for (const field of sec.fields || []) {
      if (deptPickerSyncsWithApplyHeader(field)) {
        applyFillerDefaultForField(field, true)
      }
      if (field.type === 'detail') {
        for (const col of (field.props?.columns as FormFieldDef[]) || []) {
          if (deptPickerSyncsWithApplyHeader(col)) {
            applyFillerDefaultForField(col, true)
          }
        }
      }
    }
  }
  emit('update:modelValue', { ...model })
}

function applyAllFillerDefaults() {
  for (const sec of props.schema.sections || []) {
    for (const field of sec.fields || []) {
      applyFillerDefaultForField(field)
      if (field.type === 'detail') {
        for (const col of (field.props?.columns as FormFieldDef[]) || []) {
          applyFillerDefaultForField(col)
        }
      }
    }
  }
}

function isTemporalField(type: string) {
  return type === 'date' || type === 'datetime' || type === 'time' || type === 'date_range'
}

function schemaNumberKeys() {
  return numberFieldKeysFromSchema(props.schema)
}

function fieldUsesHalfDay(field: FormFieldDef) {
  return usesHalfDay(field, schemaNumberKeys())
}

function fieldCountsWorkdays(field: FormFieldDef) {
  return usesCountWorkdays(field, schemaNumberKeys())
}

function autoDaysKey(field: FormFieldDef) {
  return autoDaysKeyOf(field, schemaNumberKeys())
}

function isAutoDaysTarget(field: FormFieldDef) {
  if (field.type !== 'number' || !field.key) return false
  for (const sec of props.schema.sections || []) {
    for (const f of sec.fields || []) {
      if (f.type === 'date_range' && autoDaysKey(f) === field.key) return true
    }
  }
  return false
}

function numberStep(field: FormFieldDef) {
  const step = Number(field.props?.step)
  if (Number.isFinite(step) && step > 0) return step
  return isAutoDaysTarget(field) ? 0.5 : 1
}

function numberPrecision(field: FormFieldDef) {
  const precision = Number(field.props?.precision)
  if (Number.isFinite(precision) && precision >= 0) return precision
  return isAutoDaysTarget(field) ? 1 : undefined
}

function onDateRangeChange(field: FormFieldDef, val: unknown) {
  if (!field.key) return
  model[field.key] = val
  const daysKey = autoDaysKey(field)
  if (!daysKey) return
  const days =
    val && typeof val === 'object' && !Array.isArray(val)
      ? (val as { days?: number }).days
      : undefined
  model[daysKey] = days ?? null
}

function formatTemporalFieldValue(field: FormFieldDef, raw: unknown): string {
  if (raw == null || raw === '') return '—'
  if (field.type === 'date') return formatDate(String(raw))
  if (field.type === 'datetime' || field.type === 'time') return formatDateTime(String(raw))
  if (field.type === 'date_range') {
    const text = formatDateRangeDisplay(
      raw,
      {
        am: '上午',
        pm: '下午',
        sep: '至',
        days: (n) => `（${n} 天）`,
      },
      fieldUsesHalfDay(field),
    )
    return text || '—'
  }
  return String(raw)
}

function isFieldReadonly(field: FormFieldDef) {
  if (field.type === 'formula' || field.type === 'serial_no') return true
  if (field.readonly) return true
  if (props.readonly) return true
  const p = fieldPerm(field.key)
  if (p === 'edit') return false
  if (p === 'read' || p === 'hidden') return true
  return props.readonly
}

function isFieldRequired(field: FormFieldDef) {
  if (field.required) return true
  const key = field.key
  if (!key || fieldPerm(key) !== 'edit') return false
  return !!props.fieldNodeRequired?.[key]
}

function detailColumns(field: FormFieldDef) {
  const cols = (field.props?.columns as FormFieldDef[]) || []
  return cols.map((col) => ({
    ...col,
    required: !!col.required || isFieldRequired(col),
  }))
}

function colSpan(field: FormFieldDef) {
  if (props.device === 'mobile' || props.printMode) return 24
  if (field.type === 'detail' || field.type === 'related_form') return 24
  return getSpan(field, props.device)
}

function optionList(field: FormFieldDef) {
  const cached = fieldOptionsMap.value[field.id]
  if (cached?.length) return cached.map((o) => ({ label: o.label, value: o.value }))
  const opts = (field.props?.options as FieldOptionItem[]) || []
  return opts.map((o) => ({ label: o.label || o.name || o.value, value: o.value }))
}

const OPTION_FIELD_TYPES = new Set(['select', 'multi_select', 'radio', 'checkbox_group'])

function isOptionField(type: string) {
  return OPTION_FIELD_TYPES.has(type)
}

function optionDisplayLabel(field: FormFieldDef, raw: unknown) {
  const opts = fieldOptionsMap.value[field.id] || []
  return resolveOptionLabel(raw, opts)
}

async function preloadFieldOptions() {
  const map: Record<string, FieldOptionItem[]> = {}
  for (const sec of props.schema.sections || []) {
    for (const field of sec.fields || []) {
      if (['select', 'multi_select', 'radio', 'checkbox_group'].includes(field.type)) {
        map[field.id] = await resolveFieldOptions(field)
      }
      if (field.type === 'detail') {
        for (const col of (field.props?.columns as FormFieldDef[]) || []) {
          if (['select', 'multi_select', 'radio', 'checkbox_group'].includes(col.type)) {
            map[col.id] = await resolveFieldOptions(col)
          }
        }
      }
    }
  }
  fieldOptionsMap.value = map
}

function detailRows(key: string) {
  const v = model[key]
  if (isDetailRowArray(v)) return v
  return []
}

function setDetailRows(key: string, rows: Record<string, unknown>[]) {
  model[key] = rows
}

function createDetailRow(field: FormFieldDef): Record<string, unknown> {
  const r: Record<string, unknown> = {}
  for (const col of (field.props?.columns as FormFieldDef[]) || []) {
    if (!col.key) continue
    if (col.type === 'money') {
      r[col.key] = col.defaultValue ?? createEmptyMoney()
    } else if (col.type === 'plain_amount') {
      r[col.key] = col.defaultValue ?? null
    } else if (col.type === 'attachment' || col.type === 'image') {
      r[col.key] = col.defaultValue ?? []
    } else {
      r[col.key] = col.defaultValue ?? undefined
    }
  }
  return r
}

function ensureModelDefaults() {
  for (const sec of props.schema.sections || []) {
    for (const field of sec.fields || []) {
      if (!field.key) continue
      if (field.type === 'detail') {
        if (!isDetailRowArray(model[field.key])) {
          model[field.key] = props.readonly ? [] : [createDetailRow(field)]
        } else if (!props.readonly && model[field.key].length === 0) {
          model[field.key] = [createDetailRow(field)]
        }
      }
      if (field.type === 'attachment' || field.type === 'image' || field.type === 'smart_receipt') {
        if (!Array.isArray(model[field.key])) {
          model[field.key] = []
        }
      }
      if (field.type === 'related_form' && model[field.key] === undefined) {
        model[field.key] = field.props?.multiple ? [] : null
      }
      if (field.type === 'record_set' && model[field.key] === undefined) {
        model[field.key] = null
      }
      if (field.type === 'user_picker' && isPickerMultiple(field) && !Array.isArray(model[field.key])) {
        model[field.key] = hasFieldValue(field.key) ? [model[field.key]] : []
      }
      if (field.type === 'dept_picker' && isPickerMultiple(field) && !Array.isArray(model[field.key])) {
        model[field.key] = hasFieldValue(field.key) ? [model[field.key]] : []
      }
      if (field.type === 'date_range' && model[field.key] != null && model[field.key] !== '') {
        const raw = model[field.key]
        const parsed = parseDateRange(raw)
        if (parsed) {
          const built = buildDateRangeValue(parsed.start, parsed.end, {
            halfDay: fieldUsesHalfDay(field),
            startHalf: parsed.startHalf,
            endHalf: parsed.endHalf,
            countWorkdays: fieldCountsWorkdays(field),
            offDays: holidayOffDays.value,
            makeupWorkdays: holidayMakeupWorkdays.value,
          })
          const storedDays =
            typeof raw === 'object' && raw !== null && !Array.isArray(raw)
              ? (raw as { days?: number }).days
              : undefined
          const needsNormalize =
            Array.isArray(raw) ||
            storedDays == null ||
            (built != null && storedDays !== built.days)
          if (built && needsNormalize) {
            model[field.key] = built
          }
          const daysKey = autoDaysKey(field)
          const daysVal = built?.days
          if (daysKey && daysVal != null && model[daysKey] !== daysVal) {
            if (model[daysKey] == null || model[daysKey] === '' || holidayLoaded.value) {
              model[daysKey] = daysVal
            }
          }
        }
      }
    }
  }
}

async function enrichDeptOptsFromModel() {
  const ids = collectDeptIdsFromModel(props.schema, model)
  const known = new Set(deptOpts.value.map((o) => o.value))
  const missing = ids.filter((id) => !known.has(id))
  if (!missing.length) return
  const extra = await resolveDepartmentLabels(missing)
  if (extra.length) {
    deptOpts.value = [...deptOpts.value, ...extra.filter((o) => !known.has(o.value))]
  }
}

async function reloadPickerData() {
  const res = await api.get<ApiResponse<{ id: number; display_name: string }[]>>('/workflow/users/options')
  if (res.data.ok) {
    userOpts.value = res.data.data.map((u) => ({ label: u.display_name, value: u.id }))
  }
  if (props.companyId) {
    deptOpts.value = await loadCompanyDeptOptions(props.companyId)
  } else {
    deptOpts.value = []
  }
  await enrichDeptOptsFromModel()
  if (props.applyFillerDefaults) {
    fillerContext.value = await loadFormFillerContext(props.companyId)
    applyAllFillerDefaults()
    syncApplyDepartmentFields()
  }
}

function formulaDisplayValue(field: FormFieldDef) {
  if (!field.key) return ''
  const v = model[field.key]
  if (v == null || v === '') return ''
  return String(v)
}

function recalcFormulas() {
  syncFormFormulas(props.schema, model)
}

watch(
  model,
  () => {
    clearHiddenFieldValues(props.schema, model, linkageCtx.value)
    recalcFormulas()
    emit('update:modelValue', { ...model })
  },
  { deep: true },
)

watch(
  () => props.applyDepartmentId,
  () => {
    syncApplyDepartmentFields()
  },
)

watch(
  () => props.modelValue,
  async (v) => {
    if (v) Object.assign(model, v)
    ensureModelDefaults()
    recalcFormulas()
    await enrichDeptOptsFromModel()
  },
  { deep: true },
)

onMounted(async () => {
  ensureModelDefaults()
  recalcFormulas()
  await preloadFieldOptions()
  await reloadPickerData()
})

watch(
  () => [props.companyId, props.applyFillerDefaults, props.schema],
  async () => {
    ensureModelDefaults()
    await reloadPickerData()
  },
  { deep: true },
)

watch(
  () => [holidayLoaded.value, holidayOffDays.value.join(','), holidayMakeupWorkdays.value.join(',')].join('|'),
  () => {
    if (props.readonly) return
    ensureModelDefaults()
  },
)

watch(
  () => props.schema,
  async () => {
    ensureModelDefaults()
    await preloadFieldOptions()
  },
  { deep: true },
)
</script>

<style scoped>
.form-renderer {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  overflow-x: clip;
}

.form-renderer.device-mobile :deep(.arco-row) {
  margin-left: 0 !important;
  margin-right: 0 !important;
}

.form-renderer.device-mobile :deep(.arco-col) {
  flex: 0 0 100%;
  max-width: 100%;
  padding-left: 0 !important;
  padding-right: 0 !important;
}

.form-renderer.device-mobile :deep(.money-field .money-grid) {
  grid-template-columns: 1fr;
}

.form-renderer.device-mobile :deep(.money-field--inline .money-grid) {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.form-renderer.device-mobile :deep(.money-field--inline .money-label) {
  display: block;
}

.form-renderer.device-mobile :deep(.record-set-field .arco-row) {
  margin-left: 0 !important;
  margin-right: 0 !important;
}

.form-renderer.device-mobile :deep(.smart-receipt-field),
.form-renderer.device-mobile :deep(.attachment-field),
.form-renderer.device-mobile :deep(.detail-field) {
  min-width: 0;
  max-width: 100%;
}

.form-renderer.device-mobile :deep(.arco-upload),
.form-renderer.device-mobile :deep(.arco-upload-list),
.form-renderer.device-mobile :deep(.arco-upload-list-item) {
  max-width: 100%;
  box-sizing: border-box;
}

.form-renderer.device-mobile :deep(.arco-upload-list-item-content) {
  overflow: hidden;
  min-width: 0;
}

.form-renderer.device-mobile :deep(.arco-upload-list-item-name) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.form-renderer.device-mobile :deep(.arco-form-item-extra),
.form-renderer.device-mobile :deep(.arco-form-item-label) {
  word-break: break-word;
}

.form-renderer.is-print {
  padding: 12px;
  background: #fff;
}

.print-head h1 {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0 0 8px;
}

.section-title {
  font-weight: 600;
  font-size: var(--app-font-base, 16px);
  margin-bottom: 10px;
}

@media print {
  .form-renderer.is-print {
    padding: 0;
  }
}
</style>
