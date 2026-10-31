<template>
  <div class="wf-instance-list">
    <div v-if="isDesktop && columnSettingsKey" class="wf-il-toolbar">
      <a-popover trigger="click" position="br" :content-style="{ padding: '12px 14px' }">
        <a-button size="mini" type="text" class="wf-il-col-btn">
          <template #icon><icon-settings /></template>
          {{ t('workflow.columns') }}
        </a-button>
        <template #content>
          <div class="wf-il-col-panel">
            <div class="wf-il-col-title">{{ t('workflow.columns') }}</div>
            <a-checkbox
              v-for="choice in columnChoices"
              :key="choice.key"
              :model-value="cols[choice.key]"
              class="wf-il-col-check"
              @change="(value: boolean) => setColumnVisible(choice.key, value)"
            >
              {{ choice.label }}
            </a-checkbox>
            <div class="wf-il-col-foot">
              <span class="wf-il-col-hint">{{ t('workflow.columns_hint') }}</span>
              <a-button size="mini" type="text" @click="resetColumns">{{ t('workflow.columns_reset') }}</a-button>
            </div>
          </div>
        </template>
      </a-popover>
    </div>
    <a-table
      v-if="isDesktop"
      v-model:selected-keys="selectedKeysModel"
      :data="rows"
      :loading="loading"
      :row-key="rowKey"
      :pagination="pagination"
      :bordered="bordered"
      :row-selection="rowSelection"
      :scroll="tableScroll"
      :row-class="rowClass"
      table-layout-fixed
      @page-change="(p: number) => emit('page-change', p)"
      @page-size-change="(s: number) => emit('page-size-change', s)"
      @sorter-change="onSorterChange"
      @row-click="(record: WorkflowInstanceListRow) => emit('row-click', record)"
    >
      <template #columns>
        <a-table-column
          v-if="cols.displayNo"
          :title="t('settings.instances_col_no')"
          data-index="display_no"
          :width="150"
          :sortable="sortable ? { sortDirections: ['ascend', 'descend'] } : undefined"
          :sort-order="sortOrderFor('display_no')"
        >
          <template #cell="{ record }">
            <span class="wf-il-no">
              <slot name="display-no-prefix" :record="record" />
              <span class="wf-il-no-text">{{ record.display_no || `#${record.id}` }}</span>
            </span>
          </template>
        </a-table-column>

        <a-table-column
          v-if="cols.flow"
          :title="t('workflow.col_flow')"
          data-index="definition_name"
          :width="190"
          :ellipsis="true"
          :tooltip="true"
          :sortable="sortable ? { sortDirections: ['ascend', 'descend'] } : undefined"
          :sort-order="sortOrderFor('definition_name')"
        >
          <template #cell="{ record }">
            <div class="wf-il-flow">
              <span class="wf-il-flow-name">{{ record.definition_name || '—' }}</span>
              <slot name="flow-extra" :record="record" />
            </div>
          </template>
        </a-table-column>

        <a-table-column
          v-if="cols.sector"
          :title="t('workflow.col_sector')"
          data-index="business_sector_name"
          :width="96"
          :ellipsis="true"
          :tooltip="true"
          :sortable="sortable ? { sortDirections: ['ascend', 'descend'] } : undefined"
          :sort-order="sortOrderFor('business_sector_name')"
        />

        <a-table-column
          v-if="cols.amount"
          :title="t('workflow.col_amount')"
          data-index="total_amount"
          :width="112"
          align="right"
          :sortable="sortable ? { sortDirections: ['ascend', 'descend'] } : undefined"
          :sort-order="sortOrderFor('total_amount')"
        >
          <template #cell="{ record }">
            <span class="wf-il-amount">
              {{ formatInstanceListAmount(record.total_amount, record.amount_currency) }}
            </span>
          </template>
        </a-table-column>

        <a-table-column
          v-if="cols.status"
          :title="t('workflow.col_status')"
          data-index="status"
          :width="120"
          :ellipsis="true"
          :tooltip="true"
          :sortable="sortable ? { sortDirections: ['ascend', 'descend'] } : undefined"
          :sort-order="sortOrderFor('status')"
        >
          <template #cell="{ record }">
            <StatusPill :status="record.status" :label="displayStatus(record)" />
          </template>
        </a-table-column>

        <a-table-column
          v-if="cols.applicant"
          :title="t('workflow.col_applicant')"
          data-index="initiator_name"
          :width="96"
          :ellipsis="true"
          :tooltip="true"
          :sortable="sortable ? { sortDirections: ['ascend', 'descend'] } : undefined"
          :sort-order="sortOrderFor('initiator_name')"
        />

        <a-table-column
          v-if="cols.department"
          :title="t('workflow.col_department')"
          data-index="department_name"
          :width="160"
          :ellipsis="true"
          :tooltip="true"
          :sortable="sortable ? { sortDirections: ['ascend', 'descend'] } : undefined"
          :sort-order="sortOrderFor('department_name')"
        />

        <a-table-column
          v-if="cols.submittedAt"
          :title="submittedAtTitle"
          data-index="started_at"
          :width="158"
          :sortable="sortable ? { sortDirections: ['ascend', 'descend'] } : undefined"
          :sort-order="sortOrderFor('started_at')"
        >
          <template #cell="{ record }">{{ formatDateTime(record.started_at) }}</template>
        </a-table-column>

        <a-table-column
          v-if="cols.updatedAt"
          :title="updatedAtTitle"
          data-index="updated_at"
          :width="158"
          :sortable="sortable ? { sortDirections: ['ascend', 'descend'] } : undefined"
          :sort-order="sortOrderFor('updated_at')"
        >
          <template #cell="{ record }">{{ formatDateTime(record.updated_at) }}</template>
        </a-table-column>

        <a-table-column
          v-if="cols.finishedAt"
          :title="t('workflow.col_finished_at')"
          data-index="finished_at"
          :width="158"
          :sortable="sortable ? { sortDirections: ['ascend', 'descend'] } : undefined"
          :sort-order="sortOrderFor('finished_at')"
        >
          <template #cell="{ record }">{{ formatDateTime(record.finished_at) }}</template>
        </a-table-column>

        <slot name="extra-columns" />

        <a-table-column
          v-if="cols.actions"
          :title="t('settings.col_actions')"
          :width="actionsWidth"
          align="right"
          :fixed="actionsFixed"
        >
          <template #cell="{ record }">
            <slot name="actions" :record="record" />
          </template>
        </a-table-column>
      </template>
    </a-table>

    <div v-else class="wf-il-mobile safe-bottom">
      <div v-if="loading" class="wf-il-mobile-skeleton" aria-hidden="true">
        <div v-for="n in 3" :key="`wf-il-sk-${n}`" class="wf-il-mobile-card wf-il-mobile-card--skeleton">
          <span class="skeleton wf-il-sk-line wf-il-sk-line--no" />
          <span class="skeleton wf-il-sk-line wf-il-sk-line--title" />
          <span class="skeleton wf-il-sk-line wf-il-sk-line--meta" />
        </div>
      </div>
      <template v-else>
        <a-card
          v-for="record in rows"
          :key="String(record[rowKey as keyof WorkflowInstanceListRow] ?? record.id)"
          class="wf-il-mobile-card app-card-hover"
          :class="mobileCardClass?.(record)"
          :bordered="false"
          @click="emit('row-click', record)"
        >
          <div class="wf-il-mobile-head">
            <span class="wf-il-mobile-no">
              <a-checkbox
                v-if="rowSelection"
                :model-value="isSelected(record)"
                class="wf-il-mobile-check"
                @click.stop
                @change="(checked: boolean) => toggleSelect(record, checked)"
              />
              <slot name="display-no-prefix" :record="record" />
              {{ record.display_no || `#${record.id}` }}
            </span>
            <a-space wrap size="mini">
              <slot name="flow-extra" :record="record" />
              <StatusPill v-if="cols.status" :status="record.status" :label="displayStatus(record)" />
            </a-space>
          </div>
          <div v-if="cols.flow" class="wf-il-mobile-title">{{ record.definition_name || '—' }}</div>
          <div v-if="cols.amount && record.total_amount != null" class="wf-il-mobile-amount">
            金额：{{ formatInstanceListAmount(record.total_amount, record.amount_currency) }}
          </div>
          <div class="wf-il-mobile-meta">
            <span v-if="cols.sector && record.business_sector_name">
              {{ record.business_sector_name }}
            </span>
            <span v-if="cols.applicant && record.initiator_name">
              <template v-if="cols.sector && record.business_sector_name"> · </template>
              {{ record.initiator_name }}
            </span>
          </div>
          <div v-if="cols.department && record.department_name" class="wf-il-mobile-meta">
            部门：{{ record.department_name }}
          </div>
          <div class="wf-il-mobile-meta">
            <span v-if="cols.submittedAt">提交：{{ formatDateTime(record.started_at) }}</span>
            <span v-if="cols.updatedAt && record.updated_at">
              · 更新：{{ formatDateTime(record.updated_at) }}
            </span>
            <span v-if="cols.finishedAt && record.finished_at">
              · 完成：{{ formatDateTime(record.finished_at) }}
            </span>
          </div>
          <slot name="mobile-extra" :record="record" />
          <div v-if="cols.actions" class="wf-il-mobile-actions" @click.stop>
            <slot name="actions" :record="record" />
          </div>
        </a-card>
        <a-empty v-if="!rows.length" />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { IconSettings } from '@arco-design/web-vue/es/icon'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { formatInstanceListStatus } from '@/composables/useWorkflowLabels'
import type {
  InstanceListColumnConfig,
  InstanceListSortDirection,
  WorkflowInstanceListRow,
} from '@/types/workflowInstanceList'
import { formatDateTime } from '@/utils/dateTime'
import { formatInstanceListAmount } from '@/utils/instanceListFormat'
import StatusPill from '@/components/workflow/StatusPill.vue'

const props = withDefaults(
  defineProps<{
    rows: WorkflowInstanceListRow[]
    loading?: boolean
    rowKey?: string
    columns?: InstanceListColumnConfig
    pagination?: Record<string, unknown> | false
    bordered?: boolean
    sortable?: boolean
    sortField?: string
    sortDirection?: InstanceListSortDirection
    rowSelection?: Record<string, unknown>
    scroll?: Record<string, unknown>
    actionsWidth?: number
    actionsFixed?: 'right' | 'left'
    submittedAtTitle?: string
    updatedAtTitle?: string
    selectedKeys?: Array<string | number>
    statusFormatter?: (record: WorkflowInstanceListRow) => string
    rowClass?: (record: WorkflowInstanceListRow) => string
    mobileCardClass?: (record: WorkflowInstanceListRow) => string
    columnSettingsKey?: string
  }>(),
  {
    loading: false,
    rowKey: 'id',
    bordered: false,
    sortable: true,
    pagination: false,
    actionsWidth: 140,
    actionsFixed: 'right',
    submittedAtTitle: '',
  },
)

const emit = defineEmits<{
  'row-click': [WorkflowInstanceListRow]
  'page-change': [number]
  'page-size-change': [number]
  'sorter-change': [string, InstanceListSortDirection]
  'update:selectedKeys': [Array<string | number>]
}>()

const { t } = useI18n()
const { isDesktop } = useBreakpoint()

type ColumnChoiceKey =
  | 'flow'
  | 'sector'
  | 'amount'
  | 'status'
  | 'applicant'
  | 'department'
  | 'submittedAt'
  | 'updatedAt'
  | 'finishedAt'
  | 'actions'

const STORAGE_PREFIX = 'imc-instance-cols:'
const visibilityOverrides = ref<Partial<Record<ColumnChoiceKey, boolean>>>({})

const storageKey = computed(() => (props.columnSettingsKey ? `${STORAGE_PREFIX}${props.columnSettingsKey}` : ''))

function loadVisibility() {
  visibilityOverrides.value = {}
  if (!storageKey.value) return
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (!raw) return
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object') visibilityOverrides.value = parsed
  } catch {
    visibilityOverrides.value = {}
  }
}

watch(storageKey, loadVisibility, { immediate: true })

function persistVisibility() {
  if (!storageKey.value) return
  try {
    localStorage.setItem(storageKey.value, JSON.stringify(visibilityOverrides.value))
  } catch {
    /* storage unavailable */
  }
}

function setColumnVisible(key: ColumnChoiceKey, visible: boolean) {
  visibilityOverrides.value = { ...visibilityOverrides.value, [key]: visible }
  persistVisibility()
}

function resetColumns() {
  visibilityOverrides.value = {}
  if (storageKey.value) {
    try {
      localStorage.removeItem(storageKey.value)
    } catch {
      /* storage unavailable */
    }
  }
}

const cols = computed(() => ({
  displayNo: true,
  flow: true,
  sector: true,
  amount: true,
  status: true,
  applicant: true,
  department: true,
  submittedAt: true,
  updatedAt: false,
  finishedAt: false,
  actions: true,
  ...props.columns,
  ...(props.columnSettingsKey ? visibilityOverrides.value : {}),
}))

const submittedAtTitle = computed(
  () => props.submittedAtTitle || t('workflow.col_submitted_at'),
)

const updatedAtTitle = computed(
  () => props.updatedAtTitle || t('workflow.col_updated_at'),
)

const columnChoices = computed<{ key: ColumnChoiceKey; label: string }[]>(() => [
  { key: 'flow', label: t('workflow.col_flow') },
  { key: 'sector', label: t('workflow.col_sector') },
  { key: 'amount', label: t('workflow.col_amount') },
  { key: 'status', label: t('workflow.col_status') },
  { key: 'applicant', label: t('workflow.col_applicant') },
  { key: 'department', label: t('workflow.col_department') },
  { key: 'submittedAt', label: submittedAtTitle.value },
  { key: 'updatedAt', label: updatedAtTitle.value },
  { key: 'finishedAt', label: t('workflow.col_finished_at') },
  { key: 'actions', label: t('settings.col_actions') },
])

const selectedKeysModel = computed({
  get: () => props.selectedKeys ?? [],
  set: (val: Array<string | number>) => emit('update:selectedKeys', val),
})

const tableScroll = computed<Record<string, unknown>>(
  () => props.scroll || { x: 'max-content' },
)

function recordKey(record: WorkflowInstanceListRow): string | number {
  const raw = record[props.rowKey as keyof WorkflowInstanceListRow]
  return raw != null ? (raw as string | number) : record.id
}

function isSelected(record: WorkflowInstanceListRow): boolean {
  return selectedKeysModel.value.includes(recordKey(record))
}

function toggleSelect(record: WorkflowInstanceListRow, checked: boolean) {
  const key = recordKey(record)
  const next = new Set(selectedKeysModel.value)
  if (checked) next.add(key)
  else next.delete(key)
  selectedKeysModel.value = [...next]
}

function sortOrderFor(field: string): InstanceListSortDirection | undefined {
  return props.sortField === field ? props.sortDirection || undefined : undefined
}

function onSorterChange(dataIndex: string, direction: InstanceListSortDirection) {
  emit('sorter-change', dataIndex, direction)
}

function displayStatus(record: WorkflowInstanceListRow): string {
  if (props.statusFormatter) return props.statusFormatter(record)
  return formatInstanceListStatus(record, t)
}
</script>

<style scoped>
.wf-il-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 4px;
}

.wf-il-col-btn {
  height: 24px;
  padding: 0 6px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.wf-il-col-btn:hover {
  color: var(--text);
}

.wf-il-col-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 172px;
}

.wf-il-col-title {
  margin-bottom: 2px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.wf-il-col-check {
  font-size: 13px;
}

.wf-il-col-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--divider);
}

.wf-il-col-hint {
  font-size: 11px;
  line-height: 1.4;
  color: var(--text-tertiary);
}

.wf-instance-list :deep(.arco-table-tr) {
  cursor: pointer;
}

.wf-instance-list :deep(.arco-table-th) {
  white-space: nowrap;
}

.wf-instance-list :deep(.arco-table-td) {
  font-size: var(--app-font-sm, 13.5px);
}

.wf-instance-list :deep(.arco-table-col-fixed-right) {
  background: var(--surface);
}

.wf-instance-list :deep(.arco-table-tr:hover .arco-table-col-fixed-right) {
  background: var(--brand-softer);
}

.wf-instance-list :deep(.arco-table-col-fixed-right::before) {
  box-shadow: none;
}

.wf-il-no {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  white-space: nowrap;
}

.wf-il-no-text {
  font-family: ui-monospace, 'Consolas', monospace;
  font-variant-numeric: tabular-nums;
}

.wf-il-flow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
}

.wf-il-flow-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wf-il-amount {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.wf-il-status {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wf-il-mobile-status {
  max-width: 48%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wf-il-mobile {
  padding: 0.75rem;
}

.wf-il-mobile-card--skeleton {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  pointer-events: none;
}

.wf-il-sk-line {
  height: 11px;
}

.wf-il-sk-line--no {
  width: 34%;
  height: 10px;
}

.wf-il-sk-line--title {
  width: 62%;
  height: 15px;
}

.wf-il-sk-line--meta {
  width: 48%;
}

.wf-il-mobile-card {
  margin-bottom: 0.65rem;
  border: 1px solid var(--border, #e8e7e2) !important;
  border-radius: var(--radius-lg, 12px) !important;
  box-shadow: var(--shadow-xs);
  cursor: pointer;
}

.wf-il-mobile-card :deep(.arco-card-body) {
  padding: 14px;
}

.wf-il-mobile-card:last-child {
  margin-bottom: 0;
}

.wf-il-mobile-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.wf-il-mobile-no {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  font-size: 12px;
  color: var(--text-tertiary, #7a7f85);
  font-family: ui-monospace, 'Consolas', monospace;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wf-il-mobile-check {
  flex-shrink: 0;
}

.wf-il-mobile-title {
  font-weight: 600;
  font-size: 15px;
  color: var(--text, #17191b);
  line-height: 1.35;
}

.wf-il-mobile-amount {
  margin-top: 4px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text, #17191b);
  font-variant-numeric: tabular-nums;
}

.wf-il-mobile-meta {
  margin-top: 3px;
  font-size: 12.5px;
  color: var(--text-secondary, #5b6066);
  line-height: 1.45;
  word-break: break-word;
}

.wf-il-mobile-actions {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--divider, #efeeea);
}
</style>
