<template>
  <div class="record-set-field">
    <template v-if="!readonly">
      <div v-if="columns.length" class="record-edit">
        <a-row :gutter="rowGutter">
          <a-col v-for="c in columns" :key="c.field_key" :span="columnSpan(c)">
            <div class="record-field-item">
              <div class="record-edit-label">{{ c.label }}</div>
              <a-auto-complete
                v-if="isLabelColumn(c)"
                v-model="editData[c.field_key]"
                :data="autoOptions"
                :placeholder="labelFieldPlaceholder(c)"
                allow-clear
                class="w-full"
                @select="onAutoSelect"
                @clear="onClear"
                @blur="onLabelBlur"
                @input="onLabelInput"
              />
              <a-input
                v-else
                v-model="editData[c.field_key]"
                :placeholder="`请输入${c.label}`"
                allow-clear
                @input="onManualEdit"
              />
            </div>
          </a-col>
        </a-row>
        <p v-if="sourceHint" class="source-hint">{{ sourceHint }}</p>
        <div v-if="canSavePersonal" class="record-save-row">
          <a-button size="small" type="outline" :loading="savingPersonal" @click="savePersonal">
            保存到个人配置
          </a-button>
        </div>
      </div>
      <span v-else class="record-empty">—</span>
    </template>
    <template v-else>
      <div v-if="hasDisplayData && columns.length" class="record-detail">
        <a-row :gutter="rowGutter">
          <a-col v-for="c in columns" :key="c.field_key" :span="columnSpan(c)">
            <div class="record-detail-item">
              <div class="record-detail-label">{{ c.label }}</div>
              <div class="record-detail-value">{{ displayData[c.field_key] || '—' }}</div>
            </div>
          </a-col>
        </a-row>
      </div>
      <span v-else class="record-empty">—</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  clearRecordSetCache,
  loadRecordSetPayload,
  recordDisplayLabel,
  saveMyRecord,
  type RecordSetColumn,
  type RecordSetDataScope,
  type RecordSetRow,
  type RecordSetValue,
} from '@/composables/useRecordSets'
import type { DeviceMode } from '@/types/form'
import { recordSetColumnSpan } from '@/utils/recordSetLayout'

const props = withDefaults(
  defineProps<{
    modelValue?: RecordSetValue | null
    recordSetCode?: string
    labelField?: string
    showCompanyRecords?: boolean
    showPersonalRecords?: boolean
    readonly?: boolean
    device?: DeviceMode
  }>(),
  {
    showCompanyRecords: true,
    showPersonalRecords: true,
    readonly: false,
    device: 'desktop',
  },
)

const emit = defineEmits<{ 'update:modelValue': [RecordSetValue | null] }>()

const columns = ref<RecordSetColumn[]>([])
const records = ref<RecordSetRow[]>([])
const dataScope = ref<RecordSetDataScope>('mixed')
const editData = reactive<Record<string, string>>({})
const pickedRowCode = ref('')
const sourceKind = ref<'company' | 'personal' | 'custom' | ''>('')
const manualDirty = ref(false)
const savingPersonal = ref(false)

const labelKey = computed(() => {
  const lf = (props.labelField || '').trim()
  if (lf) return lf
  return columns.value[0]?.field_key || ''
})

const rowGutter = computed(() => (props.device === 'mobile' ? ([0, 8] as const) : ([12, 8] as const)))

function columnSpan(col: RecordSetColumn) {
  return recordSetColumnSpan(col, props.device)
}

function isLabelColumn(col: RecordSetColumn) {
  return !!labelKey.value && col.field_key === labelKey.value
}

function labelFieldPlaceholder(col: RecordSetColumn) {
  return `输入关键字筛选或选择${col.label}`
}

/** 下拉选中值必须用展示文本，不能用 row_code，否则 Arco 会把输入框写成 row_1 */
function optionSelectValue(r: RecordSetRow) {
  return formatOptionLabel(r)
}

function findRowBySelectValue(value: string) {
  const v = value.trim()
  if (!v) return undefined
  return records.value.find(
    (r) =>
      optionSelectValue(r) === v ||
      recordDisplayLabel(r, columns.value, props.labelField) === v ||
      r.row_code === v,
  )
}

const autoOptions = computed(() => {
  const lk = labelKey.value
  const q = lk ? String(editData[lk] || '').trim().toLowerCase() : ''
  let list = records.value
  if (q) {
    list = list.filter((r) => {
      const label = recordDisplayLabel(r, columns.value, props.labelField).toLowerCase()
      const blob = Object.values(r.data || {})
        .join(' ')
        .toLowerCase()
      return label.includes(q) || blob.includes(q) || r.row_code.toLowerCase().includes(q)
    })
  }
  return list.map((r) => ({
    value: optionSelectValue(r),
    label: formatOptionLabel(r),
  }))
})

const displayData = computed(() => props.modelValue?.data || editData)

const hasDisplayData = computed(() =>
  Object.values(displayData.value || {}).some((v) => String(v || '').trim()),
)

const allowPersonalSave = computed(
  () => dataScope.value !== 'company' && props.showPersonalRecords !== false,
)

const sourceHint = computed(() => {
  if (!manualDirty.value && !pickedRowCode.value) return ''
  if (!allowPersonalSave.value) {
    if (sourceKind.value === 'company') return '已选择公司配置'
    return '自定义内容仅用于本次申请，不会保存到个人配置'
  }
  if (sourceKind.value === 'company') return '已选择公司配置，修改后可保存到个人常用数据'
  if (sourceKind.value === 'personal') return '个人常用数据，修改后请点击保存'
  return '自定义内容，可点击「保存到个人配置」立即保存'
})

const canSavePersonal = computed(() => {
  if (props.readonly || !allowPersonalSave.value) return false
  if (!columns.value.length || !(props.recordSetCode || '').trim()) return false
  return Object.values(editData).some((v) => String(v || '').trim())
})

async function savePersonal() {
  const code = (props.recordSetCode || '').trim()
  if (!code) return
  const data: Record<string, string> = {}
  columns.value.forEach((c) => {
    data[c.field_key] = String(editData[c.field_key] || '').trim()
  })
  if (!Object.values(data).some(Boolean)) {
    Message.warning('请至少填写一个字段')
    return
  }
  savingPersonal.value = true
  try {
    const rowCode =
      sourceKind.value === 'personal' && pickedRowCode.value ? pickedRowCode.value : undefined
    const res = await saveMyRecord(code, { row_code: rowCode, data })
    if (!res.ok) {
      Message.error(res.message || '保存失败')
      return
    }
    clearRecordSetCache()
    Message.success('已保存到个人配置')
    manualDirty.value = false
    await load()
    const saved = res.data
    if (saved?.row_code) {
      const row = records.value.find((r) => r.row_code === saved.row_code)
      if (row) {
        applyRow(row)
      } else {
        pickedRowCode.value = saved.row_code
        sourceKind.value = 'personal'
        emitCurrent()
      }
    }
  } catch (e: unknown) {
    Message.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    savingPersonal.value = false
  }
}

function formatOptionLabel(r: RecordSetRow) {
  const base = recordDisplayLabel(r, columns.value, props.labelField)
  if (r.source === 'personal') return `${base}（个人）`
  return base
}

function syncEditFromValue(val: RecordSetValue | null | undefined) {
  pickedRowCode.value = val?.row_code || ''
  sourceKind.value = (val?.source as typeof sourceKind.value) || ''
  manualDirty.value = false

  let row =
    (pickedRowCode.value && records.value.find((r) => r.row_code === pickedRowCode.value)) ||
    undefined
  const lk = labelKey.value
  if (!row && lk && val?.data?.[lk]) {
    const text = String(val.data[lk])
    if (records.value.some((r) => r.row_code === text)) {
      row = records.value.find((r) => r.row_code === text)
      pickedRowCode.value = row?.row_code || ''
    }
  }

  const keys = columns.value.map((c) => c.field_key)
  if (row) {
    keys.forEach((k) => {
      editData[k] = String(row!.data?.[k] || '')
    })
    return
  }

  keys.forEach((k) => {
    editData[k] = val?.data?.[k] != null ? String(val.data[k]) : ''
  })
}

function emitCurrent() {
  const data: Record<string, string> = {}
  columns.value.forEach((c) => {
    data[c.field_key] = String(editData[c.field_key] || '').trim()
  })
  if (!Object.values(data).some(Boolean)) {
    emit('update:modelValue', null)
    return
  }
  let rowCode = pickedRowCode.value
  let source: RecordSetValue['source'] = sourceKind.value || 'custom'
  if (manualDirty.value) {
    const match = records.value.find((r) =>
      columns.value.every((c) => String(r.data?.[c.field_key] || '').trim() === data[c.field_key]),
    )
    if (match) {
      rowCode = match.row_code
      source = match.source === 'personal' ? 'personal' : 'company'
    } else {
      if (!rowCode || source === 'company') {
        source = 'custom'
      }
    }
  }
  emit('update:modelValue', { row_code: rowCode || '', data, source })
}

function applyRow(row: RecordSetRow) {
  columns.value.forEach((c) => {
    editData[c.field_key] = String(row.data?.[c.field_key] || '')
  })
  pickedRowCode.value = row.row_code
  sourceKind.value = row.source === 'personal' ? 'personal' : 'company'
  manualDirty.value = false
  emitCurrent()
}

function onAutoSelect(value: string) {
  const row = findRowBySelectValue(value)
  if (row) applyRow(row)
}

function onClear() {
  columns.value.forEach((c) => {
    editData[c.field_key] = ''
  })
  pickedRowCode.value = ''
  sourceKind.value = ''
  manualDirty.value = false
  emit('update:modelValue', null)
}

function onManualEdit() {
  manualDirty.value = true
  if (sourceKind.value === 'company') {
    sourceKind.value = 'custom'
    pickedRowCode.value = ''
  }
  emitCurrent()
}

function onLabelInput() {
  onManualEdit()
}

function onLabelBlur() {
  const lk = labelKey.value
  if (!lk) return
  const q = String(editData[lk] || '').trim()
  if (!q) return
  const matched = findRowBySelectValue(q)
  if (matched && !manualDirty.value) {
    applyRow(matched)
    return
  }
  manualDirty.value = true
  sourceKind.value = 'custom'
  pickedRowCode.value = ''
  emitCurrent()
}

async function load() {
  const code = (props.recordSetCode || '').trim()
  if (!code) {
    columns.value = []
    records.value = []
    return
  }
  try {
    const payload = await loadRecordSetPayload(code, {
      includeCompany: props.showCompanyRecords !== false,
      includePersonal: props.showPersonalRecords !== false,
    })
    if (payload) {
      columns.value = payload.columns || []
      records.value = payload.records || []
      dataScope.value = payload.data_scope || 'mixed'
      syncEditFromValue(props.modelValue)
    }
  } catch {
    /* 加载失败时保持空态 */
  }
}

watch(
  () => [props.recordSetCode, props.showCompanyRecords, props.showPersonalRecords],
  () => {
    void load()
  },
)

watch(
  () => props.modelValue,
  (v) => {
    if (!manualDirty.value) syncEditFromValue(v)
  },
  { deep: true },
)

/** 组件有时在 @select 之后仍把 v-model 写成 row_code，此处纠正 */
watch(
  () => (labelKey.value ? editData[labelKey.value] : ''),
  (q) => {
    if (!q || manualDirty.value) return
    const row = records.value.find((r) => r.row_code === q)
    if (row) applyRow(row)
  },
)

onMounted(() => {
  void load()
})
</script>

<style scoped>
.record-set-field {
  width: 100%;
}

.record-edit {
  padding: 12px 14px;
  background: #fafbfc;
  border-radius: 8px;
  border: 1px solid #e5e6eb;
}

.record-field-item {
  min-width: 0;
}

.record-edit-label {
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #646a73;
}

.source-hint {
  margin: 8px 0 0;
  font-size: 13px;
  color: #646a73;
  line-height: 1.5;
}

.record-save-row {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

.record-detail {
  padding: 12px 14px;
  background: #fafbfc;
  border-radius: 8px;
  border: 1px solid #e5e6eb;
}

.record-detail-item {
  min-width: 0;
  font-size: 14px;
  line-height: 1.5715;
}

.record-detail-label {
  color: #646a73;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
}

.record-detail-value {
  color: #1f2329;
  word-break: break-all;
  line-height: 1.5715;
}

.record-empty {
  color: var(--text-tertiary, #9699a6);
}
</style>
