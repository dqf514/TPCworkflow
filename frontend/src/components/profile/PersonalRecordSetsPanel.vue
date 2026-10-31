<template>
  <div class="personal-record-sets">
    <p class="hint-text">
      此处维护您在填表时保存的个人常用数据（如个人收款账号）。公司级配置由管理员在系统设置中维护；个人级配置表仅显示本人数据。
    </p>
    <a-form layout="vertical" class="mb-3" :model="filterForm">
      <a-form-item label="控件配置表">
        <a-select
          v-model="selectedCode"
          :options="setOpts"
          placeholder="请选择要管理的配置表"
          allow-search
          @change="onSetChange"
        />
      </a-form-item>
    </a-form>

    <template v-if="selectedCode">
      <div class="flex justify-between items-center mb-2">
        <span class="text-sm text-gray-600">共 {{ rows.length }} 条个人数据</span>
        <a-button type="primary" size="small" :disabled="!columns.length" @click="openRow()">
          新增
        </a-button>
      </div>
      <a-table :data="rows" :loading="loading" row-key="row_code" :pagination="{ pageSize: 8 }">
        <template #columns>
          <a-table-column
            v-for="c in columns"
            :key="c.field_key"
            :title="c.label"
            :data-index="`data.${c.field_key}`"
          >
            <template #cell="{ record }">{{ record.data[c.field_key] || '—' }}</template>
          </a-table-column>
          <a-table-column title="操作" :width="120">
            <template #cell="{ record }">
              <a-space>
                <a-button size="mini" @click="openRow(record)">编辑</a-button>
                <a-popconfirm content="确定删除该条个人数据？" @ok="removeRow(record.row_code)">
                  <a-button size="mini" status="danger">删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <a-empty v-else description="请先选择控件配置表" />

    <a-modal
      v-model:visible="rowModal"
      :title="rowEdit.row_code ? '编辑个人数据' : '新增个人数据'"
      :ok-text="'保存'"
      @ok="saveRow"
      @cancel="rowModal = false"
    >
      <a-form layout="vertical" :model="rowEdit">
        <a-row :gutter="[12, 8]">
          <a-col v-for="c in columns" :key="c.field_key" :span="columnSpan(c)">
            <a-form-item :label="c.label" required>
              <a-input v-model="rowEdit.data[c.field_key]" :placeholder="`请输入${c.label}`" />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  clearRecordSetCache,
  deleteMyRecord,
  loadMyRecordSetDetail,
  loadMyRecordSetsOverview,
  saveMyRecord,
  type MyRecordSetOverview,
  type RecordSetColumn,
  type RecordSetRow,
} from '@/composables/useRecordSets'
import { recordSetColumnSpan } from '@/utils/recordSetLayout'

const overview = ref<MyRecordSetOverview[]>([])
const filterForm = {}
const selectedCode = ref('')
const loading = ref(false)
const columns = ref<RecordSetColumn[]>([])
const rows = ref<RecordSetRow[]>([])
const rowModal = ref(false)
const rowEdit = reactive<{ row_code: string; data: Record<string, string> }>({
  row_code: '',
  data: {},
})

const setOpts = computed(() =>
  overview.value.map((s) => ({
    label: `${s.name}（${s.code}）${s.personal_count ? ` · ${s.personal_count}条` : ''}`,
    value: s.code,
  })),
)

function columnSpan(col: RecordSetColumn) {
  return recordSetColumnSpan(col)
}

async function loadOverview() {
  overview.value = await loadMyRecordSetsOverview()
}

async function loadDetail() {
  const code = selectedCode.value.trim()
  if (!code) {
    columns.value = []
    rows.value = []
    return
  }
  loading.value = true
  try {
    const payload = await loadMyRecordSetDetail(code)
    columns.value = payload?.columns || []
    rows.value = payload?.records || []
  } finally {
    loading.value = false
  }
}

function onSetChange() {
  void loadDetail()
}

function openRow(row?: RecordSetRow) {
  rowEdit.row_code = row?.row_code || ''
  const data: Record<string, string> = {}
  columns.value.forEach((c) => {
    data[c.field_key] = row?.data?.[c.field_key] != null ? String(row.data[c.field_key]) : ''
  })
  rowEdit.data = data
  rowModal.value = true
}

async function saveRow() {
  const code = selectedCode.value.trim()
  if (!code) return
  const data: Record<string, string> = {}
  for (const c of columns.value) {
    data[c.field_key] = String(rowEdit.data[c.field_key] || '').trim()
  }
  if (!Object.values(data).some(Boolean)) {
    Message.warning('请至少填写一个字段')
    return false
  }
  const res = await saveMyRecord(code, { row_code: rowEdit.row_code || undefined, data })
  if (!res.ok) {
    Message.error(res.message || '保存失败')
    return false
  }
  clearRecordSetCache()
  Message.success('已保存')
  rowModal.value = false
  await loadOverview()
  await loadDetail()
}

async function removeRow(rowCode: string) {
  const code = selectedCode.value.trim()
  if (!code) return
  const res = await deleteMyRecord(code, rowCode)
  if (res.data.ok) {
    clearRecordSetCache()
    Message.success('已删除')
    await loadOverview()
    await loadDetail()
  } else {
    Message.error(res.data.message || '删除失败')
  }
}

onMounted(async () => {
  await loadOverview()
})
</script>

<style scoped>
.hint-text {
  font-size: 13px;
  color: #86909c;
  margin: 0 0 12px;
  line-height: 1.5;
}
</style>
