<template>
  <a-card class="settings-card" :bordered="false">
    <div class="llm-toolbar">
      <p class="llm-hint">{{ t('settings.llm_panel_desc') }}</p>
      <a-button type="primary" @click="openEdit()">{{ t('settings.llm_add') }}</a-button>
    </div>

    <a-table :data="rows" :loading="loading" row-key="id" :pagination="false">
      <template #columns>
        <a-table-column :title="t('settings.llm_col_priority')" :width="120">
          <template #cell="{ record, rowIndex }">
            <a-space>
              <a-button size="mini" :disabled="rowIndex === 0" @click="moveUp(rowIndex)">↑</a-button>
              <a-button size="mini" :disabled="rowIndex === rows.length - 1" @click="moveDown(rowIndex)">↓</a-button>
            </a-space>
          </template>
        </a-table-column>
        <a-table-column :title="t('settings.llm_col_name')" :width="140">
          <template #cell="{ record }">
            <span>{{ record.name || '—' }}</span>
            <a-tag v-if="record.is_default" color="arcoblue" size="small" class="ml-1">
              {{ t('settings.llm_default_badge') }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column :title="t('settings.llm_col_type')" :width="150">
          <template #cell="{ record }">{{ providerLabel(record.provider_type) }}</template>
        </a-table-column>
        <a-table-column :title="t('settings.llm_col_base_url')" data-index="base_url" />
        <a-table-column :title="t('settings.llm_col_model')" :width="140">
          <template #cell="{ record }">{{ record.model_name || '—' }}</template>
        </a-table-column>
        <a-table-column :title="t('settings.llm_col_status')" :width="100">
          <template #cell="{ record }">
            <a-tag :color="record.is_active ? 'green' : 'gray'">
              {{ record.is_active ? t('settings.status_enabled') : t('settings.status_disabled') }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column :title="t('settings.llm_col_test')" :width="160">
          <template #cell="{ record }">
            <template v-if="record.last_tested_at">
              <a-tag :color="record.last_test_ok ? 'green' : 'red'" size="small">
                {{ record.last_test_ok ? t('settings.llm_test_ok') : t('settings.llm_test_fail') }}
              </a-tag>
              <div class="llm-test-time">{{ record.last_tested_at }}</div>
            </template>
            <span v-else class="text-gray-400">—</span>
          </template>
        </a-table-column>
        <a-table-column :title="t('settings.col_actions')" :width="200" fixed="right">
          <template #cell="{ record }">
            <a-space>
              <a-button size="mini" :loading="testingId === record.id" @click="testSaved(record)">
                {{ t('settings.llm_test_btn') }}
              </a-button>
              <a-button size="mini" @click="openEdit(record)">{{ t('settings.action_edit') }}</a-button>
              <a-popconfirm :content="t('settings.llm_delete_confirm')" @ok="removeRow(record.id)">
                <a-button size="mini" status="danger">{{ t('settings.action_delete') }}</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>

    <a-alert type="info" class="mt-3">{{ t('settings.llm_alert') }}</a-alert>

    <a-modal
      v-model:visible="modalVisible"
      :title="edit.id ? t('settings.llm_edit_title') : t('settings.llm_new_title')"
      :width="560"
      :ok-loading="saving"
      @ok="save"
      @cancel="modalVisible = false"
    >
      <a-form layout="vertical">
        <a-form-item :label="t('settings.llm_name')">
          <a-input v-model="edit.name" :placeholder="t('settings.llm_name_ph')" allow-clear />
        </a-form-item>
        <a-form-item :label="t('settings.llm_type')" required>
          <a-select v-model="edit.provider_type" :options="providerOpts" />
        </a-form-item>
        <a-form-item :label="t('settings.llm_base_url')" required>
          <a-input v-model="edit.base_url" :placeholder="baseUrlPlaceholder" allow-clear />
          <template #extra>
            <span class="text-xs text-gray-500">{{ baseUrlHint }}</span>
          </template>
        </a-form-item>
        <a-form-item :label="t('settings.llm_api_key')">
          <a-input-password
            v-model="edit.api_key"
            :placeholder="edit.has_api_key ? t('settings.llm_api_key_keep') : t('settings.llm_api_key_ph')"
            allow-clear
          />
        </a-form-item>
        <a-form-item :label="t('settings.llm_model')">
          <a-input v-model="edit.model_name" :placeholder="modelPlaceholder" allow-clear />
        </a-form-item>
        <a-form-item :label="t('settings.llm_enabled')">
          <a-switch v-model="edit.is_active" />
        </a-form-item>
        <a-space wrap>
          <a-button :loading="testingModal" @click="testInModal">{{ t('settings.llm_test_btn') }}</a-button>
          <span v-if="modalTestMessage" :class="modalTestOk ? 'text-green-600' : 'text-red-600'" class="text-sm">
            {{ modalTestMessage }}
          </span>
        </a-space>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'

type ProviderType = 'openai_compatible' | 'anthropic_compatible' | 'ollama'

interface LlmRow {
  id: number
  name: string
  provider_type: ProviderType
  base_url: string
  has_api_key: boolean
  model_name: string
  sort_order: number
  is_active: boolean
  is_default: boolean
  last_test_ok?: boolean | null
  last_test_message?: string
  last_tested_at?: string
}

const { t } = useI18n()
const rows = ref<LlmRow[]>([])
const loading = ref(false)
const saving = ref(false)
const testingId = ref(0)
const testingModal = ref(false)
const modalVisible = ref(false)
const modalTestMessage = ref('')
const modalTestOk = ref(false)

const edit = reactive({
  id: 0,
  name: '',
  provider_type: 'openai_compatible' as ProviderType,
  base_url: '',
  api_key: '',
  has_api_key: false,
  model_name: '',
  is_active: true,
})

const providerOpts = computed(() => [
  { label: t('settings.llm_type_openai'), value: 'openai_compatible' },
  { label: t('settings.llm_type_anthropic'), value: 'anthropic_compatible' },
  { label: t('settings.llm_type_ollama'), value: 'ollama' },
])

function providerLabel(type: string) {
  const hit = providerOpts.value.find((o) => o.value === type)
  return hit?.label || type
}

const baseUrlPlaceholder = computed(() => {
  if (edit.provider_type === 'ollama') return 'http://127.0.0.1:11434'
  if (edit.provider_type === 'anthropic_compatible') return 'https://api.anthropic.com'
  return 'http://127.0.0.1:8080/v1'
})

const baseUrlHint = computed(() => {
  const internal = t('settings.llm_base_url_hint_internal')
  if (edit.provider_type === 'ollama') return `${t('settings.llm_base_url_hint_ollama')} ${internal}`
  if (edit.provider_type === 'anthropic_compatible') return t('settings.llm_base_url_hint_anthropic')
  return `${t('settings.llm_base_url_hint_openai')} ${internal}`
})

function normalizeBaseUrlInput(raw: string): string {
  const trimmed = raw.trim()
  if (!trimmed) return ''
  if (trimmed.startsWith('@internal')) return trimmed
  if (!/^https?:\/\//i.test(trimmed)) return `http://${trimmed}`
  return trimmed
}

const modelPlaceholder = computed(() => {
  if (edit.provider_type === 'anthropic_compatible') return t('settings.llm_model_ph_required')
  return t('settings.llm_model_ph')
})

async function load() {
  loading.value = true
  try {
    const res = await api.get<ApiResponse<LlmRow[]>>('/admin/llm-providers')
    if (res.data.ok) rows.value = res.data.data
  } finally {
    loading.value = false
  }
}

function openEdit(row?: LlmRow) {
  modalTestMessage.value = ''
  modalTestOk.value = false
  if (row) {
    edit.id = row.id
    edit.name = row.name
    edit.provider_type = row.provider_type
    edit.base_url = row.base_url
    edit.api_key = ''
    edit.has_api_key = row.has_api_key
    edit.model_name = row.model_name
    edit.is_active = row.is_active
  } else {
    edit.id = 0
    edit.name = ''
    edit.provider_type = 'openai_compatible'
    edit.base_url = ''
    edit.api_key = ''
    edit.has_api_key = false
    edit.model_name = ''
    edit.is_active = true
  }
  modalVisible.value = true
}

function buildPayload() {
  const payload: Record<string, unknown> = {
    name: edit.name.trim(),
    provider_type: edit.provider_type,
    base_url: normalizeBaseUrlInput(edit.base_url),
    model_name: edit.model_name.trim(),
    is_active: edit.is_active,
  }
  if (edit.api_key.trim()) payload.api_key = edit.api_key.trim()
  if (edit.id) payload.id = edit.id
  return payload
}

async function testInModal() {
  if (!edit.base_url.trim()) {
    Message.warning(t('settings.llm_fill_base_url'))
    return
  }
  testingModal.value = true
  modalTestMessage.value = ''
  try {
    const res = await api.post<ApiResponse<{ message?: string }>>('/admin/llm-providers/test', buildPayload())
    if (res.data.ok) {
      modalTestOk.value = true
      modalTestMessage.value = res.data.message || t('settings.llm_test_ok')
      Message.success(modalTestMessage.value)
    }
  } catch (e: unknown) {
    modalTestOk.value = false
    modalTestMessage.value = e instanceof Error ? e.message : t('settings.llm_test_fail')
  } finally {
    testingModal.value = false
  }
}

async function testSaved(row: LlmRow) {
  testingId.value = row.id
  try {
    const res = await api.post<ApiResponse<{ message?: string }>>(`/admin/llm-providers/${row.id}/test`, {})
    if (res.data.ok) {
      Message.success(res.data.message || t('settings.llm_test_ok'))
      await load()
    }
  } catch (e: unknown) {
    Message.error(e instanceof Error ? e.message : t('settings.llm_test_fail'))
    await load()
  } finally {
    testingId.value = 0
  }
}

async function save() {
  if (!edit.base_url.trim()) {
    Message.warning(t('settings.llm_fill_base_url'))
    return
  }
  saving.value = true
  try {
    const payload = buildPayload()
    if (edit.id) {
      await api.put(`/admin/llm-providers/${edit.id}`, payload)
    } else {
      await api.post('/admin/llm-providers', payload)
    }
    modalVisible.value = false
    Message.success(t('settings.saved'))
    await load()
  } catch (e: unknown) {
    Message.error(e instanceof Error ? e.message : t('settings.save_failed'))
  } finally {
    saving.value = false
  }
}

async function removeRow(id: number) {
  await api.delete(`/admin/llm-providers/${id}`)
  Message.success(t('settings.deleted'))
  await load()
}

async function persistOrder() {
  const ids = rows.value.map((r) => r.id)
  const res = await api.post<ApiResponse<LlmRow[]>>('/admin/llm-providers/reorder', { ids })
  if (res.data.ok) rows.value = res.data.data
}

async function moveUp(index: number) {
  if (index <= 0) return
  const list = [...rows.value]
  ;[list[index - 1], list[index]] = [list[index], list[index - 1]]
  rows.value = list
  await persistOrder()
}

async function moveDown(index: number) {
  if (index >= rows.value.length - 1) return
  const list = [...rows.value]
  ;[list[index], list[index + 1]] = [list[index + 1], list[index]]
  rows.value = list
  await persistOrder()
}

onMounted(load)
</script>

<style scoped>
.llm-toolbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  align-items: flex-start;
}

.llm-hint {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
  flex: 1;
  min-width: 200px;
}

.llm-test-time {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.ml-1 {
  margin-left: 4px;
}

.mt-3 {
  margin-top: 12px;
}

.text-gray-400 {
  color: var(--text-tertiary);
}

.text-green-600 {
  color: #00b42a;
}

.text-red-600 {
  color: #f53f3f;
}

.text-xs {
  font-size: 12px;
}

.text-gray-500 {
  color: var(--text-tertiary);
}

.text-sm {
  font-size: 0.875rem;
}
</style>
