<template>
  <a-card class="settings-card" :bordered="false">
    <div class="flex flex-wrap justify-between gap-2 mb-3">
      <p class="text-sm text-gray-500 m-0">{{ t('settings.rate_panel_desc') }}</p>
      <a-button type="primary" @click="openEdit()">{{ t('settings.rate_add') }}</a-button>
    </div>

    <a-table :data="rows" :loading="loading" row-key="id" :pagination="false">
      <template #columns>
        <a-table-column :title="t('settings.rate_col_code')" data-index="currency_code" :width="100" />
        <a-table-column :title="t('settings.rate_col_name')" data-index="currency_name" />
        <a-table-column :title="t('settings.rate_col_value')" :width="140">
          <template #cell="{ record }">{{ formatRate(record.rate_to_cny) }}</template>
        </a-table-column>
        <a-table-column :title="t('settings.rate_col_status')" :width="80">
          <template #cell="{ record }">
            <a-tag :color="record.is_active ? 'green' : 'gray'">
              {{ record.is_active ? t('settings.status_enabled') : t('settings.status_disabled') }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column :title="t('settings.rate_col_updated')" :width="160">
          <template #cell="{ record }">{{ formatDateTime(record.updated_at) }}</template>
        </a-table-column>
        <a-table-column :title="t('settings.col_actions')" :width="140">
          <template #cell="{ record }">
            <a-space>
              <a-button size="mini" @click="openEdit(record)">{{ t('settings.action_edit') }}</a-button>
              <a-popconfirm
                v-if="record.currency_code !== 'CNY'"
                :content="t('settings.rate_delete_confirm')"
                @ok="removeRow(record.id)"
              >
                <a-button size="mini" status="danger">{{ t('settings.action_delete') }}</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>

    <a-alert type="info" class="mt-3">{{ t('settings.rate_alert') }}</a-alert>

    <a-modal
      v-model:visible="modalVisible"
      :title="edit.id ? t('settings.rate_edit_title') : t('settings.rate_new_title')"
      :width="480"
      @ok="save"
    >
      <a-form layout="vertical">
        <a-form-item :label="t('settings.rate_code')" required>
          <a-input
            v-model="edit.currency_code"
            :placeholder="t('settings.rate_code_ph')"
            :disabled="!!edit.id"
          />
        </a-form-item>
        <a-form-item :label="t('settings.rate_name')" required>
          <a-input v-model="edit.currency_name" :placeholder="t('settings.rate_name_ph')" />
        </a-form-item>
        <a-form-item :label="t('settings.rate_value')" required>
          <a-input-number v-model="edit.rate_to_cny" :min="0.000001" :precision="6" class="w-full" />
          <template #extra>{{ t('settings.rate_value_extra') }}</template>
        </a-form-item>
        <a-form-item :label="t('settings.rate_remark')">
          <a-input v-model="edit.remark" />
        </a-form-item>
        <a-form-item :label="t('settings.rate_enabled')">
          <a-switch v-model="edit.is_active" />
        </a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import { clearExchangeRateCache } from '@/composables/useMoneyField'
import { formatDateTime } from '@/utils/dateTime'

interface RateRow {
  id: number
  currency_code: string
  currency_name: string
  rate_to_cny: number
  sort_order?: number
  is_active: boolean
  remark?: string
  updated_at?: string
}

const { t, locale } = useI18n()
const rows = ref<RateRow[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const edit = reactive({
  id: 0,
  currency_code: '',
  currency_name: '',
  rate_to_cny: 1,
  is_active: true,
  remark: '',
})

function formatRate(n: number) {
  const loc = locale.value.startsWith('en') ? 'en-US' : 'zh-CN'
  return Number(n).toLocaleString(loc, { minimumFractionDigits: 2, maximumFractionDigits: 6 })
}

async function load() {
  loading.value = true
  try {
    const res = await api.get<ApiResponse<RateRow[]>>('/admin/exchange-rates')
    if (res.data.ok) rows.value = res.data.data
  } finally {
    loading.value = false
  }
}

function openEdit(row?: RateRow) {
  if (row) {
    edit.id = row.id
    edit.currency_code = row.currency_code
    edit.currency_name = row.currency_name
    edit.rate_to_cny = row.rate_to_cny
    edit.is_active = row.is_active
    edit.remark = row.remark || ''
  } else {
    edit.id = 0
    edit.currency_code = ''
    edit.currency_name = ''
    edit.rate_to_cny = 1
    edit.is_active = true
    edit.remark = ''
  }
  modalVisible.value = true
}

async function save() {
  const code = edit.currency_code.trim().toUpperCase()
  if (!code || !edit.currency_name.trim()) {
    Message.warning(t('settings.rate_fill_required'))
    return
  }
  if (!edit.rate_to_cny || edit.rate_to_cny <= 0) {
    Message.warning(t('settings.rate_invalid'))
    return
  }
  const payload = {
    currency_code: code,
    currency_name: edit.currency_name.trim(),
    rate_to_cny: edit.rate_to_cny,
    is_active: edit.is_active,
    remark: edit.remark,
  }
  if (edit.id) {
    await api.put(`/admin/exchange-rates/${edit.id}`, payload)
  } else {
    await api.post('/admin/exchange-rates', payload)
  }
  clearExchangeRateCache()
  modalVisible.value = false
  Message.success(t('settings.saved'))
  await load()
}

async function removeRow(id: number) {
  await api.delete(`/admin/exchange-rates/${id}`)
  clearExchangeRateCache()
  Message.success(t('settings.deleted'))
  await load()
}

onMounted(load)
</script>
