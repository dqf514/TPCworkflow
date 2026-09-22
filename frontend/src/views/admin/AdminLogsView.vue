<template>
  <PageChrome :title="t('adminLogs.title')" :description="t('adminLogs.desc')">
    <template #actions>
      <a-button :loading="loadingSummary" @click="loadSummary">{{ t('adminLogs.refresh') }}</a-button>
    </template>

    <div v-if="summary" class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      <a-card class="rounded-xl" :bordered="false">
        <div class="text-xs text-gray-500">{{ t('adminLogs.summary_auth') }}</div>
        <div class="text-lg font-semibold mt-1">
          <span class="text-green-600">{{ summary.auth_24h.success }}</span>
          <span class="text-gray-400 mx-1">/</span>
          <span class="text-red-500">{{ summary.auth_24h.failed }}</span>
          <span class="text-xs text-gray-400 ml-1">({{ t('adminLogs.success') }}/{{ t('adminLogs.failed') }})</span>
        </div>
      </a-card>
      <a-card class="rounded-xl" :bordered="false">
        <div class="text-xs text-gray-500">{{ t('adminLogs.summary_access') }}</div>
        <div class="text-lg font-semibold mt-1">{{ summary.access_24h }}</div>
      </a-card>
      <a-card class="rounded-xl" :bordered="false">
        <div class="text-xs text-gray-500">{{ t('adminLogs.summary_workflow') }}</div>
        <div class="text-lg font-semibold mt-1">{{ summary.workflow_24h }}</div>
      </a-card>
      <a-card class="rounded-xl" :bordered="false">
        <div class="text-xs text-gray-500">{{ t('adminLogs.summary_email') }}</div>
        <div class="text-lg font-semibold mt-1">
          <span class="text-green-600">{{ summary.email_24h.sent }}</span>
          <span class="text-gray-400 mx-1">/</span>
          <span class="text-red-500">{{ summary.email_24h.failed }}</span>
        </div>
      </a-card>
    </div>

    <a-alert
      v-if="summary?.recent_email_failures?.length"
      type="warning"
      class="mb-4 rounded-xl"
      :title="t('adminLogs.recent_failures')"
    >
      <ul class="text-sm space-y-1">
        <li v-for="f in summary.recent_email_failures" :key="f.id">
          {{ formatDateTime(f.created_at) }} · {{ f.mail_type_label }} · {{ f.recipient }} — {{ f.error_message }}
        </li>
      </ul>
    </a-alert>

    <a-tabs v-model:active-key="tab" type="rounded" class="logs-tabs" @change="onTabChange">
      <a-tab-pane key="auth" :title="t('adminLogs.tab_auth')">
        <div class="flex flex-wrap gap-2 mb-3">
          <a-select v-model="authCategory" :options="authCategoryOpts" class="w-36" @change="reloadAuth" />
          <a-select v-model="authStatus" :options="statusOpts" class="w-32" @change="reloadAuth" />
          <a-input-search
            v-model="keyword"
            class="w-56"
            :placeholder="t('adminLogs.keyword_ph')"
            allow-clear
            @search="reloadAuth"
            @clear="reloadAuth"
          />
          <a-date-picker
            v-model="dateFrom"
            show-time
            format="YYYY-MM-DD HH:mm:ss"
            :placeholder="t('adminLogs.date_from')"
            class="w-48"
            @change="reloadAuth"
          />
          <a-date-picker
            v-model="dateTo"
            show-time
            format="YYYY-MM-DD HH:mm:ss"
            :placeholder="t('adminLogs.date_to')"
            class="w-48"
            @change="reloadAuth"
          />
          <a-popconfirm
            :content="t('adminLogs.delete_selected_confirm', { count: authSelectedKeys.length })"
            @ok="deleteSelected('auth')"
          >
            <a-button
              status="danger"
              :disabled="!authSelectedKeys.length"
              :loading="deletingAuth"
            >
              {{ t('adminLogs.delete_selected', { count: authSelectedKeys.length }) }}
            </a-button>
          </a-popconfirm>
          <a-popconfirm :content="deleteAllConfirmText('auth')" @ok="deleteAllFiltered('auth')">
            <a-button
              status="danger"
              type="outline"
              :disabled="!authTotal"
              :loading="deletingAuthAll"
            >
              {{ t('adminLogs.delete_all_filtered') }}
            </a-button>
          </a-popconfirm>
        </div>
        <a-table
          v-model:selected-keys="authSelectedKeys"
          :data="authRows"
          :loading="loadingAuth"
          row-key="id"
          :pagination="authPagination"
          :row-selection="rowSelection"
          @page-change="onAuthPage"
          @page-size-change="onAuthPageSize"
        >
          <template #columns>
            <a-table-column :title="t('adminLogs.col_time')" :width="170">
              <template #cell="{ record }">{{ formatDateTime(record.created_at) }}</template>
            </a-table-column>
            <a-table-column :title="t('adminLogs.col_event')" :width="140">
              <template #cell="{ record }">
                {{ record.event_label }}
              </template>
            </a-table-column>
            <a-table-column :title="t('adminLogs.col_user')" :width="140">
              <template #cell="{ record }">
                {{ record.user_name || record.subject || '—' }}
              </template>
            </a-table-column>
            <a-table-column :title="t('adminLogs.col_ip')" data-index="ip_address" :width="120" />
            <a-table-column :title="t('adminLogs.col_path')" :ellipsis="true">
              <template #cell="{ record }">
                <span v-if="record.event_type === 'page_view'">{{ record.request_path || '—' }}</span>
                <span v-else>
                  <span v-if="record.request_method" class="text-xs text-gray-400">{{ record.request_method }}</span>
                  {{ record.request_path || '—' }}
                </span>
              </template>
            </a-table-column>
            <a-table-column :title="t('adminLogs.col_status')" :width="80">
              <template #cell="{ record }">
                <a-tag :color="record.status === 'success' ? 'green' : 'red'" size="small">
                  {{ record.status === 'success' ? t('adminLogs.success') : t('adminLogs.failed') }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column :title="t('adminLogs.col_message')" :ellipsis="true">
              <template #cell="{ record }">
                {{ record.message || '—' }}
              </template>
            </a-table-column>
          </template>
        </a-table>
        <p class="text-xs text-gray-400 mt-2">{{ totalHint(authTotal) }}</p>
      </a-tab-pane>

      <a-tab-pane key="workflow" :title="t('adminLogs.tab_workflow')">
        <div class="flex flex-wrap gap-2 mb-3">
          <a-select v-model="wfAction" :options="wfActionOpts" class="w-36" @change="reloadWf" />
          <a-input-search
            v-model="keyword"
            class="w-56"
            :placeholder="t('adminLogs.keyword_ph')"
            allow-clear
            @search="reloadWf"
            @clear="reloadWf"
          />
          <a-date-picker
            v-model="dateFrom"
            show-time
            format="YYYY-MM-DD HH:mm:ss"
            :placeholder="t('adminLogs.date_from')"
            class="w-48"
            @change="reloadWf"
          />
          <a-date-picker
            v-model="dateTo"
            show-time
            format="YYYY-MM-DD HH:mm:ss"
            :placeholder="t('adminLogs.date_to')"
            class="w-48"
            @change="reloadWf"
          />
          <a-popconfirm
            :content="t('adminLogs.delete_selected_confirm', { count: wfSelectedKeys.length })"
            @ok="deleteSelected('workflow')"
          >
            <a-button
              status="danger"
              :disabled="!wfSelectedKeys.length"
              :loading="deletingWf"
            >
              {{ t('adminLogs.delete_selected', { count: wfSelectedKeys.length }) }}
            </a-button>
          </a-popconfirm>
          <a-popconfirm :content="deleteAllConfirmText('workflow')" @ok="deleteAllFiltered('workflow')">
            <a-button
              status="danger"
              type="outline"
              :disabled="!wfTotal"
              :loading="deletingWfAll"
            >
              {{ t('adminLogs.delete_all_filtered') }}
            </a-button>
          </a-popconfirm>
        </div>
        <a-table
          v-model:selected-keys="wfSelectedKeys"
          :data="wfRows"
          :loading="loadingWf"
          row-key="id"
          :pagination="wfPagination"
          :row-selection="rowSelection"
          @page-change="onWfPage"
          @page-size-change="onWfPageSize"
        >
          <template #columns>
            <a-table-column :title="t('adminLogs.col_time')" :width="170">
              <template #cell="{ record }">{{ formatDateTime(record.created_at) }}</template>
            </a-table-column>
            <a-table-column :title="t('adminLogs.col_instance')" data-index="display_no" :width="120" />
            <a-table-column :title="t('adminLogs.col_flow')" data-index="definition_name" />
            <a-table-column :title="t('adminLogs.col_actor')" data-index="actor_name" :width="100" />
            <a-table-column :title="t('adminLogs.col_action')" :width="90">
              <template #cell="{ record }">
                {{ actionLabel(record.action) }}
              </template>
            </a-table-column>
            <a-table-column :title="t('adminLogs.col_node')" data-index="node_id" :width="100" />
            <a-table-column :title="t('adminLogs.col_comment')" data-index="comment" :ellipsis="true" />
            <a-table-column :title="t('adminLogs.col_actions')" :width="100" align="right">
              <template #cell="{ record }">
                <a-button type="text" size="mini" @click="goInstance(record.public_uuid)">
                  {{ t('adminLogs.goto_instance') }}
                </a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
        <p class="text-xs text-gray-400 mt-2">{{ totalHint(wfTotal) }}</p>
      </a-tab-pane>

      <a-tab-pane key="email" :title="t('adminLogs.tab_email')">
        <div class="flex flex-wrap gap-2 mb-3">
          <a-select v-model="mailType" :options="mailTypeOpts" class="w-44" @change="reloadMail" />
          <a-select v-model="mailStatus" :options="mailStatusOpts" class="w-32" @change="reloadMail" />
          <a-input-search
            v-model="keyword"
            class="w-56"
            :placeholder="t('adminLogs.keyword_ph')"
            allow-clear
            @search="reloadMail"
            @clear="reloadMail"
          />
          <a-date-picker
            v-model="dateFrom"
            show-time
            format="YYYY-MM-DD HH:mm:ss"
            :placeholder="t('adminLogs.date_from')"
            class="w-48"
            @change="reloadMail"
          />
          <a-date-picker
            v-model="dateTo"
            show-time
            format="YYYY-MM-DD HH:mm:ss"
            :placeholder="t('adminLogs.date_to')"
            class="w-48"
            @change="reloadMail"
          />
          <a-popconfirm
            :content="t('adminLogs.delete_selected_confirm', { count: mailSelectedKeys.length })"
            @ok="deleteSelected('email')"
          >
            <a-button
              status="danger"
              :disabled="!mailSelectedKeys.length"
              :loading="deletingMail"
            >
              {{ t('adminLogs.delete_selected', { count: mailSelectedKeys.length }) }}
            </a-button>
          </a-popconfirm>
          <a-popconfirm :content="deleteAllConfirmText('email')" @ok="deleteAllFiltered('email')">
            <a-button
              status="danger"
              type="outline"
              :disabled="!mailTotal"
              :loading="deletingMailAll"
            >
              {{ t('adminLogs.delete_all_filtered') }}
            </a-button>
          </a-popconfirm>
        </div>
        <a-table
          v-model:selected-keys="mailSelectedKeys"
          :data="mailRows"
          :loading="loadingMail"
          row-key="id"
          :pagination="mailPagination"
          :row-selection="rowSelection"
          @page-change="onMailPage"
          @page-size-change="onMailPageSize"
        >
          <template #columns>
            <a-table-column :title="t('adminLogs.col_time')" :width="170">
              <template #cell="{ record }">{{ formatDateTime(record.created_at) }}</template>
            </a-table-column>
            <a-table-column :title="t('adminLogs.col_type')" data-index="mail_type_label" :width="180" />
            <a-table-column :title="t('adminLogs.col_channel')" data-index="channel" :width="72" />
            <a-table-column :title="t('adminLogs.col_recipient')" data-index="recipient" :width="160" />
            <a-table-column :title="t('adminLogs.col_subject')" data-index="subject" :ellipsis="true" />
            <a-table-column :title="t('adminLogs.col_status')" :width="90">
              <template #cell="{ record }">
                <a-tag :color="mailStatusColor(record.status)" size="small">{{ record.status }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column :title="t('adminLogs.col_message')" data-index="error_message" :ellipsis="true" />
            <a-table-column :title="t('adminLogs.col_actions')" :width="90" align="right">
              <template #cell="{ record }">
                <a-button type="text" size="mini" @click="openBody(record)">
                  {{ t('adminLogs.view_body') }}
                </a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
        <p class="text-xs text-gray-400 mt-2">{{ totalHint(mailTotal) }}</p>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:visible="bodyVisible" :title="t('adminLogs.body_title')" width="720px" :footer="false">
      <pre class="text-sm whitespace-pre-wrap max-h-[60vh] overflow-auto">{{ bodyContent }}</pre>
    </a-modal>
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api, type ApiResponse } from '@/api/client'
import PageChrome from '@/components/layout/PageChrome.vue'
import { formatDateTime } from '@/utils/dateTime'
import { timelineActionLabel } from '@/utils/printFormat'

interface Summary {
  auth_24h: { success: number; failed: number }
  access_24h: number
  workflow_24h: number
  email_24h: { sent: number; failed: number }
  recent_email_failures: {
    id: number
    mail_type_label: string
    recipient?: string
    error_message?: string
    created_at?: string
  }[]
}

interface AuthRow {
  id: number
  event_type?: string
  event_label: string
  user_name?: string
  subject?: string
  ip_address?: string
  request_method?: string
  request_path?: string
  status: string
  message?: string
  created_at: string
}

interface WfRow {
  id: number
  instance_id: number
  public_uuid?: string
  display_no: string
  definition_name: string
  actor_name: string
  action: string
  node_id?: string
  comment?: string
  created_at: string
}

interface MailRow {
  id: number
  mail_type_label: string
  channel: string
  recipient?: string
  subject?: string
  body?: string
  status: string
  error_message?: string
  created_at: string
}

const { t } = useI18n()
const router = useRouter()

const tab = ref('auth')
const keyword = ref('')
const dateFrom = ref<string>()
const dateTo = ref<string>()

const summary = ref<Summary | null>(null)
const loadingSummary = ref(false)

const authCategory = ref('')
const authStatus = ref('')
const authRows = ref<AuthRow[]>([])
const authTotal = ref(0)
const authPage = ref(1)
const authPageSize = ref(20)
const loadingAuth = ref(false)

const wfAction = ref('')
const wfRows = ref<WfRow[]>([])
const wfTotal = ref(0)
const wfPage = ref(1)
const wfPageSize = ref(20)
const loadingWf = ref(false)

const mailType = ref('')
const mailStatus = ref('')
const mailRows = ref<MailRow[]>([])
const mailTotal = ref(0)
const mailPage = ref(1)
const mailPageSize = ref(20)
const loadingMail = ref(false)

const bodyVisible = ref(false)
const bodyContent = ref('')

type LogKind = 'auth' | 'workflow' | 'email'

const authSelectedKeys = ref<Array<string | number>>([])
const wfSelectedKeys = ref<Array<string | number>>([])
const mailSelectedKeys = ref<Array<string | number>>([])

const deletingAuth = ref(false)
const deletingAuthAll = ref(false)
const deletingWf = ref(false)
const deletingWfAll = ref(false)
const deletingMail = ref(false)
const deletingMailAll = ref(false)

const rowSelection = {
  type: 'checkbox',
  showCheckedAll: true,
  onlyCurrent: true,
}

const authCategoryOpts = computed(() => [
  { label: t('adminLogs.category_all'), value: '' },
  { label: t('adminLogs.category_auth'), value: 'auth' },
  { label: t('adminLogs.category_access'), value: 'access' },
])

const statusOpts = computed(() => [
  { label: t('adminLogs.status_all'), value: '' },
  { label: t('adminLogs.status_success'), value: 'success' },
  { label: t('adminLogs.status_fail'), value: 'fail' },
])

const wfActionOpts = computed(() => [
  { label: t('adminLogs.action_all'), value: '' },
  { label: timelineActionLabel('submit'), value: 'submit' },
  { label: timelineActionLabel('approve'), value: 'approve' },
  { label: timelineActionLabel('reject'), value: 'reject' },
  { label: timelineActionLabel('transfer'), value: 'transfer' },
  { label: timelineActionLabel('add_sign'), value: 'add_sign' },
  { label: timelineActionLabel('auto_approve'), value: 'auto_approve' },
  { label: timelineActionLabel('cancel'), value: 'cancel' },
])

const mailTypeOpts = computed(() => [
  { label: t('adminLogs.mail_type_all'), value: '' },
  { label: t('adminLogs.mail_login_code'), value: 'login_code' },
  { label: t('adminLogs.mail_sms_login'), value: 'sms_login' },
  { label: t('adminLogs.mail_approval'), value: 'approval_notify' },
  { label: t('adminLogs.mail_test'), value: 'test' },
])

const mailStatusOpts = computed(() => [
  { label: t('adminLogs.status_all'), value: '' },
  { label: t('adminLogs.sent'), value: 'sent' },
  { label: t('adminLogs.failed'), value: 'failed' },
  { label: 'dev_log', value: 'dev_log' },
])

const authPagination = computed(() => ({
  current: authPage.value,
  pageSize: authPageSize.value,
  total: authTotal.value,
  showTotal: true,
  showPageSize: true,
}))

const wfPagination = computed(() => ({
  current: wfPage.value,
  pageSize: wfPageSize.value,
  total: wfTotal.value,
  showTotal: true,
  showPageSize: true,
}))

const mailPagination = computed(() => ({
  current: mailPage.value,
  pageSize: mailPageSize.value,
  total: mailTotal.value,
  showTotal: true,
  showPageSize: true,
}))

function totalHint(n: number) {
  return t('adminLogs.total', { n })
}

function actionLabel(action: string) {
  return timelineActionLabel(action)
}

function mailStatusColor(status: string) {
  if (status === 'sent' || status === 'dev_log') return 'green'
  if (status === 'failed') return 'red'
  return 'gray'
}

function serializeDate(v: unknown): string | undefined {
  if (!v) return undefined
  if (typeof v === 'string') return v
  if (v instanceof Date) {
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${v.getFullYear()}-${pad(v.getMonth() + 1)}-${pad(v.getDate())} ${pad(v.getHours())}:${pad(v.getMinutes())}:${pad(v.getSeconds())}`
  }
  return String(v)
}

function queryBase() {
  const q: Record<string, string | number> = {}
  if (keyword.value.trim()) q.keyword = keyword.value.trim()
  const from = serializeDate(dateFrom.value)
  const to = serializeDate(dateTo.value)
  if (from) q.date_from = from
  if (to) q.date_to = to
  return q
}

function compactFilters(obj: Record<string, unknown>) {
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== null && String(v).trim() !== '') {
      out[k] = String(v).trim()
    }
  }
  return out
}

function authFilters() {
  return compactFilters({
    ...queryBase(),
    category: authCategory.value,
    status: authStatus.value,
  })
}

function wfFilters() {
  return compactFilters({
    ...queryBase(),
    action: wfAction.value,
  })
}

function mailFilters() {
  return compactFilters({
    ...queryBase(),
    mail_type: mailType.value,
    status: mailStatus.value,
  })
}

function deleteEndpoint(kind: LogKind) {
  if (kind === 'auth') return '/admin/logs/login-access/delete'
  if (kind === 'workflow') return '/admin/logs/workflow/delete'
  return '/admin/logs/notifications/delete'
}

function selectedKeysFor(kind: LogKind) {
  if (kind === 'auth') return authSelectedKeys
  if (kind === 'workflow') return wfSelectedKeys
  return mailSelectedKeys
}

function totalFor(kind: LogKind) {
  if (kind === 'auth') return authTotal.value
  if (kind === 'workflow') return wfTotal.value
  return mailTotal.value
}

function deletingFlagsFor(kind: LogKind, all = false) {
  if (kind === 'auth') return all ? deletingAuthAll : deletingAuth
  if (kind === 'workflow') return all ? deletingWfAll : deletingWf
  return all ? deletingMailAll : deletingMail
}

function filtersFor(kind: LogKind) {
  if (kind === 'auth') return authFilters()
  if (kind === 'workflow') return wfFilters()
  return mailFilters()
}

async function reloadKind(kind: LogKind) {
  if (kind === 'auth') await loadAuth()
  else if (kind === 'workflow') await loadWf()
  else await loadMail()
}

function deleteAllConfirmText(kind: LogKind) {
  const base = t('adminLogs.delete_all_confirm', { count: totalFor(kind) })
  if (kind === 'workflow') {
    return `${base}\n${t('adminLogs.delete_workflow_all_hint')}`
  }
  return base
}

async function deleteSelected(kind: LogKind) {
  const keysRef = selectedKeysFor(kind)
  if (!keysRef.value.length) {
    Message.warning(t('adminLogs.delete_none_selected'))
    return
  }
  const loadingRef = deletingFlagsFor(kind, false)
  loadingRef.value = true
  try {
    const res = await api.post<ApiResponse<{ deleted: number }>>(deleteEndpoint(kind), {
      ids: keysRef.value.map((k) => Number(k)),
    })
    if (res.data.ok) {
      const n = res.data.data?.deleted ?? keysRef.value.length
      Message.success(res.data.message || t('adminLogs.deleted', { count: n }))
      keysRef.value = []
      await reloadKind(kind)
      await loadSummary()
    } else {
      Message.error(res.data.message || t('adminLogs.delete_failed'))
    }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('adminLogs.delete_failed'))
  } finally {
    loadingRef.value = false
  }
}

async function deleteAllFiltered(kind: LogKind) {
  const total = totalFor(kind)
  if (!total) return false
  const loadingRef = deletingFlagsFor(kind, true)
  loadingRef.value = true
  try {
    const res = await api.post<ApiResponse<{ deleted: number }>>(deleteEndpoint(kind), {
      delete_all_filtered: true,
      filters: filtersFor(kind),
    })
    if (res.data.ok) {
      const n = res.data.data?.deleted ?? total
      Message.success(res.data.message || t('adminLogs.deleted', { count: n }))
      selectedKeysFor(kind).value = []
      await reloadKind(kind)
      await loadSummary()
      return true
    }
    Message.error(res.data.message || t('adminLogs.delete_failed'))
    return false
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('adminLogs.delete_failed'))
    return false
  } finally {
    loadingRef.value = false
  }
}

async function loadSummary() {
  loadingSummary.value = true
  try {
    const res = await api.get<ApiResponse<Summary>>('/admin/logs/summary')
    if (res.data.ok) summary.value = res.data.data
  } finally {
    loadingSummary.value = false
  }
}

async function loadAuth() {
  loadingAuth.value = true
  try {
    const res = await api.get<ApiResponse<{ items: AuthRow[]; total: number }>>('/admin/logs/login-access', {
      params: {
        ...queryBase(),
        page: authPage.value,
        page_size: authPageSize.value,
        category: authCategory.value || undefined,
        status: authStatus.value || undefined,
      },
    })
    if (res.data.ok) {
      authRows.value = res.data.data.items
      authTotal.value = res.data.data.total
    }
  } finally {
    loadingAuth.value = false
  }
}

async function loadWf() {
  loadingWf.value = true
  try {
    const res = await api.get<ApiResponse<{ items: WfRow[]; total: number }>>('/admin/logs/workflow', {
      params: {
        ...queryBase(),
        page: wfPage.value,
        page_size: wfPageSize.value,
        action: wfAction.value || undefined,
      },
    })
    if (res.data.ok) {
      wfRows.value = res.data.data.items
      wfTotal.value = res.data.data.total
    }
  } finally {
    loadingWf.value = false
  }
}

async function loadMail() {
  loadingMail.value = true
  try {
    const res = await api.get<ApiResponse<{ items: MailRow[]; total: number }>>('/admin/logs/notifications', {
      params: {
        ...queryBase(),
        page: mailPage.value,
        page_size: mailPageSize.value,
        mail_type: mailType.value || undefined,
        status: mailStatus.value || undefined,
      },
    })
    if (res.data.ok) {
      mailRows.value = res.data.data.items
      mailTotal.value = res.data.data.total
    }
  } finally {
    loadingMail.value = false
  }
}

function reloadAuth() {
  authPage.value = 1
  authSelectedKeys.value = []
  loadAuth()
}
function reloadWf() {
  wfPage.value = 1
  wfSelectedKeys.value = []
  loadWf()
}
function reloadMail() {
  mailPage.value = 1
  mailSelectedKeys.value = []
  loadMail()
}

function onTabChange(key: string | number) {
  if (key === 'auth') loadAuth()
  else if (key === 'workflow') loadWf()
  else loadMail()
}

function onAuthPage(p: number) {
  authPage.value = p
  authSelectedKeys.value = []
  loadAuth()
}
function onAuthPageSize(s: number) {
  authPageSize.value = s
  authPage.value = 1
  authSelectedKeys.value = []
  loadAuth()
}
function onWfPage(p: number) {
  wfPage.value = p
  wfSelectedKeys.value = []
  loadWf()
}
function onWfPageSize(s: number) {
  wfPageSize.value = s
  wfPage.value = 1
  wfSelectedKeys.value = []
  loadWf()
}
function onMailPage(p: number) {
  mailPage.value = p
  mailSelectedKeys.value = []
  loadMail()
}
function onMailPageSize(s: number) {
  mailPageSize.value = s
  mailPage.value = 1
  mailSelectedKeys.value = []
  loadMail()
}

function goInstance(uuid?: string) {
  if (!uuid) return
  router.push({ name: 'instance-detail', params: { uuid } })
}

function openBody(row: MailRow) {
  bodyContent.value = row.body || row.subject || '—'
  bodyVisible.value = true
}

onMounted(async () => {
  await loadSummary()
  await loadAuth()
})
</script>

<style scoped>
.logs-tabs :deep(.arco-tabs-content) {
  padding-top: 0.75rem;
}
</style>
