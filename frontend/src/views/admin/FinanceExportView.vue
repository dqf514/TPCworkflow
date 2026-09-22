<template>
  <PageChrome title="财务凭证导出" description="按需筛选并勾选流程，生成用友 YonSuite BIP 凭证导入 Excel；可在此板块管理字段映射方案。">
    <template #actions>
      <a-select
        v-model="sectorId"
        :options="sectorOpts"
        placeholder="业务板块"
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
        :placeholder="['开始日期', '结束日期']"
        allow-clear
      />
      <a-button @click="refresh">刷新</a-button>
      <a-button
        type="primary"
        :disabled="!selectedKeys.length"
        @click="exportVisible = true"
      >
        导出选中（{{ selectedKeys.length }}）
      </a-button>
      </template>
    </template>

    <a-tabs v-model:active-key="activeTab" class="finance-tabs">
      <a-tab-pane key="export" title="导出流程">
        <div class="finance-panel app-card">
          <a-empty v-if="!loading && !sectorOpts.length" description="暂无可导出的业务板块" />
          <template v-else>
            <div class="finance-toolbar">
              <a-checkbox
                :model-value="allCurrentSelected"
                :indeterminate="someCurrentSelected && !allCurrentSelected"
                :disabled="!rows.length"
                @change="toggleSelectAll"
              >
                全选当前列表（{{ rows.length }} 条）
              </a-checkbox>
              <span v-if="selectedKeys.length" class="finance-selected-hint">
                已勾选 {{ selectedKeys.length }} 条
              </span>
            </div>
            <WorkflowInstanceList
              v-model:selected-keys="selectedKeys"
              :rows="displayRows"
              :loading="loading"
              row-key="id"
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
      <a-tab-pane key="mapping" title="映射方案">
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

const timeFieldOpts = [
  { label: '按提交时间', value: 'started_at' },
  { label: '按完成时间', value: 'finished_at' },
]

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
  font-size: 13px;
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
</style>
