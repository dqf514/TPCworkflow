<template>
  <PageChrome :title="t('monitor.title')" :description="t('monitor.desc')">
    <template #actions>
      <a-select
        v-model="sectorId"
        :options="sectorOpts"
        :placeholder="t('monitor.sector_placeholder')"
        class="w-44"
      />
      <a-select v-model="statusFilter" :options="statusOpts" class="w-32" />
      <a-button @click="refresh">{{ t('monitor.refresh') }}</a-button>
      <a-button type="primary" :disabled="!sectorId" :loading="exporting" @click="exportExcel">
        {{ t('monitor.export_excel') }}
      </a-button>
    </template>
    <div class="monitor-panel app-card">
      <a-empty v-if="!loading && !sectorOpts.length" description="暂无有数据的业务板块" />
      <WorkflowInstanceList
        v-else
        :rows="displayRows"
        :loading="loading"
        row-key="id"
        :columns="{ actions: false, updatedAt: true }"
        :sort-field="sortField"
        :sort-direction="sortDirection"
        @row-click="goDetail"
        @sorter-change="onSorterChange"
      />
    </div>
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import WorkflowInstanceList from '@/components/workflow/WorkflowInstanceList.vue'
import { useInstanceListSort } from '@/composables/useInstanceListSort'
import PageChrome from '@/components/layout/PageChrome.vue'
import type { WorkflowInstanceListRow } from '@/types/workflowInstanceList'
import { formatDateTime } from '@/utils/dateTime'
import { downloadBlob, parseContentDispositionFilename } from '@/utils/downloadBlob'

interface SectorOption {
  id: number
  name: string
  instance_count: number
}

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
const statusFilter = ref('')
const rows = ref<WorkflowInstanceListRow[]>([])
const loading = ref(false)
const exporting = ref(false)

const statusOpts = computed(() => [
  { label: t('workflow.status_all'), value: '' },
  { label: t('workflow.status_running'), value: 'running' },
  { label: t('workflow.status_approved'), value: 'approved' },
  { label: t('workflow.status_rejected'), value: 'rejected' },
  { label: t('workflow.status_cancelled'), value: 'cancelled' },
])

const sectorOpts = computed(() =>
  sectors.value.map((s) => ({
    label: `${s.name}(${s.instance_count})`,
    value: s.id,
  })),
)

const displayRows = computed(() => sortRowsClient(rows.value))

function syncSelectedSector() {
  if (!sectors.value.length) {
    sectorId.value = undefined
    rows.value = []
    return
  }
  if (!sectorId.value || !sectors.value.some((s) => s.id === sectorId.value)) {
    sectorId.value = sectors.value[0].id
  }
}

watch(sectorId, () => load())
watch(statusFilter, () => load())

async function loadSectors() {
  const res = (await api.get('/workflow/sector-monitor/sectors')) as {
    data: ApiResponse<SectorOption[]>
  }
  if (res.data.ok) {
    sectors.value = res.data.data
    syncSelectedSector()
  }
}

async function load() {
  if (!sectorId.value) return
  loading.value = true
  try {
    const res = (await api.get('/workflow/sector-instances', {
      params: {
        sector_id: sectorId.value,
        status: statusFilter.value || undefined,
        ...sortQueryParams(),
      },
    })) as { data: ApiResponse<WorkflowInstanceListRow[]> }
    if (res.data.ok) rows.value = res.data.data
  } finally {
    loading.value = false
  }
}

function onSorterChange(dataIndex: string, direction: '' | 'ascend' | 'descend') {
  handleSorterChange(dataIndex, direction)
  if (sortField.value === 'total_amount') return
  load()
}

function refresh() {
  loadSectors()
  load()
}

function goDetail(record: WorkflowInstanceListRow) {
  router.push({ name: 'instance-detail', params: { uuid: record.public_uuid } })
}

async function exportExcel() {
  if (!sectorId.value) return
  exporting.value = true
  try {
    const res = await api.get('/workflow/sector-instances/export', {
      params: {
        sector_id: sectorId.value,
        status: statusFilter.value || undefined,
      },
      responseType: 'blob',
    })
    const sectorName = sectors.value.find((s) => s.id === sectorId.value)?.name || String(sectorId.value)
    const fallbackName = `流程清单_${sectorName}_${formatDateTime(new Date().toISOString()).replace(/[:\s]/g, '')}.xlsx`
    const fname = parseContentDispositionFilename(res.headers['content-disposition']) || fallbackName
    downloadBlob(res.data as Blob, fname)
    Message.success('导出成功')
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  await loadSectors()
  await load()
})
</script>

<style scoped>
.monitor-panel {
  overflow: hidden;
  padding: 0.25rem 0;
}
</style>
