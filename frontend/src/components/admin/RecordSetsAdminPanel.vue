<template>
  <a-card class="settings-card" :bordered="false">
    <div class="flex flex-wrap justify-between gap-2 mb-3">
      <p class="text-sm text-gray-500 m-0">{{ t('settings.rec_panel_desc') }}</p>
      <a-button type="primary" @click="openEdit()">{{ t('settings.rec_add') }}</a-button>
    </div>

    <a-table :data="sets" :loading="loading" row-key="id" :pagination="false">
      <template #columns>
        <a-table-column :title="t('settings.opt_col_code')" data-index="code" :width="140" />
        <a-table-column :title="t('settings.opt_col_name')" data-index="name" />
        <a-table-column :title="t('settings.rec_col_fields')" :width="88">
          <template #cell="{ record }">{{ record.columns?.length || 0 }}</template>
        </a-table-column>
        <a-table-column :title="t('settings.rec_col_rows')" :width="88">
          <template #cell="{ record }">{{ record.records?.length || 0 }}</template>
        </a-table-column>
        <a-table-column :title="t('settings.rec_col_scope')" :width="120">
          <template #cell="{ record }">{{ scopeLabel(record.data_scope) }}</template>
        </a-table-column>
        <a-table-column :title="t('settings.rate_col_status')" :width="80">
          <template #cell="{ record }">
            <a-tag :color="record.is_active ? 'green' : 'gray'">
              {{ record.is_active ? t('settings.status_enabled') : t('settings.status_disabled') }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column :title="t('settings.col_actions')" :width="160">
          <template #cell="{ record }">
            <a-space>
              <a-button size="mini" @click="openEdit(record)">{{ t('settings.action_edit') }}</a-button>
              <a-popconfirm :content="t('settings.rec_delete_confirm')" @ok="removeSet(record.id)">
                <a-button size="mini" status="danger">{{ t('settings.action_delete') }}</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>

    <a-modal
      v-model:visible="modalVisible"
      :title="edit.id ? t('settings.rec_edit_title') : t('settings.rec_new_title')"
      :width="920"
      :ok-text="t('common.save')"
      @ok="save"
      @cancel="modalVisible = false"
    >
      <a-form layout="vertical">
        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item :label="t('settings.opt_code')" required>
              <a-input v-model="edit.code" :placeholder="t('settings.rec_code_ph')" :disabled="!!edit.id" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item :label="t('settings.opt_name')" required>
              <a-input v-model="edit.name" :placeholder="t('settings.rec_name_ph')" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item :label="t('settings.opt_enabled')">
              <a-switch v-model="edit.is_active" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item :label="t('settings.opt_description')">
          <a-input v-model="edit.description" />
        </a-form-item>
        <a-form-item :label="t('settings.rec_col_scope')" required>
          <a-radio-group v-model="edit.data_scope" type="button">
            <a-radio value="company">{{ t('settings.rec_scope_company') }}</a-radio>
            <a-radio value="personal">{{ t('settings.rec_scope_personal') }}</a-radio>
            <a-radio value="mixed">{{ t('settings.rec_scope_mixed') }}</a-radio>
          </a-radio-group>
          <p class="hint-text mt-1">{{ t('settings.rec_scope_hint') }}</p>
        </a-form-item>

        <a-divider>{{ t('settings.rec_columns_title') }}</a-divider>
        <p class="hint-text">{{ t('settings.rec_columns_hint') }}</p>
        <div class="col-row col-row-head">
          <span class="col-head-label">{{ t('settings.rec_col_label_ph') }}</span>
          <span class="col-head-key">{{ t('settings.rec_col_key_ph') }}</span>
          <span class="col-head-span">{{ t('settings.rec_col_span') }}</span>
          <span class="col-head-action" />
        </div>
        <div v-for="(col, ci) in edit.columns" :key="ci" class="col-row">
          <a-input v-model="col.label" :placeholder="t('settings.rec_col_label_ph')" class="flex-1" />
          <a-input v-model="col.field_key" :placeholder="t('settings.rec_col_key_ph')" class="w-40" />
          <a-input-number
            v-model="col.span"
            :min="6"
            :max="24"
            :step="2"
            class="col-span-input"
          />
          <a-button size="mini" status="danger" @click="edit.columns.splice(ci, 1)">−</a-button>
        </div>
        <a-button size="small" class="mb-4" @click="addColumn">{{ t('settings.rec_add_column') }}</a-button>

        <a-divider v-if="edit.data_scope !== 'personal'">{{ t('settings.rec_data_title') }}</a-divider>
        <p v-if="edit.data_scope === 'personal'" class="hint-text">{{ t('settings.rec_personal_scope_hint') }}</p>
        <template v-if="edit.data_scope !== 'personal'">
        <div class="rec-table-wrap">
          <table v-if="edit.columns.length" class="rec-table">
            <thead>
              <tr>
                <th v-for="c in edit.columns" :key="c.field_key">{{ c.label || c.field_key }}</th>
                <th class="w-16">{{ t('settings.rec_row_actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in edit.records" :key="ri">
                <td v-for="c in edit.columns" :key="c.field_key">
                  <a-input v-model="row.data[c.field_key]" size="small" />
                </td>
                <td>
                  <a-button size="mini" status="danger" @click="edit.records.splice(ri, 1)">−</a-button>
                </td>
              </tr>
            </tbody>
          </table>
          <a-empty v-else :description="t('settings.rec_need_columns')" />
        </div>
        <a-button size="small" :disabled="!edit.columns.length" @click="addRecord">
          {{ t('settings.rec_add_row') }}
        </a-button>
        </template>

        <template v-if="edit.id && edit.data_scope === 'mixed'">
          <a-divider>{{ t('settings.rec_personal_all_title') }}</a-divider>
          <p class="hint-text">{{ t('settings.rec_personal_all_hint') }}</p>
          <a-spin :loading="personalLoading">
            <a-table
              v-if="personalRows.length"
              :data="personalRows"
              row-key="row_code"
              :pagination="{ pageSize: 6 }"
              size="small"
            >
              <template #columns>
                <a-table-column :title="t('settings.rec_personal_owner')" data-index="owner_display_name" :width="100" />
                <a-table-column
                  v-for="c in edit.columns"
                  :key="c.field_key"
                  :title="c.label"
                >
                  <template #cell="{ record }">{{ record.data[c.field_key] || '—' }}</template>
                </a-table-column>
              </template>
            </a-table>
            <a-empty v-else :description="t('settings.rec_personal_empty')" />
          </a-spin>
        </template>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import { clearRecordSetCache, type RecordSetDataScope } from '@/composables/useRecordSets'
import { normalizeRecordSetColumnSpan } from '@/utils/recordSetLayout'

interface ColumnEdit {
  field_key: string
  label: string
  sort_order?: number
  span?: number
}

interface RecordEdit {
  row_code?: string
  data: Record<string, string>
}

interface RecordSetRow {
  id: number
  code: string
  name: string
  description?: string
  is_active: boolean
  data_scope?: RecordSetDataScope
  columns: ColumnEdit[]
  records: { row_code: string; data: Record<string, string> }[]
}

const { t } = useI18n()
const sets = ref<RecordSetRow[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const personalLoading = ref(false)
const personalRows = ref<
  { row_code: string; data: Record<string, string>; owner_display_name?: string }[]
>([])

const edit = reactive({
  id: 0,
  code: '',
  name: '',
  description: '',
  is_active: true,
  data_scope: 'mixed' as RecordSetDataScope,
  columns: [] as ColumnEdit[],
  records: [] as RecordEdit[],
})

function scopeLabel(scope?: RecordSetDataScope) {
  if (scope === 'company') return t('settings.rec_scope_company')
  if (scope === 'personal') return t('settings.rec_scope_personal')
  return t('settings.rec_scope_mixed')
}

function slugKey(label: string) {
  const s = label.trim().replace(/\s+/g, '_')
  if (/^[a-zA-Z][\w]*$/.test(s)) return s.slice(0, 64)
  return `f_${Date.now().toString(36).slice(-6)}`
}

function addColumn() {
  edit.columns.push({ label: '', field_key: '', sort_order: edit.columns.length, span: 12 })
}

function addRecord() {
  const data: Record<string, string> = {}
  for (const c of edit.columns) {
    data[c.field_key || slugKey(c.label)] = ''
  }
  edit.records.push({ data })
}

async function load() {
  loading.value = true
  try {
    const res = await api.get<ApiResponse<RecordSetRow[]>>('/admin/option-sets', {
      params: { set_type: 'record' },
    })
    if (res.data.ok) sets.value = res.data.data
  } finally {
    loading.value = false
  }
}

function openEdit(row?: RecordSetRow) {
  if (row) {
    edit.id = row.id
    edit.code = row.code
    edit.name = row.name
    edit.description = row.description || ''
    edit.is_active = row.is_active
    edit.data_scope = row.data_scope || 'mixed'
    edit.columns = (row.columns || []).map((c, i) => ({
      ...c,
      sort_order: i,
      span: normalizeRecordSetColumnSpan(c.span),
    }))
    edit.records = (row.records || []).map((r) => ({
      row_code: r.row_code,
      data: { ...r.data },
    }))
  } else {
    edit.id = 0
    edit.code = ''
    edit.name = ''
    edit.description = ''
    edit.is_active = true
    edit.data_scope = 'mixed'
    edit.columns = [
      { label: '收款人', field_key: 'payee', sort_order: 0, span: 12 },
      { label: '开户行', field_key: 'bank', sort_order: 1, span: 12 },
      { label: '账户', field_key: 'account', sort_order: 2, span: 12 },
      { label: '联系人', field_key: 'contact', sort_order: 3, span: 12 },
      { label: '联系方式', field_key: 'phone', sort_order: 4, span: 12 },
    ]
    edit.records = []
  }
  modalVisible.value = true
  personalRows.value = []
  if (row?.id && row.data_scope === 'mixed') void loadPersonalRows(row.id)
}

async function loadPersonalRows(setId: number) {
  personalLoading.value = true
  try {
    const res = await api.get<
      ApiResponse<{
        records: { row_code: string; data: Record<string, string>; owner_display_name?: string }[]
      }>
    >(`/admin/option-sets/${setId}/personal-records`)
    if (res.data.ok) personalRows.value = res.data.data.records || []
  } finally {
    personalLoading.value = false
  }
}

async function save() {
  if (!edit.code.trim() || !edit.name.trim()) {
    Message.warning(t('settings.opt_fill_code_name'))
    return
  }
  const columns = edit.columns
    .filter((c) => c.label.trim())
    .map((c, i) => ({
      label: c.label.trim(),
      field_key: (c.field_key || slugKey(c.label)).trim(),
      sort_order: i,
      span: normalizeRecordSetColumnSpan(c.span),
    }))
  if (!columns.length) {
    Message.warning(t('settings.rec_need_columns'))
    return
  }
  const records = edit.data_scope === 'personal'
    ? []
    : edit.records
        .map((r, i) => {
          const data: Record<string, string> = {}
          for (const c of columns) {
            data[c.field_key] = String(r.data[c.field_key] || '').trim()
          }
          return {
            row_code: r.row_code || `row_${i + 1}`,
            data,
            sort_order: i,
            is_active: true,
          }
        })
        .filter((r) => Object.values(r.data).some((v) => v))

  const payload = {
    set_type: 'record',
    code: edit.code.trim(),
    name: edit.name.trim(),
    description: edit.description,
    is_active: edit.is_active,
    data_scope: edit.data_scope,
    columns,
    records,
  }
  if (edit.id) {
    await api.put(`/admin/option-sets/${edit.id}`, payload)
  } else {
    await api.post('/admin/option-sets', payload)
  }
  clearRecordSetCache()
  modalVisible.value = false
  Message.success(t('settings.saved'))
  await load()
}

async function removeSet(id: number) {
  await api.delete(`/admin/option-sets/${id}`)
  clearRecordSetCache()
  Message.success(t('settings.deleted'))
  await load()
}

onMounted(load)
</script>

<style scoped>
.col-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}

.col-row-head {
  font-size: 12px;
  color: #86909c;
  margin-bottom: 4px;
}

.col-head-label {
  flex: 1;
}

.col-head-key {
  width: 160px;
}

.col-head-span {
  width: 88px;
  text-align: center;
}

.col-head-action {
  width: 32px;
}

.col-span-input {
  width: 88px;
}

.hint-text {
  font-size: 12px;
  color: #86909c;
  margin: 0 0 8px;
}

.mt-1 {
  margin-top: 4px;
}

.rec-table-wrap {
  overflow-x: auto;
  margin-bottom: 12px;
  max-height: 360px;
}

.rec-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.rec-table th,
.rec-table td {
  border: 1px solid var(--border, #e5e6eb);
  padding: 6px 8px;
  white-space: nowrap;
}

.rec-table th {
  background: var(--surface-muted, #f7f8fa);
  font-weight: 600;
}
</style>
