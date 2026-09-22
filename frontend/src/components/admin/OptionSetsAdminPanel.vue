<template>
  <a-card class="settings-card" :bordered="false">
    <div class="flex flex-wrap justify-between gap-2 mb-3">
      <p class="text-sm text-gray-500 m-0">{{ t('settings.opt_panel_desc_option') }}</p>
      <a-button type="primary" @click="openEdit()">{{ t('settings.opt_add') }}</a-button>
    </div>

    <a-table :data="sets" :loading="loading" row-key="id" :pagination="false">
      <template #columns>
        <a-table-column :title="t('settings.opt_col_code')" data-index="code" :width="140" />
        <a-table-column :title="t('settings.opt_col_name')" data-index="name" />
        <a-table-column :title="t('settings.opt_col_count')" :width="88">
          <template #cell="{ record }">{{ record.items?.length || 0 }}</template>
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
              <a-popconfirm :content="t('settings.opt_delete_confirm')" @ok="removeSet(record.id)">
                <a-button size="mini" status="danger">{{ t('settings.action_delete') }}</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>

    <a-modal
      v-model:visible="modalVisible"
      :title="edit.id ? t('settings.opt_edit_title') : t('settings.opt_new_title')"
      :width="640"
      @ok="save"
      @cancel="modalVisible = false"
    >
      <a-form layout="vertical">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item :label="t('settings.opt_code')" required>
              <a-input v-model="edit.code" :placeholder="t('settings.opt_code_ph')" :disabled="!!edit.id" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item :label="t('settings.opt_name')" required>
              <a-input v-model="edit.name" :placeholder="t('settings.opt_name_ph')" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item :label="t('settings.opt_description')">
          <a-input v-model="edit.description" />
        </a-form-item>
        <a-form-item :label="t('settings.opt_enabled')">
          <a-switch v-model="edit.is_active" />
        </a-form-item>
        <a-divider>{{ t('settings.opt_list_divider') }}</a-divider>
        <p class="hint-text">{{ t('settings.opt_list_hint') }}</p>
        <div v-for="(item, idx) in edit.items" :key="idx" class="item-row">
          <a-input v-model="item.name" :placeholder="t('settings.opt_item_name')" />
          <a-input v-model="item.code" :placeholder="t('settings.opt_item_code')" />
          <a-button size="mini" status="danger" @click="edit.items.splice(idx, 1)">−</a-button>
        </div>
        <a-space>
          <a-button size="small" @click="edit.items.push({ name: '', code: '', sort_order: edit.items.length })">
            {{ t('settings.opt_add_item') }}
          </a-button>
          <a-button size="small" @click="batchOpen = true">{{ t('settings.opt_batch_import') }}</a-button>
        </a-space>
      </a-form>
    </a-modal>

    <a-modal v-model:visible="batchOpen" :title="t('settings.opt_batch_title')" @ok="applyBatch">
      <a-textarea v-model="batchText" :auto-size="{ minRows: 6 }" :placeholder="t('settings.opt_batch_ph')" />
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import { clearOptionSetCache } from '@/composables/useFieldOptions'

interface OptionItem {
  id?: number
  name: string
  code: string
  sort_order?: number
  is_active?: boolean
}

interface OptionSetRow {
  id: number
  code: string
  name: string
  description?: string
  sort_order?: number
  is_active: boolean
  items: OptionItem[]
}

const { t } = useI18n()
const sets = ref<OptionSetRow[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const batchOpen = ref(false)
const batchText = ref('')

const edit = reactive({
  id: 0,
  code: '',
  name: '',
  description: '',
  sort_order: 0,
  is_active: true,
  items: [] as OptionItem[],
})

async function load() {
  loading.value = true
  try {
    const res = await api.get<ApiResponse<OptionSetRow[]>>('/admin/option-sets', {
      params: { set_type: 'option' },
    })
    if (res.data.ok) sets.value = res.data.data
  } finally {
    loading.value = false
  }
}

function openEdit(row?: OptionSetRow) {
  if (row) {
    edit.id = row.id
    edit.code = row.code
    edit.name = row.name
    edit.description = row.description || ''
    edit.sort_order = row.sort_order || 0
    edit.is_active = row.is_active
    edit.items = (row.items || []).map((i) => ({ ...i }))
  } else {
    edit.id = 0
    edit.code = ''
    edit.name = ''
    edit.description = ''
    edit.sort_order = 0
    edit.is_active = true
    edit.items = [{ name: '', code: '', sort_order: 0 }]
  }
  modalVisible.value = true
}

async function save() {
  if (!edit.code.trim() || !edit.name.trim()) {
    Message.warning(t('settings.opt_fill_code_name'))
    return
  }
  const payload = {
    set_type: 'option',
    code: edit.code.trim(),
    name: edit.name.trim(),
    description: edit.description,
    sort_order: edit.sort_order,
    is_active: edit.is_active,
    items: edit.items
      .filter((i) => i.name.trim() && i.code.trim())
      .map((i, idx) => ({
        name: i.name.trim(),
        code: i.code.trim(),
        sort_order: idx,
        is_active: true,
      })),
  }
  if (edit.id) {
    await api.put(`/admin/option-sets/${edit.id}`, payload)
  } else {
    await api.post('/admin/option-sets', payload)
  }
  clearOptionSetCache()
  modalVisible.value = false
  Message.success(t('settings.saved'))
  await load()
}

async function removeSet(id: number) {
  await api.delete(`/admin/option-sets/${id}`)
  clearOptionSetCache()
  Message.success(t('settings.deleted'))
  await load()
}

function applyBatch() {
  const lines = batchText.value.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  for (const line of lines) {
    const parts = line.split(/[,，\t]/).map((p) => p.trim())
    const name = parts[0] || ''
    const code = parts[1] || name
    if (name) edit.items.push({ name, code, sort_order: edit.items.length })
  }
  batchOpen.value = false
  batchText.value = ''
}

onMounted(load)
</script>

<style scoped>
.item-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.hint-text {
  font-size: 12px;
  color: #86909c;
  margin: 0 0 8px;
}
</style>
