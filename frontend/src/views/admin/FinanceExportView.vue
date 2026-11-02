<template>
  <PageChrome :title="t('finance.title')" :description="t('finance.desc')">
    <template #actions>
      <div class="finance-actions">
        <a-select
          v-model="sectorId"
          :options="sectorOpts"
          :placeholder="t('finance.sector_placeholder')"
          class="w-44"
          allow-search
        />
        <template v-if="activeTab === 'export'">
        <a-select v-model="statusFilter" :options="statusOpts" class="w-32" />
        <a-select v-model="timeField" :options="timeFieldOpts" class="w-36" />
        <a-range-picker
          v-model="dateRange"
          class="w-72"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          :placeholder="[t('finance.date_from'), t('finance.date_to')]"
          allow-clear
        />
        <a-button @click="refresh">{{ t('finance.refresh') }}</a-button>
        <a-button
          type="primary"
          :disabled="!selectedKeys.length"
          @click="exportVisible = true"
        >
          {{ t('finance.export_selected', { count: selectedKeys.length }) }}
        </a-button>
        </template>
      </div>
    </template>

    <a-tabs v-model:active-key="activeTab" class="finance-tabs">
      <a-tab-pane key="export" :title="t('finance.tab_export')">
        <div class="finance-panel app-card">
          <a-empty v-if="!loading && !sectorOpts.length" :description="t('finance.empty_sector')" />
          <template v-else>
            <div class="finance-toolbar">
              <a-checkbox
                :model-value="allCurrentSelected"
                :indeterminate="someCurrentSelected && !allCurrentSelected"
                :disabled="!rows.length"
                @change="toggleSelectAll"
              >
                {{ t('finance.select_all', { count: rows.length }) }}
              </a-checkbox>
              <span v-if="selectedKeys.length" class="finance-selected-hint">
                {{ t('finance.selected', { count: selectedKeys.length }) }}
              </span>
            </div>
            <WorkflowInstanceList
              v-model:selected-keys="selectedKeys"
              :rows="displayRows"
              :loading="loading"
              row-key="id"
              column-settings-key="finance-export"
              :columns="{
                displayNo: false,
                actions: false,
                finishedAt: true,
              }"
              :row-selection="rowSelection"
              :sort-field="sortField"
              :sort-direction="sortDirection"
              @row-click="onRowClick"
              @sorter-change="onSorterChange"
            />
          </template>
        </div>
      </a-tab-pane>
      <a-tab-pane key="mapping" :title="t('finance.tab_mapping')">
        <div class="finance-panel app-card">
          <FinanceMappingManager :sector-id="sectorId" />
        </div>
      </a-tab-pane>
    </a-tabs>

    <FinanceExportModal
      v-model:visible="exportVisible"
      :sector-id="sectorId"
      :instance-ids="selectedKeys"
    />
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api, type ApiResponse } from '@/api/client'
import WorkflowInstanceList from '@/components/workflow/WorkflowInstanceList.vue'
import { useInstanceListSort } from '@/composables/useInstanceListSort'
import PageChrome from '@/components/layout/PageChrome.vue'
import FinanceExportModal from '@/components/finance/FinanceExportModal.vue'
import FinanceMappingManager from '@/components/finance/FinanceMappingManager.vue'
import type { WorkflowInstanceListRow } from '@/types/workflowInstanceList'

interface SectorOption {
  id: number
  name: string
  instance_count: number
}

interface Row extends WorkflowInstanceListRow {}

const { t } = useI18n()
const router = useRouter()
const {
  sortField,
  sortDirection,
  sortQueryParams,
  onSorterChange: handleSorterChange,
  sortRowsClient,
} = useInstanceListSort('started_at')
const sectors = ref<SectorOption[]>([])
const sectorId = ref<number>()
const statusFilter = ref('approved')
const timeField = ref<'started_at' | 'finished_at'>('started_at')
const dateRange = ref<string[]>([])
const rows = ref<Row[]>([])
const loading = ref(false)
const selectedKeys = ref<number[]>([])
const exportVisible = ref(false)
const activeTab = ref('export')

const statusOpts = computed(() => [
  { label: t('workflow.status_all'), value: '' },
  { label: t('workflow.status_running'), value: 'running' },
  { label: t('workflow.status_approved'), value: 'approved' },
  { label: t('workflow.status_rejected'), value: 'rejected' },
  { label: t('workflow.status_cancelled'), value: 'cancelled' },
])

const timeFieldOpts = computed(() => [
  { label: t('finance.by_started_at'), value: 'started_at' },
  { label: t('finance.by_finished_at'), value: 'finished_at' },
])

const sectorOpts = computed(() =>
  sectors.value.map((s) => ({
    label: `${s.name}(${s.instance_count})`,
    value: s.id,
  })),
)

const displayRows = computed(() => sortRowsClient(rows.value))

const rowSelection = {
  type: 'checkbox' as const,
  showCheckedAll: false,
}

const allCurrentSelected = computed(
  () => rows.value.length > 0 && rows.value.every((r) => selectedKeys.value.includes(r.id)),
)

const someCurrentSelected = computed(() =>
  rows.value.some((r) => selectedKeys.value.includes(r.id)),
)

function syncSelectedSector() {
  if (!sectors.value.length) {
    sectorId.value = undefined
    rows.value = []
    selectedKeys.value = []
    return
  }
  if (!sectorId.value || !sectors.value.some((s) => s.id === sectorId.value)) {
    sectorId.value = sectors.value[0].id
  }
}

function toggleSelectAll(checked: boolean | (string | boolean | number)[]) {
  const on = checked === true
  if (!on) {
    const currentIds = new Set(rows.value.map((r) => r.id))
    selectedKeys.value = selectedKeys.value.filter((id) => !currentIds.has(id))
    return
  }
  const merged = new Set(selectedKeys.value)
  for (const row of rows.value) merged.add(row.id)
  selectedKeys.value = [...merged]
}

watch([sectorId, statusFilter, timeField, dateRange], () => {
  void load()
})

async function loadSectors() {
  const res = (await api.get('/workflow/finance-export/sectors')) as {
    data: ApiResponse<SectorOption[]>
  }
  if (res.data.ok) {
    sectors.value = res.data.data
    syncSelectedSector()
  }
}

async function load() {
  if (!sectorId.value) {
    rows.value = []
    return
  }
  loading.value = true
  try {
    const params: Record<string, string | number | undefined> = {
      sector_id: sectorId.value,
      status: statusFilter.value || undefined,
      time_field: timeField.value,
    }
    if (dateRange.value?.length === 2) {
      params.date_from = dateRange.value[0]
      params.date_to = dateRange.value[1]
    }
    const res = (await api.get('/workflow/finance-export/instances', {
      params: {
        ...params,
        ...sortQueryParams(),
      },
    })) as {
      data: ApiResponse<Row[]>
    }
    if (res.data.ok) {
      rows.value = res.data.data
      const visible = new Set(rows.value.map((r) => r.id))
      selectedKeys.value = selectedKeys.value.filter((id) => visible.has(id))
    }
  } finally {
    loading.value = false
  }
}

async function refresh() {
  await loadSectors()
  await load()
}

function onSorterChange(dataIndex: string, direction: '' | 'ascend' | 'descend') {
  handleSorterChange(dataIndex, direction)
  if (sortField.value === 'total_amount') return
  void load()
}

function onRowClick(record: Row) {
  router.push({ name: 'instance-detail', params: { uuid: record.public_uuid } })
}

onMounted(async () => {
  await loadSectors()
  await load()
})
</script>

<style scoped>
.finance-tabs {
  margin-top: 0.25rem;
}

.finance-panel {
  overflow: hidden;
  padding: 0.25rem 0;
}

.finance-toolbar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.65rem 1rem;
  border-bottom: 1px solid var(--border);
}

.finance-selected-hint {
  font-size: var(--app-font-sm);
  color: var(--text-secondary);
}

.finance-panel :deep(.arco-table-th) {
  background: var(--surface-muted) !important;
  font-weight: 600;
  color: var(--text-secondary);
}

.finance-panel :deep(.arco-table-tr) {
  cursor: pointer;
}

/* 窄屏适配：工具栏换行、顶部操作区控件整行 */
@media (max-width: 768px) {
  .finance-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    width: 100%;
  }

  .finance-actions :deep(.arco-select),
  .finance-actions :deep(.arco-range-picker) {
    width: 100%;
  }

  .finance-toolbar {
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.6rem 0.75rem;
  }

  .finance-panel :deep(.arco-select),
  .finance-panel :deep(.arco-picker),
  .finance-panel :deep(.arco-range-picker) {
    width: 100%;
  }
}
</style>
