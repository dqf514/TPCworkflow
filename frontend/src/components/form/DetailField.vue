<template>
  <div class="detail-field" :class="{ 'detail-field--readonly': readonly }">
    <div v-if="!rows.length && readonly" class="detail-empty">暂无明细</div>

    <div v-else class="detail-rows">
      <div v-for="(row, ri) in rows" :key="ri" class="detail-row">
        <div v-if="!readonly || rows.length > 1" class="detail-row-head">
          <span class="detail-row-index">第 {{ ri + 1 }} 行</span>
          <a-button
            v-if="!readonly"
            type="text"
            size="mini"
            status="danger"
            :disabled="rows.length <= 1"
            @click="removeRow(ri)"
          >
            删除
          </a-button>
        </div>

        <div class="detail-row-grid">
          <div
            v-for="col in columns"
            :key="col.id"
            class="detail-cell"
            :class="{ 'detail-cell--wide': isWideColumn(col) }"
          >
            <label class="detail-cell-label">
              {{ col.label }}
              <span v-if="col.required" class="detail-req">*</span>
            </label>
            <DetailCell
              :column="col"
              :columns="columns"
              :detail-key="detailKey"
              :row-index="ri"
              :model-value="row[col.key]"
              :readonly="readonly"
              :inline="false"
              @update:model-value="(v) => setCell(ri, col.key, v)"
              @fill-row="(patch) => applyRowPatch(ri, patch)"
            />
          </div>
        </div>
      </div>
    </div>

    <a-button
      v-if="!readonly && rows.length < maxRows"
      type="dashed"
      long
      class="detail-add-btn"
      @click="addRow"
    >
      <icon-plus /> 添加一行
    </a-button>

    <div v-if="showSummary && moneySummary.length" class="detail-summary">
      <div v-for="s in moneySummary" :key="s.key" class="detail-summary-line">
        <span>{{ s.label }} 合计</span>
        <strong>¥ {{ formatMoney(s.total) }}</strong>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { IconPlus } from '@arco-design/web-vue/es/icon'
import type { DeviceMode, FormFieldDef } from '@/types/form'
import { getAmountColumnTotal, createEmptyMoney, isAmountSummaryFieldType } from '@/composables/useMoneyField'
import DetailCell from '@/components/form/DetailCell.vue'

const props = withDefaults(
  defineProps<{
    columns: FormFieldDef[]
    modelValue?: Record<string, unknown>[]
    readonly?: boolean
    device?: DeviceMode
    showSummary?: boolean
    maxRows?: number
    detailKey?: string
    schema?: import('@/types/form').FormSchema
  }>(),
  { modelValue: () => [], readonly: false, device: 'desktop', showSummary: true, maxRows: 50, detailKey: '' },
)

const emit = defineEmits<{ 'update:modelValue': [Record<string, unknown>[]] }>()

onMounted(() => {
  ensureDefaultRow()
})

const rows = computed({
  get: () => (Array.isArray(props.modelValue) ? props.modelValue : []),
  set: (v) => emit('update:modelValue', v),
})

const columns = computed(() => props.columns || [])

const moneySummary = computed(() => {
  const list: { key: string; label: string; total: number }[] = []
  for (const col of columns.value) {
    if (!isAmountSummaryFieldType(col.type) || !col.key) continue
    let total = 0
    for (const row of rows.value) {
      total += getAmountColumnTotal(row[col.key], col.type)
    }
    list.push({ key: col.key, label: col.label || col.key, total })
  }
  return list
})

function newRow(): Record<string, unknown> {
  const r: Record<string, unknown> = {}
  for (const col of columns.value) {
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

function ensureDefaultRow() {
  if (props.readonly || rows.value.length > 0) return
  rows.value = [newRow()]
}

function addRow() {
  rows.value = [...rows.value, newRow()]
}

function removeRow(ri: number) {
  if (rows.value.length <= 1) return
  const next = [...rows.value]
  next.splice(ri, 1)
  rows.value = next
}

function setCell(ri: number, key: string, val: unknown) {
  const next = rows.value.map((r, i) => (i === ri ? { ...r, [key]: val } : r))
  rows.value = next
}

function applyRowPatch(ri: number, patch: Record<string, unknown>) {
  const next = rows.value.map((r, i) => (i === ri ? { ...r, ...patch } : r))
  rows.value = next
}

function isWideColumn(col: FormFieldDef) {
  return col.type === 'textarea' || col.type === 'attachment' || col.type === 'image'
}

function formatMoney(n: number) {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

watch(
  () => [props.columns, props.readonly],
  () => ensureDefaultRow(),
  { deep: true },
)
</script>

<style scoped>
.detail-field {
  width: 100%;
  min-width: 0;
  max-width: 100%;
}

.detail-rows {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-row {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
}

.detail-field--readonly .detail-row {
  padding: 14px;
  background: var(--surface-muted);
  border-color: transparent;
}

.detail-row-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--border);
}

.detail-row-index {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.detail-row-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 160px), 1fr));
  gap: 10px 14px;
}

.detail-cell {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 5px;
}

.detail-cell-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary);
  line-height: 1.35;
}

.detail-req {
  margin-left: 2px;
  color: var(--danger);
}

.detail-add-btn {
  margin-top: 10px;
}

.detail-summary {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px 22px;
  margin-top: 12px;
  padding: 10px 14px;
  border: 1px solid #e6e0ff;
  border-radius: var(--radius-md);
  background: var(--brand-softer);
}

.detail-summary-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.detail-summary-line strong {
  color: var(--brand);
  font-size: 0.9375rem;
  font-variant-numeric: tabular-nums;
}

.detail-empty {
  padding: 10px 0;
  font-size: var(--app-font-sm);
  color: var(--text-tertiary);
}

@media (min-width: 768px) {
  .detail-cell--wide {
    grid-column: span 2;
  }
}

.detail-field :deep(.arco-input-wrapper),
.detail-field :deep(.arco-select-view),
.detail-field :deep(.arco-picker),
.detail-field :deep(.arco-input-number) {
  width: 100%;
}

.detail-field :deep(.arco-upload-list-item-name) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-field--readonly :deep(.arco-input-wrapper[readonly]),
.detail-field--readonly :deep(.arco-input[readonly]) {
  background: transparent;
  border-color: transparent;
  padding-left: 0;
}
</style>
