<template>
  <a-card class="settings-card" :bordered="false">
    <p class="i18n-panel-desc">{{ t('settings.i18n_panel_desc') }}</p>
    <p class="i18n-coverage-hint">{{ t('settings.i18n_coverage_hint') }}</p>

    <a-form layout="inline" class="i18n-filter-form">
      <a-form-item :label="t('settings.i18n_locale')">
        <a-select v-model="filter.locale" :options="localeOpts" style="width: 140px" @change="onLocaleChange" />
      </a-form-item>
      <a-form-item :label="t('settings.i18n_namespace')">
        <a-select
          v-model="filter.namespace"
          :options="namespaceOpts"
          allow-clear
          allow-search
          :placeholder="t('settings.i18n_namespace_all')"
          style="width: 160px"
          @change="onNamespaceChange"
        />
      </a-form-item>
      <a-form-item :label="t('settings.i18n_search')">
        <a-input v-model="filter.q" allow-clear :placeholder="t('settings.i18n_search_ph')" style="width: 200px" />
      </a-form-item>
      <a-form-item>
        <a-checkbox v-model="filter.emptyOnly">{{ t('settings.i18n_empty_only') }}</a-checkbox>
      </a-form-item>
      <a-form-item>
        <a-space wrap>
          <a-button type="primary" @click="onSearch">{{ t('settings.i18n_query') }}</a-button>
          <a-button type="outline" @click="openCreate">{{ t('settings.i18n_add_entry') }}</a-button>
          <a-button @click="keysDrawerVisible = true">{{ t('settings.i18n_browse_keys') }}</a-button>
          <a-button @click="publish">{{ t('settings.i18n_publish') }}</a-button>
        </a-space>
      </a-form-item>
    </a-form>

    <a-table
      :data="rows"
      :loading="loading"
      :row-key="rowKey"
      :pagination="pagination"
      :scroll="{ x: 1100 }"
      class="i18n-table"
      :row-class="rowClass"
      @page-change="onPageChange"
      @page-size-change="onPageSizeChange"
    >
      <template #columns>
        <a-table-column :title="t('settings.i18n_col_namespace')" data-index="namespace" :width="100" />
        <a-table-column :title="t('settings.i18n_col_key')" data-index="msg_key" :width="150" />
        <a-table-column :title="t('settings.i18n_col_value')" :width="280">
          <template #cell="{ record }">
            <a-textarea
              v-model="record.msg_value"
              :auto-size="{ minRows: 1, maxRows: 4 }"
              :placeholder="record.is_empty ? t('settings.i18n_value_ph') : ''"
              @blur="saveRow(record)"
            />
          </template>
        </a-table-column>
        <a-table-column :title="t('settings.i18n_col_ref')" :width="240">
          <template #cell="{ record }">
            <div class="ref-cell">
              <span class="ref-locale">{{ record.ref_locale }}</span>
              <span class="ref-text" :title="record.ref_value">{{ record.ref_value || '—' }}</span>
              <a-button
                v-if="record.ref_value"
                type="text"
                size="mini"
                @click="applyRef(record)"
              >
                {{ t('settings.i18n_use_ref') }}
              </a-button>
            </div>
          </template>
        </a-table-column>
        <a-table-column :title="t('settings.i18n_col_desc')" data-index="description" :width="120">
          <template #cell="{ record }">
            <span class="i18n-desc">{{ record.description || '—' }}</span>
          </template>
        </a-table-column>
        <a-table-column :title="t('settings.i18n_col_actions')" :width="140" fixed="right">
          <template #cell="{ record }">
            <a-space>
              <a-tag v-if="!record.in_db" size="small" color="orangered">{{ t('settings.i18n_not_in_db') }}</a-tag>
              <a-button size="mini" type="text" @click="openEdit(record)">{{ t('settings.action_edit') }}</a-button>
              <a-popconfirm
                v-if="record.id"
                :content="t('settings.i18n_delete_confirm')"
                @ok="removeRow(record)"
              >
                <a-button size="mini" type="text" status="danger">{{ t('settings.action_delete') }}</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>

    <a-modal
      v-model:visible="modalVisible"
      :title="editForm.id ? t('settings.i18n_edit_entry') : t('settings.i18n_new_entry')"
      :width="560"
      @ok="submitModal"
      @cancel="modalVisible = false"
    >
      <a-form layout="vertical">
        <a-form-item :label="t('settings.i18n_lang')" required>
          <a-select
            v-model="editForm.locale"
            :options="localeOpts"
            :disabled="!!editForm.id"
          />
        </a-form-item>
        <a-form-item :label="t('settings.i18n_namespace')" required>
          <a-select
            v-model="editForm.namespace"
            :options="namespaceOpts"
            allow-search
            allow-create
            :disabled="!!editForm.id"
            :placeholder="t('settings.i18n_ns_ph')"
            @change="loadKeyOptions"
          />
        </a-form-item>
        <a-form-item :label="t('settings.i18n_pick_key')" required>
          <a-select
            v-if="!editForm.id"
            v-model="editForm.msg_key"
            :options="keyOpts"
            allow-search
            allow-clear
            :placeholder="t('settings.i18n_key_ph')"
            :loading="keyOptsLoading"
          />
          <a-input
            v-else
            v-model="editForm.msg_key"
            disabled
          />
        </a-form-item>
        <a-form-item :label="t('settings.i18n_col_value')">
          <a-textarea
            v-model="editForm.msg_value"
            :auto-size="{ minRows: 2, maxRows: 6 }"
            :placeholder="t('settings.i18n_value_ph')"
          />
        </a-form-item>
        <a-form-item :label="t('settings.i18n_desc_optional')">
          <a-input v-model="editForm.description" :placeholder="t('settings.i18n_desc_ph')" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-drawer
      v-model:visible="keysDrawerVisible"
      :title="t('settings.i18n_browse_keys')"
      :width="720"
      unmount-on-close
    >
      <a-form layout="inline" class="keys-drawer-filter">
        <a-form-item :label="t('settings.i18n_namespace')">
          <a-select
            v-model="catalogFilter.namespace"
            :options="namespaceOpts"
            allow-clear
            allow-search
            :placeholder="t('settings.i18n_namespace_all')"
            style="width: 160px"
            @change="loadCatalog"
          />
        </a-form-item>
        <a-form-item :label="t('settings.i18n_search')">
          <a-input
            v-model="catalogFilter.q"
            allow-clear
            :placeholder="t('settings.i18n_search_ph')"
            style="width: 200px"
            @press-enter="loadCatalog"
          />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" :loading="catalogLoading" @click="loadCatalog">
            {{ t('settings.i18n_query') }}
          </a-button>
        </a-form-item>
      </a-form>
      <p class="catalog-count">{{ t('settings.i18n_catalog_count', { n: catalogRows.length }) }}</p>
      <a-table
        :data="catalogRows"
        :loading="catalogLoading"
        :pagination="{ pageSize: 30, showTotal: true }"
        :scroll="{ y: 'calc(100vh - 220px)' }"
        size="small"
        row-key="catalogRowKey"
      >
        <template #columns>
          <a-table-column :title="t('settings.i18n_col_namespace')" data-index="namespace" :width="100" />
          <a-table-column :title="t('settings.i18n_col_key')" data-index="msg_key" :width="140" />
          <a-table-column title="zh-CN" :width="180">
            <template #cell="{ record }">
              <span class="seed-text" :title="record.zh_seed">{{ record.zh_seed || '—' }}</span>
            </template>
          </a-table-column>
          <a-table-column title="en-US" :width="180">
            <template #cell="{ record }">
              <span class="seed-text" :title="record.en_seed">{{ record.en_seed || '—' }}</span>
            </template>
          </a-table-column>
          <a-table-column :title="t('settings.col_actions')" :width="100" fixed="right">
            <template #cell="{ record }">
              <a-button size="mini" type="text" @click="pickCatalogKey(record)">
                {{ t('settings.i18n_add_entry') }}
              </a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-drawer>
  </a-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import { loadLocaleMessages } from '@/plugins/i18n'

interface MsgRow {
  id: number | null
  namespace: string
  msg_key: string
  locale: string
  msg_value: string
  description?: string
  zh_seed?: string
  en_seed?: string
  ref_locale?: string
  ref_value?: string
  is_empty?: boolean
  in_db?: boolean
}

interface CatalogRow {
  namespace: string
  msg_key: string
  zh_seed: string
  en_seed: string
  catalogRowKey: string
}

interface ListPayload {
  items: MsgRow[]
  total: number
  page: number
  per_page: number
  coverage?: boolean
}

const DEFAULT_NAMESPACES = [
  'common',
  'menu',
  'auth',
  'login',
  'workflow',
  'monitor',
  'dashboard',
  'apply',
  'validation',
  'admin',
  'settings',
  'studio',
  'org',
  'designer',
  'flowRole',
  'flowDesign',
  'wfSettings',
]

const { t, locale } = useI18n()
const rows = ref<MsgRow[]>([])
const loading = ref(false)
const localeOpts = ref<{ label: string; value: string }[]>([])
const namespaceOpts = ref<{ label: string; value: string }[]>([])
const filter = reactive({
  locale: 'zh-CN',
  namespace: '' as string | undefined,
  q: '',
  emptyOnly: false,
})
const pagination = reactive({
  current: 1,
  pageSize: 50,
  total: 0,
  showTotal: true,
  showPageSize: true,
  pageSizeOptions: [20, 50, 100, 200],
})

const modalVisible = ref(false)
const editForm = reactive({
  id: 0,
  locale: 'zh-CN',
  namespace: 'common',
  msg_key: '',
  msg_value: '',
  description: '',
})

const keyOpts = ref<{ label: string; value: string }[]>([])
const keyOptsLoading = ref(false)

const keysDrawerVisible = ref(false)
const catalogLoading = ref(false)
const catalogRows = ref<CatalogRow[]>([])
const catalogFilter = reactive({
  namespace: '' as string | undefined,
  q: '',
})

function rowKey(record: MsgRow) {
  return `${record.namespace}:${record.msg_key}`
}

function rowClass(record: MsgRow) {
  return record.is_empty ? 'i18n-row-empty' : ''
}

function resetEditForm() {
  editForm.id = 0
  editForm.locale = filter.locale
  editForm.namespace = filter.namespace || 'common'
  editForm.msg_key = ''
  editForm.msg_value = ''
  editForm.description = ''
}

async function loadNamespaces() {
  try {
    const res = await api.get<ApiResponse<string[]>>('/i18n/admin/namespaces')
    const list = res.data.ok ? res.data.data : DEFAULT_NAMESPACES
    namespaceOpts.value = list.map((ns) => ({ label: ns, value: ns }))
  } catch {
    namespaceOpts.value = DEFAULT_NAMESPACES.map((ns) => ({ label: ns, value: ns }))
  }
}

async function loadKeyOptions() {
  const ns = String(editForm.namespace || '').trim()
  if (!ns) {
    keyOpts.value = []
    return
  }
  keyOptsLoading.value = true
  try {
    const res = await api.get<ApiResponse<{ items: CatalogRow[]; total: number }>>('/i18n/admin/catalog', {
      params: { namespace: ns },
    })
    if (res.data.ok) {
      keyOpts.value = res.data.data.items.map((item) => ({
        value: item.msg_key,
        label: t('settings.i18n_key_full', { ns: item.namespace, key: item.msg_key }),
      }))
    }
  } finally {
    keyOptsLoading.value = false
  }
}

async function loadCatalog() {
  catalogLoading.value = true
  try {
    const res = await api.get<ApiResponse<{ items: CatalogRow[]; total: number }>>('/i18n/admin/catalog', {
      params: {
        namespace: catalogFilter.namespace || undefined,
        q: catalogFilter.q || undefined,
      },
    })
    if (res.data.ok) {
      catalogRows.value = res.data.data.items.map((item) => ({
        ...item,
        catalogRowKey: `${item.namespace}:${item.msg_key}`,
      }))
    }
  } finally {
    catalogLoading.value = false
  }
}

async function load() {
  loading.value = true
  try {
    const res = await api.get<ApiResponse<ListPayload>>('/i18n/admin/messages', {
      params: {
        locale: filter.locale,
        namespace: filter.namespace || undefined,
        q: filter.q || undefined,
        empty_only: filter.emptyOnly ? 1 : undefined,
        coverage: 1,
        page: pagination.current,
        per_page: pagination.pageSize,
      },
    })
    if (res.data.ok) {
      rows.value = res.data.data.items
      pagination.total = res.data.data.total
    }
  } finally {
    loading.value = false
  }
}

function onSearch() {
  pagination.current = 1
  load()
}

function onPageChange(page: number) {
  pagination.current = page
  load()
}

function onPageSizeChange(size: number) {
  pagination.pageSize = size
  pagination.current = 1
  load()
}

function onLocaleChange() {
  pagination.current = 1
  load()
}

function onNamespaceChange() {
  pagination.current = 1
  load()
}

function openCreate() {
  resetEditForm()
  loadKeyOptions()
  modalVisible.value = true
}

function openEdit(row: MsgRow) {
  editForm.id = row.id || 0
  editForm.locale = row.locale
  editForm.namespace = row.namespace
  editForm.msg_key = row.msg_key
  editForm.msg_value = row.msg_value
  editForm.description = row.description || ''
  modalVisible.value = true
}

function pickCatalogKey(item: CatalogRow) {
  keysDrawerVisible.value = false
  editForm.id = 0
  editForm.locale = filter.locale
  editForm.namespace = item.namespace
  editForm.msg_key = item.msg_key
  const seed = filter.locale === 'zh-CN' ? item.zh_seed : item.en_seed
  editForm.msg_value = seed || ''
  editForm.description = ''
  loadKeyOptions()
  modalVisible.value = true
}

function applyRef(record: MsgRow) {
  if (!record.ref_value) return
  record.msg_value = record.ref_value
  saveRow(record)
}

async function submitModal() {
  const namespace = String(editForm.namespace || '').trim()
  const msg_key = String(editForm.msg_key || '').trim()
  const localeCode = String(editForm.locale || '').trim()
  if (!namespace || !msg_key || !localeCode) {
    Message.warning(t('settings.i18n_fill_ns_key'))
    return
  }
  if (editForm.id) {
    await api.put(`/i18n/admin/messages/${editForm.id}`, {
      msg_value: editForm.msg_value,
      description: editForm.description,
    })
  } else {
    await api.post('/i18n/admin/messages', {
      namespace,
      msg_key,
      locale: localeCode,
      msg_value: editForm.msg_value || '',
      description: editForm.description,
    })
  }
  Message.success(t('common.success'))
  modalVisible.value = false
  await load()
}

async function saveRow(row: MsgRow) {
  const msg_value = row.msg_value ?? ''
  if (row.id) {
    await api.put(`/i18n/admin/messages/${row.id}`, {
      msg_value,
      description: row.description,
    })
  } else {
    const res = await api.post<ApiResponse<{ id: number }>>('/i18n/admin/messages', {
      namespace: row.namespace,
      msg_key: row.msg_key,
      locale: row.locale,
      msg_value,
      description: row.description,
    })
    if (res.data.ok && res.data.data?.id) {
      row.id = res.data.data.id
      row.in_db = true
      row.is_empty = !String(msg_value).trim()
    }
  }
  Message.success(t('settings.saved'))
}

async function removeRow(row: MsgRow) {
  if (!row.id) return
  await api.delete(`/i18n/admin/messages/${row.id}`)
  Message.success(t('settings.i18n_deleted'))
  if (rows.value.length === 1 && pagination.current > 1) {
    pagination.current -= 1
  }
  await load()
}

async function publish() {
  await api.post('/i18n/admin/publish', { locale: filter.locale })
  await loadLocaleMessages(locale.value, true)
  Message.success(t('settings.i18n_published'))
}

watch(keysDrawerVisible, (open) => {
  if (open) {
    catalogFilter.namespace = filter.namespace
    catalogFilter.q = filter.q
    loadCatalog()
  }
})

onMounted(async () => {
  const res = await api.get<ApiResponse<{ code: string; native_name: string }[]>>('/i18n/locales')
  if (res.data.ok) {
    localeOpts.value = res.data.data.map((x) => ({ label: x.native_name, value: x.code }))
  }
  await loadNamespaces()
  await load()
})
</script>

<style scoped>
.i18n-panel-desc {
  margin: 0 0 0.5rem;
  font-size: 0.9375rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.i18n-coverage-hint {
  margin: 0 0 1rem;
  font-size: 0.8125rem;
  color: var(--text-tertiary);
  line-height: 1.5;
}

.i18n-filter-form {
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.i18n-table :deep(.arco-table-th) {
  background: var(--surface-muted) !important;
  font-weight: 600;
}

.i18n-table :deep(.i18n-row-empty) .arco-table-td {
  background: rgba(var(--warning-6), 0.06);
}

.i18n-desc {
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}

.ref-cell {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.8125rem;
}

.ref-locale {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

.ref-text {
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.keys-drawer-filter {
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.catalog-count {
  margin: 0 0 0.5rem;
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}

.seed-text {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  max-width: 160px;
}
</style>
