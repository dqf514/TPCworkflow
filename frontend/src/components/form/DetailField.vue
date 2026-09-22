<template>
  <div class="detail-field" :class="{ 'detail-field--mobile': isMobileLayout }">
    <div v-if="!rows.length && readonly" class="detail-empty text-gray-500 text-sm">暂无明细</div>

    <!-- 手机端：卡片纵向布局，避免明细表横向滚动 -->
    <div v-else-if="isMobileLayout" class="detail-mobile-list">
      <div v-for="(row, ri) in rows" :key="ri" class="detail-mobile-card">
        <div class="detail-mobile-card-head">
          <span class="detail-mobile-index">第 {{ ri + 1 }} 行</span>
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
        <div v-for="col in columns" :key="col.id" class="detail-mobile-field">
          <label class="detail-mobile-label">
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

    <!-- 桌面端：表格布局 -->
    <div v-else class="detail-table-wrap">
      <table class="detail-table">
        <thead>
          <tr>
            <th v-for="col in columns" :key="col.id" class="detail-th">
              {{ col.label }}
              <span v-if="col.required" class="detail-req">*</span>
            </th>
            <th v-if="!readonly" class="detail-th detail-th-action">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ri) in rows" :key="ri" class="detail-tr">
            <td v-for="col in columns" :key="col.id" class="detail-td">
              <DetailCell
                :column="col"
                :columns="columns"
                :detail-key="detailKey"
                :row-index="ri"
                :model-value="row[col.key]"
                :readonly="readonly"
                inline
                @update:model-value="(v) => setCell(ri, col.key, v)"
                @fill-row="(patch) => applyRowPatch(ri, patch)"
              />
            </td>
            <td v-if="!readonly" class="detail-td detail-td-action">
              <a-button
                type="text"
                size="mini"
                status="danger"
                :disabled="rows.length <= 1"
                @click="removeRow(ri)"
              >
                删除
              </a-button>
            </td>
          </tr>
        </tbody>
      </table>
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { IconPlus } from '@arco-design/web-vue/es/icon'
import type { DeviceMode, FormFieldDef } from '@/types/form'
import { getAmountColumnTotal, createEmptyMoney, isAmountSummaryFieldType } from '@/composables/useMoneyField'
import { matchMobileViewport, MOBILE_MEDIA_QUERY, useBreakpoint } from '@/composables/useBreakpoint'
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

const { isMobile: viewportMobile } = useBreakpoint()
const screenMobile = ref(matchMobileViewport())

const isMobileLayout = computed(
  () => props.device === 'mobile' || screenMobile.value || viewportMobile.value,
)

onMounted(() => {
  ensureDefaultRow()
  const mq = window.matchMedia(MOBILE_MEDIA_QUERY)
  const sync = () => {
    screenMobile.value = mq.matches
  }
  sync()
  mq.addEventListener('change', sync)
  onBeforeUnmount(() => mq.removeEventListener('change', sync))
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

.detail-table-wrap {
  overflow-x: auto;
  max-width: 100%;
  border: 1px solid var(--border, #e6e9ef);
  border-radius: var(--radius-md, 12px);
  background: var(--surface, #fff);
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 640px;
}

@media (max-width: 1023px) {
  .detail-table {
    min-width: 0;
  }

  .detail-table-wrap {
    overflow-x: visible;
  }
}

.detail-th {
  padding: 8px 10px;
  font-size: 0.8125rem;
  font-weight: 600;
  text-align: left;
  background: var(--surface-muted, #f5f6f8);
  border-bottom: 1px solid var(--border, #e6e9ef);
  white-space: nowrap;
}

.detail-th-action {
  width: 56px;
  text-align: center;
}

.detail-req {
  color: #f53f3f;
  margin-left: 2px;
}

.detail-td {
  padding: 6px 8px;
  vertical-align: middle;
  border-bottom: 1px solid var(--border, #e6e9ef);
}

.detail-tr:last-child .detail-td {
  border-bottom: none;
}

.detail-td-action {
  text-align: center;
}

.detail-add-btn {
  margin-top: 8px;
}

.detail-summary {
  margin-top: 12px;
  padding: 10px 14px;
  background: var(--brand-soft, #f0ecff);
  border-radius: var(--radius-sm, 8px);
  border: 1px solid #e8e4ff;
}

.detail-summary-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9375rem;
}

.detail-summary-line + .detail-summary-line {
  margin-top: 6px;
}

.detail-summary-line strong {
  color: var(--brand, #5034ff);
  font-size: 1.05rem;
}

.detail-empty {
  padding: 8px 0;
}

/* 手机端卡片明细 */
.detail-mobile-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-mobile-card {
  border: 1px solid var(--border, #e6e9ef);
  border-radius: var(--radius-md, 12px);
  background: var(--surface, #fff);
  padding: 12px;
}

.detail-mobile-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--border, #e6e9ef);
}

.detail-mobile-index {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary, #676879);
}

.detail-mobile-field {
  margin-bottom: 12px;
}

.detail-mobile-field:last-child {
  margin-bottom: 0;
}

.detail-mobile-label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary, #676879);
}

.detail-field--mobile :deep(.detail-inline-att) {
  max-width: none;
  min-width: 0;
  width: 100%;
}

.detail-field--mobile :deep(.arco-input),
.detail-field--mobile :deep(.arco-select),
.detail-field--mobile :deep(.arco-picker),
.detail-field--mobile :deep(.arco-input-number),
.detail-field--mobile :deep(.arco-textarea) {
  width: 100%;
}

.detail-field--mobile :deep(.money-field .money-grid),
.detail-field--mobile :deep(.money-field--compact .money-grid) {
  display: grid !important;
  grid-template-columns: 1fr !important;
}

.detail-field--mobile :deep(.attachment-field),
.detail-field--mobile :deep(.arco-upload),
.detail-field--mobile :deep(.arco-upload-list),
.detail-field--mobile :deep(.arco-upload-list-item) {
  max-width: 100%;
  box-sizing: border-box;
}

.detail-field--mobile :deep(.arco-upload-list-item-name) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
