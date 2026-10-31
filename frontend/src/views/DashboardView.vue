<template>
  <PageChrome :title="t('menu.dashboard')" :description="welcomeLine">
    <template #actions>
      <a-button type="primary" @click="goApply">
        <template #icon><icon-plus /></template>
        {{ t('menu.apply') }}
      </a-button>
      <a-button @click="goTasks">{{ t('workflow.todo') }}</a-button>
    </template>

    <section class="dash-metrics">
      <router-link
        v-for="metric in metrics"
        :key="metric.key"
        :to="metric.to"
        class="dash-metric"
        :class="`dash-metric--${metric.tone}`"
      >
        <span class="dash-metric-head">
          <span class="dash-metric-label">{{ metric.label }}</span>
          <span class="dash-metric-icon">
            <component :is="metric.icon" />
          </span>
        </span>
        <span class="dash-metric-value tabular-nums">{{ metric.value }}</span>
      </router-link>
    </section>

    <div class="dash-columns">
      <section class="dash-panel app-card">
        <header class="dash-panel-head">
          <div class="dash-panel-title">
            <h2>{{ t('workflow.todo') }}</h2>
            <span v-if="todoTotal" class="dash-panel-count">{{ todoTotal }}</span>
          </div>
          <router-link :to="{ name: 'tasks' }" class="dash-link">
            {{ t('workflow.tasks_view') }}
            <icon-right />
          </router-link>
        </header>

        <div v-if="loading" class="dash-loading"><a-spin /></div>
        <ul v-else-if="todoRows.length" class="dash-todo-list">
          <li v-for="row in todoRows" :key="row.task_id">
            <button type="button" class="dash-todo" @click="goTask(row)">
              <span class="dash-todo-dot" aria-hidden="true" />
              <span class="dash-todo-main">
                <span class="dash-todo-title">{{ row.definition_name || row.display_no }}</span>
                <span class="dash-todo-meta">
                  <span v-if="row.node_name || row.current_node_label">
                    {{ t('workflow.col_node') }} · {{ row.node_name || row.current_node_label }}
                  </span>
                  <span v-if="row.display_no" class="dash-todo-no">{{ row.display_no }}</span>
                  <span v-if="row.task_created_at">{{ formatDateTime(row.task_created_at) }}</span>
                </span>
              </span>
              <icon-right class="dash-todo-arrow" />
            </button>
          </li>
        </ul>
        <a-empty v-else class="dash-empty" />

        <footer v-if="todoRows.length" class="dash-panel-foot">
          <router-link :to="{ name: 'tasks' }" class="dash-link">
            {{ t('workflow.tasks_view') }} ({{ todoTotal }})
            <icon-right />
          </router-link>
        </footer>
      </section>

      <div class="dash-side">
        <section class="dash-panel app-card">
          <header class="dash-panel-head">
            <div class="dash-panel-title">
              <h2>{{ t('menu.apply') }}</h2>
            </div>
            <router-link :to="{ name: 'apply' }" class="dash-link">
              {{ t('workflow.tasks_view') }}
              <icon-right />
            </router-link>
          </header>

          <div v-if="quickItems.length" class="dash-quick">
            <button
              v-for="item in quickItems"
              :key="`${item.form_key}-${item.workflow_definition_id}`"
              type="button"
              class="dash-quick-item"
              @click="openProcess(item)"
            >
              <ProcessIcon :icon="item.icon" :size="34" />
              <span class="dash-quick-name">{{ item.form_name }}</span>
              <icon-right class="dash-quick-arrow" />
            </button>
          </div>
          <p v-else-if="!loading" class="dash-quick-empty">{{ t('apply.catalog_empty') }}</p>
        </section>

        <section v-if="membershipLine" class="dash-panel dash-membership app-card">
          <h2 class="dash-membership-title">{{ t('dashboard.membership_title') }}</h2>
          <p class="dash-membership-text">{{ membershipLine }}</p>
        </section>
      </div>
    </div>

    <section class="dash-panel app-card dash-recent">
      <header class="dash-panel-head">
        <div class="dash-panel-title">
          <h2>{{ t('workflow.tab_my_submitted') }}</h2>
        </div>
        <router-link :to="{ name: 'my-instances' }" class="dash-link">
          {{ t('workflow.tasks_view') }}
          <icon-right />
        </router-link>
      </header>

      <ul v-if="recentRows.length" class="dash-recent-list">
        <li v-for="row in recentRows" :key="row.public_uuid">
          <button type="button" class="dash-recent-row" @click="goInstance(row)">
            <span class="dash-recent-main">
              <span class="dash-recent-title">{{ row.definition_name || row.display_no }}</span>
              <span class="dash-recent-meta">
                <span v-if="row.display_no">{{ row.display_no }}</span>
                <span v-if="row.started_at">{{ formatDateTime(row.started_at) }}</span>
              </span>
            </span>
            <span v-if="row.total_amount != null" class="dash-recent-amount tabular-nums">
              {{ formatAmount(row) }}
            </span>
            <StatusPill :status="row.status" :label="formatInstanceListStatus(row, t)" />
            <icon-right class="dash-recent-arrow" />
          </button>
        </li>
      </ul>
      <a-empty v-else class="dash-empty" />
    </section>
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  IconPlus,
  IconRight,
  IconCalendarClock,
  IconFile,
  IconUserGroup,
  IconNotification,
} from '@arco-design/web-vue/es/icon'
import { api, type ApiResponse } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowBadgesStore } from '@/stores/workflowBadges'
import PageChrome from '@/components/layout/PageChrome.vue'
import ProcessIcon from '@/components/apply/ProcessIcon.vue'
import StatusPill from '@/components/workflow/StatusPill.vue'
import { formatInstanceListStatus } from '@/composables/useWorkflowLabels'
import { formatDateTime } from '@/utils/dateTime'
import type { WorkflowInstanceListRow } from '@/types/workflowInstanceList'
import type { TaskListPageResult, WorkflowTaskListRow } from '@/types/workflowTaskList'

interface CatalogItem {
  form_key: string
  form_name: string
  workflow_definition_id: number
  description?: string
  icon?: string
}

interface CatalogGroup {
  sector_name: string
  items: CatalogItem[]
}

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const badges = useWorkflowBadgesStore()

const todoRows = ref<WorkflowTaskListRow[]>([])
const todoTotal = ref(0)
const mineRows = ref<WorkflowInstanceListRow[]>([])
const quickItems = ref<CatalogItem[]>([])
const loading = ref(true)

const welcomeLine = computed(() => {
  const name = auth.user?.display_name || ''
  return name ? t('dashboard.welcome_named', { name }) : t('dashboard.welcome_anon')
})

const membershipLine = computed(() => {
  const m = auth.user?.memberships
  if (!m?.length) return ''
  return m.map((x) => `${x.company_name} / ${x.department_name}`).join('、')
})

const metrics = computed(() => [
  {
    key: 'todo',
    label: t('workflow.todo'),
    value: Math.max(todoTotal.value, badges.todoCount),
    tone: 'brand',
    icon: IconCalendarClock,
    to: { name: 'tasks' },
  },
  {
    key: 'mine',
    label: t('workflow.tab_my_submitted'),
    value: mineRows.value.length,
    tone: 'neutral',
    icon: IconFile,
    to: { name: 'my-instances' },
  },
  {
    key: 'participated',
    label: t('workflow.tab_participated'),
    value: badges.participatedPendingCount,
    tone: 'neutral',
    icon: IconUserGroup,
    to: { name: 'my-instances' },
  },
  {
    key: 'unread',
    label: t('workflow.update_badge'),
    value: badges.mineUnreadCount,
    tone: badges.mineUnreadCount > 0 ? 'warning' : 'neutral',
    icon: IconNotification,
    to: { name: 'my-instances' },
  },
])

const recentRows = computed(() =>
  [...mineRows.value]
    .sort(
      (a, b) =>
        new Date(b.updated_at || b.started_at || 0).getTime() -
        new Date(a.updated_at || a.started_at || 0).getTime(),
    )
    .slice(0, 5),
)

function goApply() {
  router.push({ name: 'apply' })
}

function goTasks() {
  router.push({ name: 'tasks' })
}

function goTask(row: WorkflowTaskListRow) {
  router.push({ name: 'task-detail', params: { id: String(row.task_id) } })
}

function goInstance(row: WorkflowInstanceListRow) {
  if (row.status === 'draft') {
    router.push({
      name: 'apply-start',
      query: {
        def: String(row.definition_id),
        draft: row.public_uuid,
        title: row.definition_name || '',
      },
    })
    return
  }
  router.push({ name: 'instance-detail', params: { uuid: row.public_uuid } })
}

function openProcess(item: CatalogItem) {
  router.push({
    name: 'apply-start',
    query: {
      def: String(item.workflow_definition_id),
      key: item.form_key,
      title: item.form_name,
    },
  })
}

function formatAmount(row: WorkflowInstanceListRow) {
  const n = Number(row.total_amount)
  if (!Number.isFinite(n)) return ''
  const currency = row.amount_currency || 'CNY'
  return `${currency === 'CNY' ? '¥' : `${currency} `}${n.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

async function loadDashboard() {
  loading.value = true
  try {
    const [todoRes, mineRes, catalogRes] = await Promise.allSettled([
      api.get<ApiResponse<TaskListPageResult>>('/workflow/tasks/todo', {
        params: { page: 1, page_size: 5 },
      }),
      api.get<ApiResponse<WorkflowInstanceListRow[]>>('/workflow/instances', {
        params: { mine: 1 },
      }),
      api.get<ApiResponse<CatalogGroup[]>>('/forms/applications-catalog'),
    ])

    if (todoRes.status === 'fulfilled' && todoRes.value.data.ok) {
      todoRows.value = todoRes.value.data.data.items
      todoTotal.value = todoRes.value.data.data.total
    }
    if (mineRes.status === 'fulfilled' && mineRes.value.data.ok) {
      mineRows.value = mineRes.value.data.data
    }
    if (catalogRes.status === 'fulfilled' && catalogRes.value.data.ok) {
      quickItems.value = catalogRes.value.data.data
        .flatMap((g) => g.items)
        .slice(0, 4)
    }
    void badges.refresh(true)
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<style scoped>
.dash-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

@media (min-width: 900px) {
  .dash-metrics {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.dash-metric {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px 15px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  color: inherit;
  text-decoration: none;
  transition:
    border-color var(--dur-base) var(--ease-out),
    box-shadow var(--dur-base) var(--ease-out);
}

.dash-metric:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-sm);
}

.dash-metric-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.dash-metric-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.dash-metric-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--radius-md);
  background: var(--surface-muted);
  color: var(--text-secondary);
  font-size: 14px;
}

.dash-metric--brand .dash-metric-icon {
  background: var(--brand-soft);
  color: var(--brand);
}

.dash-metric--warning .dash-metric-icon {
  background: var(--warning-soft);
  color: var(--warning);
}

.dash-metric-value {
  font-size: 1.75rem;
  font-weight: 650;
  line-height: 1.1;
  letter-spacing: -0.03em;
  color: var(--text);
}

.dash-metric--brand .dash-metric-value {
  color: var(--brand);
}

.dash-metric--warning .dash-metric-value {
  color: var(--warning);
}

.dash-columns {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
  margin-bottom: 14px;
}

@media (min-width: 1024px) {
  .dash-columns {
    grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
  }
}

.dash-side {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.dash-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 0;
  overflow: hidden;
}

.dash-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--divider);
}

.dash-panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.dash-panel-title h2 {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text);
}

.dash-panel-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--radius-pill);
  background: var(--brand-soft);
  color: var(--brand);
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.dash-link {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-tertiary);
  text-decoration: none;
  white-space: nowrap;
  transition: color var(--dur-fast) var(--ease-out);
}

.dash-link:hover {
  color: var(--brand);
}

.dash-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 160px;
}

.dash-empty {
  padding: 24px 0;
}

.dash-todo-list,
.dash-recent-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.dash-todo-list li + li,
.dash-recent-list li + li {
  border-top: 1px solid var(--divider);
}

.dash-todo {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background-color var(--dur-fast) var(--ease-out);
}

.dash-todo:hover,
.dash-recent-row:hover {
  background: var(--brand-softer);
}

.dash-todo-dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand);
}

.dash-todo-main {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
}

.dash-todo-title {
  overflow: hidden;
  font-size: 0.875rem;
  font-weight: 550;
  color: var(--text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dash-todo-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.dash-todo-no {
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  background: var(--surface-muted);
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.dash-todo-arrow,
.dash-recent-arrow,
.dash-quick-arrow {
  flex-shrink: 0;
  color: var(--text-disabled);
  font-size: 12px;
}

.dash-panel-foot {
  padding: 10px 16px;
  border-top: 1px solid var(--divider);
  text-align: right;
}

.dash-quick {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 12px;
}

.dash-quick-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  cursor: pointer;
  text-align: left;
  transition:
    border-color var(--dur-fast) var(--ease-out),
    background-color var(--dur-fast) var(--ease-out);
}

.dash-quick-item:hover {
  border-color: #d9d2ff;
  background: var(--brand-softer);
}

.dash-quick-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dash-quick-arrow {
  display: none;
}

.dash-quick-empty {
  margin: 0;
  padding: 20px 16px;
  font-size: 0.75rem;
  color: var(--text-tertiary);
  text-align: center;
}

.dash-membership {
  padding: 14px 16px;
}

.dash-membership-title {
  margin: 0 0 6px;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text);
}

.dash-membership-text {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.dash-recent-row {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background-color var(--dur-fast) var(--ease-out);
}

.dash-recent-main {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
}

.dash-recent-title {
  overflow: hidden;
  font-size: 0.875rem;
  font-weight: 550;
  color: var(--text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dash-recent-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 0.75rem;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.dash-recent-amount {
  flex-shrink: 0;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text);
}

@media (max-width: 640px) {
  .dash-recent-amount {
    display: none;
  }

  .dash-recent-row {
    gap: 10px;
  }
}
</style>
