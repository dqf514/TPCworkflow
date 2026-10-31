<template>
  <PageChrome :title="t('workflow.my_instances')" :description="pageDesc">
    <a-tabs v-model:active-key="activeTab" type="line" class="instances-tabs" @change="onTabChange">
      <a-tab-pane key="mine">
        <template #title>
          <span class="tab-title-with-badge">
            {{ t('workflow.tab_my_submitted') }}
            <NavBadge :count="badges.mineUnreadCount" inline />
          </span>
        </template>
        <div class="instances-panel instances-panel--mine app-card" :class="{ 'instances-panel--flush': isDesktop }">
          <WorkflowInstanceList
            :rows="displayMineRows"
            :loading="loadingMine"
            row-key="public_uuid"
            :columns="{
              sector: false,
              applicant: false,
              department: false,
              updatedAt: true,
            }"
            :submitted-at-title="t('workflow.col_started_at')"
            :updated-at-title="t('workflow.col_status_updated_at')"
            :sort-field="mineSort.sortField.value"
            :sort-direction="mineSort.sortDirection.value"
            :row-class="mineRowClass"
            :mobile-card-class="mineMobileCardClass"
            @row-click="goDetail"
            @sorter-change="onMineSorterChange"
          >
            <template #display-no-prefix="{ record }">
              <span
                v-if="record.has_unread_update"
                class="instances-unread-dot"
                :title="t('workflow.update_badge')"
              />
            </template>
            <template #flow-extra="{ record }">
              <a-tag v-if="record.is_latest_update" color="arcoblue" size="small">
                {{ t('workflow.latest_update_badge') }}
              </a-tag>
            </template>
            <template #actions="{ record }">
              <a-space @click.stop>
                <a-button
                  v-if="record.status === 'draft'"
                  type="primary"
                  size="small"
                  @click.stop="continueDraft(record)"
                >
                  {{ t('apply.continue_draft') }}
                </a-button>
                <template v-else>
                  <a-popconfirm
                    v-if="record.can_withdraw"
                    :content="withdrawConfirmText(record)"
                    @ok="withdraw(record)"
                  >
                    <a-button type="outline" status="warning" size="small">
                      {{ t('workflow.withdraw') }}
                    </a-button>
                  </a-popconfirm>
                  <a-button type="outline" size="small" @click.stop="resubmit(record)">
                    {{ t('workflow.resubmit') }}
                  </a-button>
                </template>
              </a-space>
            </template>
          </WorkflowInstanceList>
        </div>
      </a-tab-pane>

      <a-tab-pane key="participated">
        <template #title>
          <span class="tab-title-with-badge">
            {{ t('workflow.tab_participated') }}
            <NavBadge :count="badges.participatedPendingCount" inline />
          </span>
        </template>
        <div class="instances-panel app-card" :class="{ 'instances-panel--flush': isDesktop }">
          <WorkflowInstanceList
            :rows="displayParticipatedRows"
            :loading="loadingParticipated"
            row-key="public_uuid"
            :columns="{
              sector: false,
              department: false,
              actions: false,
            }"
            :submitted-at-title="t('workflow.col_started_at')"
            :sort-field="participatedSort.sortField.value"
            :sort-direction="participatedSort.sortDirection.value"
            @row-click="goDetail"
            @sorter-change="onParticipatedSorterChange"
          >
            <template #mobile-extra="{ record }">
              <div v-if="record.my_task_status" class="instances-mobile-meta">
                {{ formatMyTaskStatus(record.my_task_status, t) }}
                <template v-if="record.my_completed_at">
                  · {{ formatDateTime(record.my_completed_at) }}
                </template>
              </div>
            </template>
            <template #extra-columns>
              <a-table-column :title="t('workflow.col_my_action')" :width="108">
                <template #cell="{ record }">
                  {{ formatMyTaskStatus(record.my_task_status, t) }}
                </template>
              </a-table-column>
              <a-table-column :title="t('workflow.col_my_handled_at')" :width="158">
                <template #cell="{ record }">{{ formatDateTime(record.my_completed_at) }}</template>
              </a-table-column>
            </template>
          </WorkflowInstanceList>
        </div>
      </a-tab-pane>
    </a-tabs>
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api, type ApiResponse } from '@/api/client'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { useInstanceListSort } from '@/composables/useInstanceListSort'
import PageChrome from '@/components/layout/PageChrome.vue'
import WorkflowInstanceList from '@/components/workflow/WorkflowInstanceList.vue'
import { formatMyTaskStatus } from '@/composables/useWorkflowLabels'
import { formatDateTime } from '@/utils/dateTime'
import { useWorkflowBadgesStore } from '@/stores/workflowBadges'
import NavBadge from '@/components/NavBadge.vue'
import type { WorkflowInstanceListRow } from '@/types/workflowInstanceList'

type InstanceRow = WorkflowInstanceListRow

const { t } = useI18n()
const router = useRouter()
const { isDesktop } = useBreakpoint()
const badges = useWorkflowBadgesStore()
const mineSort = useInstanceListSort('updated_at')
const participatedSort = useInstanceListSort('started_at')
const activeTab = ref<'mine' | 'participated'>('mine')
const mineRows = ref<InstanceRow[]>([])
const participatedRows = ref<InstanceRow[]>([])
const loadingMine = ref(false)
const loadingParticipated = ref(false)
const participatedLoaded = ref(false)

const pageDesc = computed(() =>
  activeTab.value === 'mine' ? t('workflow.my_instances_desc') : t('workflow.participated_desc'),
)

const displayMineRows = computed(() => mineSort.sortRowsClient(mineRows.value))
const displayParticipatedRows = computed(() => participatedSort.sortRowsClient(participatedRows.value))

function goDetail(record: InstanceRow) {
  if (record.status === 'draft') {
    continueDraft(record)
    return
  }
  router.push({ name: 'instance-detail', params: { uuid: record.public_uuid } })
}

function continueDraft(record: InstanceRow) {
  router.push({
    name: 'apply-start',
    query: {
      def: String(record.definition_id),
      draft: record.public_uuid,
      title: record.definition_name || '',
    },
  })
}

function withdrawConfirmText(record: InstanceRow) {
  return record.status === 'approved'
    ? t('workflow.withdraw_confirm_approved')
    : t('workflow.withdraw_confirm')
}

function mineRowClass(record: InstanceRow) {
  return record.has_unread_update ? 'instances-row--unread' : ''
}

function mineMobileCardClass(record: InstanceRow) {
  return record.has_unread_update ? 'instances-mobile-card--unread' : ''
}

async function loadMine() {
  loadingMine.value = true
  try {
    const res = await api.get<ApiResponse<InstanceRow[]>>('/workflow/instances', {
      params: { mine: 1, ...mineSort.sortQueryParams() },
    })
    if (res.data.ok) mineRows.value = res.data.data
    void badges.refresh(true)
  } finally {
    loadingMine.value = false
  }
}

async function loadParticipated() {
  loadingParticipated.value = true
  try {
    const res = await api.get<ApiResponse<InstanceRow[]>>('/workflow/instances', {
      params: { participated: 1, ...participatedSort.sortQueryParams() },
    })
    if (res.data.ok) {
      participatedRows.value = res.data.data
      participatedLoaded.value = true
    } else {
      Message.error(res.data.message || '加载失败')
    }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loadingParticipated.value = false
  }
}

function onMineSorterChange(dataIndex: string, direction: '' | 'ascend' | 'descend') {
  mineSort.onSorterChange(dataIndex, direction)
  if (mineSort.sortField.value === 'total_amount') return
  void loadMine()
}

function onParticipatedSorterChange(dataIndex: string, direction: '' | 'ascend' | 'descend') {
  participatedSort.onSorterChange(dataIndex, direction)
  if (participatedSort.sortField.value === 'total_amount') return
  void loadParticipated()
}

function onTabChange(key: string | number) {
  if (key === 'participated' && !participatedLoaded.value) {
    loadParticipated()
  }
}

async function withdraw(record: InstanceRow) {
  try {
    const res = await api.post<ApiResponse<InstanceRow>>(
      `/workflow/instances/${record.public_uuid}/withdraw`,
    )
    if (res.data.ok) {
      Message.success(res.data.message || t('workflow.withdraw_ok'))
      await loadMine()
    } else {
      Message.error(res.data.message || '撤回失败')
    }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '撤回失败')
  }
}

function resubmit(record: InstanceRow) {
  router.push({
    name: 'apply-start',
    query: {
      from: record.public_uuid,
      def: String(record.definition_id),
      title: record.definition_name || '',
    },
  })
}

onMounted(() => {
  loadMine()
  void badges.refresh()
})

onActivated(() => {
  if (activeTab.value === 'mine') void loadMine()
  else if (activeTab.value === 'participated') void loadParticipated()
})
</script>

<style scoped>
.tab-title-with-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.instances-tabs :deep(.arco-tabs-content) {
  padding-top: 12px;
}

.instances-panel {
  overflow: hidden;
  padding: 0.25rem 0;
}

.instances-panel--flush :deep(.arco-table-th) {
  background: var(--surface-muted) !important;
  font-weight: 600;
  color: var(--text-secondary);
}

.instances-panel--mine :deep(.arco-table-td:last-child) {
  text-align: right;
}

.instances-panel--mine :deep(.arco-table-tr.instances-row--unread) {
  background: rgba(80, 52, 255, 0.04);
}

.instances-unread-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f53f3f;
}

.instances-mobile-card--unread {
  border-color: rgba(245, 63, 63, 0.35) !important;
  background: rgba(80, 52, 255, 0.03);
}

.instances-mobile-meta {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.45;
}
</style>
