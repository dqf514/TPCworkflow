<template>
  <PageChrome :title="t('workflow.todo')" :description="pageDesc">
    <div class="tasks-workspace">
      <a-tabs v-model:active-key="activeTab" type="line" class="tasks-tabs" @change="onTabChange">
        <a-tab-pane key="todo">
          <template #title>
            <span class="tab-title-with-badge">
              {{ t('workflow.tab_todo') }}
              <NavBadge :count="badges.todoCount" inline />
            </span>
          </template>
        </a-tab-pane>
        <a-tab-pane key="done">
          <template #title>{{ t('workflow.tab_done') }}</template>
        </a-tab-pane>
      </a-tabs>

      <div class="tasks-toolbar">
      <div class="tasks-toolbar-filters">
        <a-input-search
          v-model="keyword"
          :placeholder="t('workflow.tasks_keyword_ph')"
          allow-clear
          class="tasks-toolbar-search"
          @search="onSearch"
          @clear="onSearch"
        />
        <a-select
          v-model="sectorId"
          :options="sectorOpts"
          :placeholder="t('workflow.tasks_sector_all')"
          allow-clear
          class="tasks-toolbar-select"
          @change="reload"
        />
        <a-select
          v-if="activeTab === 'done'"
          v-model="doneStatusFilter"
          :options="doneStatusOpts"
          class="tasks-toolbar-select tasks-toolbar-select--status"
          @change="reload"
        />
      </div>
      <div class="tasks-toolbar-actions">
        <a-button @click="reload">{{ t('workflow.tasks_refresh') }}</a-button>
        <a-button
          v-if="activeTab === 'todo' && selectedTodoKeys.length"
          type="primary"
          :loading="batchLoading"
          @click="openBatchApprove"
        >
          {{ t('workflow.batch_approve', { count: selectedQuickApproveCount }) }}
        </a-button>
      </div>
      </div>

      <div v-show="activeTab === 'todo'" class="tasks-panel app-card" :class="{ 'tasks-panel--flush': isDesktop }">
          <WorkflowInstanceList
            :rows="displayTodoRows"
            :loading="loadingTodo"
            row-key="task_id"
            column-settings-key="tasks-todo"
            :columns="todoColumns"
            :pagination="todoPagination"
            :sort-field="todoSort.sortField.value"
            :sort-direction="todoSort.sortDirection.value"
            :row-selection="todoRowSelection"
            :selected-keys="selectedTodoKeys"
            :status-formatter="todoStatusFormatter"
            :submitted-at-title="t('workflow.col_task_received_at')"
            :actions-width="220"
            @row-click="goTask"
            @page-change="onTodoPageChange"
            @page-size-change="onTodoPageSizeChange"
            @sorter-change="onTodoSorterChange"
            @update:selected-keys="selectedTodoKeys = $event"
          >
            <template #extra-columns>
              <a-table-column
                :title="t('workflow.col_node')"
                data-index="node_name"
                :width="108"
                :ellipsis="true"
                :tooltip="true"
                :sortable="{ sortDirections: ['ascend', 'descend'] }"
                :sort-order="todoSort.sortField.value === 'node_name' ? todoSort.sortDirection.value : undefined"
              >
                <template #cell="{ record }">
                  {{ (record as WorkflowTaskListRow).node_name || (record as WorkflowTaskListRow).node_id }}
                </template>
              </a-table-column>
            </template>
            <template #actions="{ record }">
              <TaskRowActions
                :record="record as WorkflowTaskListRow"
                :acting-id="actingTaskId"
                @approve="onQuickApprove"
                @reject="openRejectModal"
                @view="goTask"
              />
            </template>
            <template #mobile-extra="{ record }">
              <div class="tasks-mobile-node">
                {{ t('workflow.col_node') }}：{{ (record as WorkflowTaskListRow).node_name || '—' }}
              </div>
            </template>
          </WorkflowInstanceList>
      </div>

      <div v-show="activeTab === 'done'" class="tasks-panel app-card" :class="{ 'tasks-panel--flush': isDesktop }">
          <WorkflowInstanceList
            :rows="displayDoneRows"
            :loading="loadingDone"
            row-key="task_id"
            column-settings-key="tasks-done"
            :columns="doneColumns"
            :pagination="donePagination"
            :sort-field="doneSort.sortField.value"
            :sort-direction="doneSort.sortDirection.value"
            :status-formatter="doneStatusFormatter"
            :submitted-at-title="t('workflow.col_started_at')"
            :updated-at-title="t('workflow.col_my_handled_at')"
            :actions-width="96"
            @row-click="goInstance"
            @page-change="onDonePageChange"
            @page-size-change="onDonePageSizeChange"
            @sorter-change="onDoneSorterChange"
          >
            <template #extra-columns>
              <a-table-column
                :title="t('workflow.col_node')"
                data-index="node_name"
                :width="108"
                :ellipsis="true"
                :tooltip="true"
              >
                <template #cell="{ record }">
                  {{ (record as WorkflowTaskListRow).node_name || (record as WorkflowTaskListRow).node_id }}
                </template>
              </a-table-column>
            </template>
            <template #actions="{ record }">
              <a-space @click.stop>
                <a-button size="mini" @click.stop="goInstance(record as WorkflowTaskListRow)">
                  {{ t('workflow.tasks_view') }}
                </a-button>
              </a-space>
            </template>
            <template #mobile-extra="{ record }">
              <div class="tasks-mobile-node">
                {{ t('workflow.col_node') }}：{{ (record as WorkflowTaskListRow).node_name || '—' }}
              </div>
            </template>
          </WorkflowInstanceList>
      </div>
    </div>

    <a-modal
      v-model:visible="rejectModalOpen"
      :title="t('workflow.comment_modal_reject_title')"
      :ok-loading="actingTaskId != null"
      @ok="confirmReject"
      @cancel="closeRejectModal"
    >
      <a-textarea
        v-model="rejectComment"
        :auto-size="{ minRows: 3 }"
        :placeholder="t('workflow.comment_ph')"
      />
    </a-modal>

    <a-modal
      v-model:visible="batchModalOpen"
      :title="t('workflow.batch_approve_title')"
      :ok-loading="batchLoading"
      @ok="confirmBatchApprove"
      @cancel="batchModalOpen = false"
    >
      <p class="tasks-batch-hint">
        {{ t('workflow.batch_approve_hint', { count: selectedQuickApproveCount }) }}
      </p>
      <a-textarea
        v-model="batchComment"
        :auto-size="{ minRows: 2 }"
        :placeholder="t('workflow.comment_ph')"
      />
    </a-modal>
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api, type ApiResponse } from '@/api/client'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { useInstanceListSort } from '@/composables/useInstanceListSort'
import { formatMyTaskStatus } from '@/composables/useWorkflowLabels'
import PageChrome from '@/components/layout/PageChrome.vue'
import WorkflowInstanceList from '@/components/workflow/WorkflowInstanceList.vue'
import TaskRowActions from '@/components/workflow/TaskRowActions.vue'
import NavBadge from '@/components/NavBadge.vue'
import type { WorkflowInstanceListRow } from '@/types/workflowInstanceList'
import type {
  TaskBatchCompleteResult,
  TaskListPageResult,
  WorkflowTaskListRow,
} from '@/types/workflowTaskList'
import { useWorkflowBadgesStore } from '@/stores/workflowBadges'

const { t } = useI18n()
const router = useRouter()
const { isDesktop } = useBreakpoint()
const badges = useWorkflowBadgesStore()

const activeTab = ref<'todo' | 'done'>('todo')
const keyword = ref('')
const sectorId = ref<number | undefined>()
const doneStatusFilter = ref('')
const sectors = ref<{ id: number; name: string }[]>([])

const todoSort = useInstanceListSort('task_created_at')
const doneSort = useInstanceListSort('completed_at')

const todoRows = ref<WorkflowTaskListRow[]>([])
const doneRows = ref<WorkflowTaskListRow[]>([])
const loadingTodo = ref(false)
const loadingDone = ref(false)
const doneLoaded = ref(false)

const todoTotal = ref(0)
const doneTotal = ref(0)
const todoPage = ref(1)
const donePage = ref(1)
const pageSize = ref(20)

const selectedTodoKeys = ref<Array<string | number>>([])
const actingTaskId = ref<number | null>(null)
const batchLoading = ref(false)
const batchModalOpen = ref(false)
const batchComment = ref('同意')

const rejectModalOpen = ref(false)
const rejectComment = ref('')
const rejectTaskId = ref<number | null>(null)

const pageDesc = computed(() =>
  activeTab.value === 'todo' ? t('workflow.todo_desc') : t('workflow.done_desc'),
)

const sectorOpts = computed(() => sectors.value.map((s) => ({ label: s.name, value: s.id })))

const doneStatusOpts = computed(() => [
  { label: t('workflow.status_all'), value: '' },
  { label: t('workflow.my_task_approved'), value: 'approved' },
  { label: t('workflow.my_task_rejected'), value: 'rejected' },
  { label: t('workflow.my_task_completed'), value: 'completed' },
  { label: t('workflow.my_task_transfer'), value: 'transfer' },
])

const todoColumns = {
  updatedAt: false,
  finishedAt: false,
}

const doneColumns = {
  status: true,
  updatedAt: true,
  finishedAt: false,
}

const todoPagination = computed(() => ({
  current: todoPage.value,
  pageSize: pageSize.value,
  total: todoTotal.value,
  showTotal: true,
  showPageSize: true,
  pageSizeOptions: [10, 20, 50, 100],
}))

const donePagination = computed(() => ({
  current: donePage.value,
  pageSize: pageSize.value,
  total: doneTotal.value,
  showTotal: true,
  showPageSize: true,
  pageSizeOptions: [10, 20, 50, 100],
}))

const displayTodoRows = computed(() => {
  if (todoSort.sortField.value === 'total_amount') {
    return todoSort.sortRowsClient(todoRows.value)
  }
  return todoRows.value
})

const displayDoneRows = computed(() => {
  if (doneSort.sortField.value === 'total_amount') {
    return doneSort.sortRowsClient(doneRows.value)
  }
  return doneRows.value
})

const selectedQuickApproveCount = computed(() => {
  const keys = new Set(selectedTodoKeys.value.map(String))
  return todoRows.value.filter((r) => keys.has(String(r.task_id)) && r.can_quick_approve).length
})

const todoRowSelection = computed(() => ({
  type: 'checkbox',
  showCheckedAll: true,
  onlyCurrent: false,
}))

function todoStatusFormatter(record: WorkflowInstanceListRow): string {
  const row = record as WorkflowTaskListRow
  return row.node_name || row.current_node_label || t('workflow.status_pending')
}

function doneStatusFormatter(record: WorkflowInstanceListRow): string {
  const row = record as WorkflowTaskListRow
  return formatMyTaskStatus(row.task_status, t)
}

function goTask(record: WorkflowTaskListRow) {
  router.push({ name: 'task-detail', params: { id: String(record.task_id) } })
}

function goInstance(record: WorkflowTaskListRow) {
  if (record.public_uuid) {
    router.push({ name: 'instance-detail', params: { uuid: record.public_uuid } })
  }
}

async function loadSectors() {
  const res = await api.get<ApiResponse<{ id: number; name: string }[]>>('/workflow/business-sectors')
  if (res.data.ok) sectors.value = res.data.data
}

function listParams(sort: ReturnType<typeof useInstanceListSort>) {
  return {
    page: activeTab.value === 'todo' ? todoPage.value : donePage.value,
    page_size: pageSize.value,
    keyword: keyword.value.trim() || undefined,
    sector_id: sectorId.value || undefined,
    ...sort.sortQueryParams(),
  }
}

async function loadTodo() {
  loadingTodo.value = true
  try {
    const res = await api.get<ApiResponse<TaskListPageResult>>('/workflow/tasks/todo', {
      params: listParams(todoSort),
    })
    if (res.data.ok) {
      todoRows.value = res.data.data.items.map((r) => ({
        ...r,
        started_at: r.task_created_at || r.started_at,
      }))
      todoTotal.value = res.data.data.total
      todoPage.value = res.data.data.page
      const valid = new Set(todoRows.value.map((r) => r.task_id))
      selectedTodoKeys.value = selectedTodoKeys.value.filter((k) => valid.has(Number(k)))
    }
    void badges.refresh(true)
  } finally {
    loadingTodo.value = false
  }
}

async function loadDone() {
  loadingDone.value = true
  try {
    const res = await api.get<ApiResponse<TaskListPageResult>>('/workflow/tasks/done', {
      params: {
        ...listParams(doneSort),
        task_status: doneStatusFilter.value || undefined,
      },
    })
    if (res.data.ok) {
      doneRows.value = res.data.data.items.map((r) => ({
        ...r,
        updated_at: r.task_completed_at || r.updated_at,
      }))
      doneTotal.value = res.data.data.total
      donePage.value = res.data.data.page
      doneLoaded.value = true
    }
  } finally {
    loadingDone.value = false
  }
}

function reload() {
  if (activeTab.value === 'todo') void loadTodo()
  else void loadDone()
}

function onSearch() {
  if (activeTab.value === 'todo') todoPage.value = 1
  else donePage.value = 1
  reload()
}

function onTabChange(key: string | number) {
  if (key === 'done' && !doneLoaded.value) void loadDone()
}

function onTodoPageChange(p: number) {
  todoPage.value = p
  void loadTodo()
}

function onDonePageChange(p: number) {
  donePage.value = p
  void loadDone()
}

function onTodoPageSizeChange(size: number) {
  pageSize.value = size
  todoPage.value = 1
  void loadTodo()
}

function onDonePageSizeChange(size: number) {
  pageSize.value = size
  donePage.value = 1
  void loadDone()
}

function onTodoSorterChange(dataIndex: string, direction: '' | 'ascend' | 'descend') {
  todoSort.onSorterChange(dataIndex, direction)
  todoPage.value = 1
  if (todoSort.sortField.value === 'total_amount') return
  void loadTodo()
}

function onDoneSorterChange(dataIndex: string, direction: '' | 'ascend' | 'descend') {
  doneSort.onSorterChange(dataIndex, direction)
  donePage.value = 1
  if (doneSort.sortField.value === 'total_amount') return
  void loadDone()
}

async function completeTask(taskId: number, action: 'approve' | 'reject', comment: string) {
  actingTaskId.value = taskId
  try {
    const res = await api.post<ApiResponse<unknown>>(`/workflow/tasks/${taskId}/complete`, {
      action,
      comment,
    })
    if (res.data.ok) {
      Message.success(res.data.message || t('common.success'))
      void badges.refresh(true)
      await loadTodo()
      return true
    }
    Message.error(res.data.message || '操作失败')
    return false
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '操作失败')
    return false
  } finally {
    actingTaskId.value = null
  }
}

function onQuickApprove(record: WorkflowTaskListRow) {
  if (record.field_requirement_errors?.length) {
    Message.warning(record.field_requirement_errors.join('；'))
    return
  }
  if (record.can_quick_approve) {
    void completeTask(record.task_id, 'approve', '同意')
    return
  }
  goTask(record)
}

function openRejectModal(record: WorkflowTaskListRow) {
  rejectTaskId.value = record.task_id
  rejectComment.value = ''
  rejectModalOpen.value = true
}

function closeRejectModal() {
  rejectModalOpen.value = false
  rejectTaskId.value = null
  rejectComment.value = ''
}

async function confirmReject() {
  if (!rejectTaskId.value) return false
  if (!rejectComment.value.trim()) {
    Message.warning(t('workflow.comment_required'))
    return false
  }
  const ok = await completeTask(rejectTaskId.value, 'reject', rejectComment.value.trim())
  if (ok) closeRejectModal()
  return ok
}

function openBatchApprove() {
  if (!selectedQuickApproveCount.value) {
    Message.warning(t('workflow.batch_approve_none'))
    return
  }
  batchComment.value = '同意'
  batchModalOpen.value = true
}

async function confirmBatchApprove() {
  const keys = new Set(selectedTodoKeys.value.map(String))
  const ids = todoRows.value
    .filter((r) => keys.has(String(r.task_id)) && r.can_quick_approve)
    .map((r) => r.task_id)
  if (!ids.length) {
    Message.warning(t('workflow.batch_approve_none'))
    return false
  }
  batchLoading.value = true
  try {
    const res = await api.post<ApiResponse<TaskBatchCompleteResult>>('/workflow/tasks/batch-complete', {
      task_ids: ids,
      action: 'approve',
      comment: batchComment.value.trim() || '同意',
    })
    if (res.data.ok) {
      const data = res.data.data
      Message.success(res.data.message || t('common.success'))
      if (data.failed?.length) {
        Message.warning(
          data.failed.map((f) => `#${f.task_id}: ${f.reason}`).join('；'),
        )
      }
      selectedTodoKeys.value = []
      batchModalOpen.value = false
      void badges.refresh(true)
      await loadTodo()
      return true
    }
    Message.error(res.data.message || '操作失败')
    return false
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '操作失败')
    return false
  } finally {
    batchLoading.value = false
  }
}

onMounted(async () => {
  await loadSectors()
  await loadTodo()
})

onActivated(() => {
  if (activeTab.value === 'todo') void loadTodo()
  else if (doneLoaded.value) void loadDone()
})

watch(activeTab, (tab) => {
  if (tab === 'done' && !doneLoaded.value) void loadDone()
})
</script>

<style scoped>
.tab-title-with-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.tasks-workspace {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.tasks-tabs :deep(.arco-tabs-content) {
  display: none;
  padding: 0;
  height: 0;
  overflow: hidden;
}

.tasks-tabs :deep(.arco-tabs-nav) {
  margin-bottom: 0;
}

.tasks-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 12px 0 12px;
  flex-wrap: wrap;
}

.tasks-toolbar-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1 1 auto;
  min-width: 0;
  flex-wrap: wrap;
}

.tasks-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.tasks-toolbar-search {
  width: 260px;
  max-width: 100%;
  flex: 0 1 260px;
}

.tasks-toolbar-search :deep(.arco-input-wrapper) {
  width: 100%;
}

.tasks-toolbar-select {
  width: 140px;
  flex: 0 0 140px;
}

.tasks-toolbar-select--status {
  width: 116px;
  flex-basis: 116px;
}

.tasks-toolbar-filters :deep(.arco-select-view-single),
.tasks-toolbar-filters :deep(.arco-select) {
  width: 100%;
}

@media (max-width: 900px) {
  .tasks-toolbar-search {
    flex: 1 1 180px;
    width: auto;
    min-width: 160px;
  }

  .tasks-toolbar-select {
    flex: 1 1 120px;
    width: auto;
    min-width: 110px;
  }

  .tasks-toolbar-actions {
    width: 100%;
    justify-content: flex-end;
  }
}

.tasks-panel {
  overflow: hidden;
  padding: 0;
}

.tasks-panel--flush :deep(.arco-table-th) {
  background: var(--surface-muted) !important;
  font-weight: 600;
  color: var(--text-secondary);
}

.tasks-panel--flush :deep(.arco-table-td:last-child) {
  text-align: right;
}

.tasks-mobile-node {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

.tasks-batch-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
