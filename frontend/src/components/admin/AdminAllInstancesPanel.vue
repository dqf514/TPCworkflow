<template>
  <a-card class="settings-card" :bordered="false">
    <div class="flex flex-wrap gap-2 mb-3">
      <a-input-search
        v-model="keyword"
        :placeholder="t('settings.instances_keyword_ph')"
        allow-clear
        class="w-52"
        @search="onSearch"
        @clear="onSearch"
      />
      <a-select
        v-model="sectorId"
        :options="sectorOpts"
        :placeholder="t('settings.instances_sector_all')"
        allow-clear
        class="w-40"
        @change="reload"
      />
      <a-select v-model="statusFilter" :options="statusOpts" class="w-32" @change="reload" />
      <a-button @click="reload">{{ t('settings.instances_refresh') }}</a-button>
    </div>

    <WorkflowInstanceList
      :rows="displayRows"
      :loading="loading"
      row-key="id"
      :pagination="pagination"
      :sort-field="sortField"
      :sort-direction="sortDirection"
      @row-click="goDetail"
      @page-change="onPageChange"
      @page-size-change="onPageSizeChange"
      @sorter-change="onSorterChange"
    >
      <template #actions="{ record }">
        <a-space @click.stop>
          <a-button size="mini" @click="goDetail(record)">{{ t('settings.instances_view') }}</a-button>
          <a-button size="mini" status="danger" @click="openDeleteModal(record)">
            {{ t('settings.action_delete') }}
          </a-button>
        </a-space>
      </template>
    </WorkflowInstanceList>

    <a-modal
      v-model:visible="deleteModalOpen"
      :title="t('settings.instances_delete_modal_title')"
      :ok-loading="deleteLoading"
      :ok-button-props="{ disabled: !deleteCode.trim() }"
      @ok="confirmDelete"
      @cancel="closeDeleteModal"
    >
      <p class="instances-delete-warn">
        {{ t('settings.instances_delete_confirm', { no: deleteTarget?.display_no || '—' }) }}
      </p>
      <p class="instances-delete-hint">{{ t('settings.instances_delete_code_hint') }}</p>
      <a-form layout="vertical">
        <a-form-item :label="t('settings.instances_delete_code_label')">
          <a-input-group>
            <a-input
              v-model="deleteCode"
              :placeholder="t('settings.instances_delete_code_ph')"
              maxlength="6"
              allow-clear
            />
            <a-button
              type="outline"
              :loading="sendingCode"
              :disabled="codeCooldown > 0"
              @click="sendDeleteCode"
            >
              {{
                codeCooldown > 0
                  ? t('settings.instances_delete_code_resend', { sec: codeCooldown })
                  : t('settings.instances_delete_code_send')
              }}
            </a-button>
          </a-input-group>
        </a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import WorkflowInstanceList from '@/components/workflow/WorkflowInstanceList.vue'
import { useInstanceListSort } from '@/composables/useInstanceListSort'
import type { WorkflowInstanceListRow } from '@/types/workflowInstanceList'

const { t } = useI18n()
const router = useRouter()
const {
  sortField,
  sortDirection,
  sortQueryParams,
  onSorterChange: handleSorterChange,
  sortRowsClient,
} = useInstanceListSort('started_at')

const sectors = ref<{ id: number; name: string }[]>([])
const sectorId = ref<number | undefined>()
const statusFilter = ref('')
const keyword = ref('')
const rows = ref<WorkflowInstanceListRow[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const deleteModalOpen = ref(false)
const deleteTarget = ref<WorkflowInstanceListRow | null>(null)
const deleteCode = ref('')
const deleteLoading = ref(false)
const sendingCode = ref(false)
const codeCooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

const statusOpts = computed(() => [
  { label: t('workflow.status_all'), value: '' },
  { label: t('workflow.status_draft'), value: 'draft' },
  { label: t('workflow.status_running'), value: 'running' },
  { label: t('workflow.status_approved'), value: 'approved' },
  { label: t('workflow.status_rejected'), value: 'rejected' },
  { label: t('workflow.status_cancelled'), value: 'cancelled' },
])

const sectorOpts = computed(() =>
  sectors.value.map((s) => ({ label: s.name, value: s.id })),
)

const pagination = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: total.value,
  showTotal: true,
  showPageSize: true,
  pageSizeOptions: [10, 20, 50, 100],
}))

const displayRows = computed(() => sortRowsClient(rows.value))

function startCodeCooldown(seconds = 60) {
  codeCooldown.value = seconds
  if (cooldownTimer) clearInterval(cooldownTimer)
  cooldownTimer = setInterval(() => {
    codeCooldown.value -= 1
    if (codeCooldown.value <= 0 && cooldownTimer) {
      clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }, 1000)
}

async function loadSectors() {
  const res = (await api.get('/workflow/business-sectors')) as {
    data: ApiResponse<{ id: number; name: string }[]>
  }
  if (res.data.ok) sectors.value = res.data.data
}

async function reload() {
  loading.value = true
  try {
    const res = (await api.get('/admin/workflow-instances', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        status: statusFilter.value || undefined,
        sector_id: sectorId.value || undefined,
        keyword: keyword.value.trim() || undefined,
        ...sortQueryParams(),
      },
    })) as {
      data: ApiResponse<{
        items: WorkflowInstanceListRow[]
        total: number
        page: number
        page_size: number
      }>
    }
    if (res.data.ok) {
      rows.value = res.data.data.items
      total.value = res.data.data.total
      page.value = res.data.data.page
    }
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  reload()
}

function onPageChange(p: number) {
  page.value = p
  reload()
}

function onPageSizeChange(size: number) {
  pageSize.value = size
  page.value = 1
  reload()
}

function onSorterChange(dataIndex: string, direction: '' | 'ascend' | 'descend') {
  handleSorterChange(dataIndex, direction)
  page.value = 1
  if (sortField.value === 'total_amount') {
    return
  }
  reload()
}

function goDetail(record: WorkflowInstanceListRow) {
  router.push({ name: 'instance-detail', params: { uuid: record.public_uuid } })
}

function openDeleteModal(record: WorkflowInstanceListRow) {
  deleteTarget.value = record
  deleteCode.value = ''
  deleteModalOpen.value = true
}

function closeDeleteModal() {
  deleteModalOpen.value = false
  deleteTarget.value = null
  deleteCode.value = ''
}

async function sendDeleteCode() {
  sendingCode.value = true
  try {
    const res = (await api.post('/admin/workflow-instances/delete-confirm/send')) as {
      data: ApiResponse<unknown>
    }
    if (res.data.ok) {
      Message.success(res.data.message || t('settings.instances_delete_code_sent'))
      startCodeCooldown()
    } else {
      Message.error(res.data.message || t('settings.instances_delete_code_send_failed'))
    }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('settings.instances_delete_code_send_failed'))
  } finally {
    sendingCode.value = false
  }
}

async function confirmDelete() {
  if (!deleteTarget.value) return false
  const code = deleteCode.value.trim()
  if (!code) {
    Message.warning(t('settings.instances_delete_code_required'))
    return false
  }
  deleteLoading.value = true
  try {
    const ref = deleteTarget.value.public_uuid || String(deleteTarget.value.id)
    const res = (await api.delete(`/admin/workflow-instances/${ref}`, {
      data: { email_code: code },
    })) as { data: ApiResponse<unknown> }
    if (res.data.ok) {
      Message.success(res.data.message || t('settings.instances_deleted'))
      closeDeleteModal()
      await reload()
      return true
    }
    Message.error(res.data.message || t('settings.instances_delete_failed'))
    return false
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('settings.instances_delete_failed'))
    return false
  } finally {
    deleteLoading.value = false
  }
}

onMounted(async () => {
  await loadSectors()
  await reload()
})

onUnmounted(() => {
  if (cooldownTimer) clearInterval(cooldownTimer)
})
</script>

<style scoped>
.settings-card :deep(.arco-card-body) {
  padding-top: 12px;
}

.instances-delete-warn {
  margin: 0 0 8px;
  color: var(--color-danger-6, #f53f3f);
  font-weight: 600;
}

.instances-delete-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
