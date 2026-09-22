<template>
  <div class="mapping-manager">
    <div class="mapping-toolbar">
      <a-space wrap>
        <a-button type="primary" :disabled="!sectorId" @click="openCreate">新建映射方案</a-button>
        <a-dropdown :disabled="!sectorId" @select="cloneFromBuiltin">
          <a-button>从内置方案复制</a-button>
          <template #content>
            <a-doption v-for="tpl in builtinTemplates" :key="tpl.id" :value="tpl.id">
              {{ tpl.name }}
            </a-doption>
          </template>
        </a-dropdown>
        <a-button :disabled="!sectorId" @click="loadMappings">刷新</a-button>
      </a-space>
    </div>

    <a-table
      :data="mappings"
      :loading="loading"
      row-key="id"
      :bordered="false"
      :pagination="false"
    >
      <template #columns>
        <a-table-column title="方案名称" data-index="name" :width="180" />
        <a-table-column title="分录模式" :width="200">
          <template #cell="{ record }">
            {{ lineModeLabel(record.line_mode) }}
          </template>
        </a-table-column>
        <a-table-column title="适用流程" :width="220">
          <template #cell="{ record }">
            {{ formatDefinitionNames(record.definition_ids) }}
          </template>
        </a-table-column>
        <a-table-column title="映射列数" :width="100">
          <template #cell="{ record }">
            {{ record.column_mappings?.length || 0 }}
          </template>
        </a-table-column>
        <a-table-column title="状态" :width="80">
          <template #cell="{ record }">
            <a-tag :color="record.is_active ? 'green' : 'gray'">
              {{ record.is_active ? '启用' : '停用' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="操作" :width="160" fixed="right">
          <template #cell="{ record }">
            <a-space>
              <a-button type="text" size="small" @click="openEdit(record)">编辑</a-button>
              <a-popconfirm content="确定删除该映射方案？" @ok="removeMapping(record.id)">
                <a-button type="text" size="small" status="danger">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>

    <a-drawer
      v-model:visible="editorVisible"
      :title="editorId ? '编辑映射方案' : '新建映射方案'"
      :width="920"
      unmount-on-close
      :footer="false"
      @cancel="editorVisible = false"
    >
      <a-form layout="vertical" :model="form">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="方案名称" required>
              <a-input v-model="form.name" placeholder="如：财务报销凭证" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="分录模式">
              <a-select v-model="form.line_mode" :options="lineModeOpts" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="说明">
          <a-textarea v-model="form.description" :auto-size="{ minRows: 2, maxRows: 4 }" />
        </a-form-item>

        <a-form-item label="适用流程（可多选）">
          <a-select
            v-model="form.definition_ids"
            :options="definitionOpts"
            multiple
            allow-search
            placeholder="选择本方案适用的流程定义"
            @change="onDefinitionsChange"
          />
        </a-form-item>

        <a-row v-if="form.line_mode === 'expense_detail'" :gutter="16">
          <a-col :span="12">
            <a-form-item label="明细字段 key">
              <a-input v-model="form.detail_key" placeholder="如 expense_items" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="金额列 key">
              <a-input v-model="form.amount_source_key" placeholder="如 amount" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">导出默认参数</a-divider>
        <div class="export-options-grid">
          <a-form-item
            v-for="opt in exportOptionRows"
            :key="opt.key"
            :label="opt.label"
            class="export-option-item"
          >
            <a-switch
              v-if="opt.type === 'switch'"
              v-model="form.export_options[opt.key]"
            />
            <a-input
              v-else
              v-model="form.export_options[opt.key]"
              :placeholder="opt.placeholder || ''"
              allow-clear
            />
          </a-form-item>
        </div>

        <a-divider orientation="left">
          模板列映射
          <a-button type="text" size="small" @click="addColumnMapping">添加映射</a-button>
        </a-divider>

        <a-table
          :data="form.column_mappings"
          row-key="_uid"
          :pagination="false"
          :bordered="false"
          size="small"
          :scroll="{ x: 860 }"
        >
          <template #columns>
            <a-table-column title="模板列" :width="220">
              <template #cell="{ record }">
                <a-select
                  v-model="record.template_key"
                  :options="templateColumnOpts"
                  allow-search
                  placeholder="选择用友模板列"
                  @change="(v: string) => syncTemplateLabel(record, v)"
                />
              </template>
            </a-table-column>
            <a-table-column title="数据来源" :width="130">
              <template #cell="{ record }">
                <a-select v-model="record.source_type" :options="sourceTypeOpts" />
              </template>
            </a-table-column>
            <a-table-column title="来源字段 / 固定值" :width="220">
              <template #cell="{ record }">
                <a-input
                  v-if="record.source_type === 'constant'"
                  v-model="record.constant_value"
                  placeholder="固定写入模板的值"
                />
                <a-select
                  v-else-if="record.source_type === 'export_option'"
                  v-model="record.source_key"
                  :options="exportOptionKeyOpts"
                  allow-search
                  placeholder="导出参数 key"
                />
                <a-select
                  v-else
                  v-model="record.source_key"
                  :options="workflowFieldOpts"
                  allow-search
                  allow-create
                  placeholder="选择或输入字段 key"
                />
              </template>
            </a-table-column>
            <a-table-column title="值映射表" :width="220">
              <template #cell="{ record }">
                <a-button size="mini" @click="openLookupEditor(record)">
                  {{ lookupCount(record) ? `已配置 ${lookupCount(record)} 项` : '编辑映射' }}
                </a-button>
              </template>
            </a-table-column>
            <a-table-column title="" :width="60">
              <template #cell="{ record }">
                <a-button
                  type="text"
                  status="danger"
                  size="small"
                  @click="removeColumnMapping(record._uid!)"
                >
                  删除
                </a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>

        <a-form-item label="启用" class="mt-4">
          <a-switch v-model="form.is_active" />
        </a-form-item>

        <div class="drawer-footer">
          <a-space>
            <a-button @click="editorVisible = false">取消</a-button>
            <a-button type="primary" :loading="saving" @click="saveMapping">保存</a-button>
          </a-space>
        </div>
      </a-form>
    </a-drawer>

    <a-modal
      v-model:visible="lookupVisible"
      title="编辑值映射表"
      :width="560"
      unmount-on-close
      @ok="applyLookup"
    >
      <p class="lookup-hint">将工作流字段值转换为写入用友模板的值，例如消费类别 → 科目编码。</p>
      <div v-for="(row, idx) in lookupRows" :key="idx" class="lookup-row">
        <a-input v-model="row.source" placeholder="源值" />
        <span class="lookup-arrow">→</span>
        <a-input v-model="row.target" placeholder="目标值" />
        <a-button type="text" status="danger" @click="lookupRows.splice(idx, 1)">删</a-button>
      </div>
      <a-button long class="mt-2" @click="lookupRows.push({ source: '', target: '' })">添加一行</a-button>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'

interface ColumnMapping {
  _uid?: string
  template_key: string
  template_label?: string
  source_type: string
  source_key: string
  constant_value?: string
  lookup?: Record<string, string>
}

interface MappingRow {
  id: number
  name: string
  description?: string
  definition_ids: number[]
  line_mode: string
  detail_key?: string
  amount_source_key?: string
  column_mappings: ColumnMapping[]
  export_options: Record<string, string | boolean>
  is_active: boolean
}

interface TemplateColumn {
  key: string
  uid: string
  label: string
}

interface WorkflowField {
  key: string
  label: string
  scope: string
  detail_key?: string
  group?: string
}

const props = defineProps<{ sectorId?: number }>()

const loading = ref(false)
const saving = ref(false)
const mappings = ref<MappingRow[]>([])
const templateColumns = ref<TemplateColumn[]>([])
const workflowFields = ref<WorkflowField[]>([])
const workflowDefinitions = ref<{ id: number; name: string }[]>([])
const builtinTemplates = ref<{ id: string; name: string }[]>([])
const lineModeOpts = ref<{ label: string; value: string }[]>([])
const sourceTypeOpts = ref<{ label: string; value: string }[]>([])
const exportOptionRows = ref<
  { key: string; label: string; type?: string; placeholder?: string }[]
>([])

const editorVisible = ref(false)
const editorId = ref<number | null>(null)
const lookupVisible = ref(false)
const lookupRows = ref<{ source: string; target: string }[]>([])
const lookupTarget = ref<ColumnMapping | null>(null)

let uidSeq = 1
function nextUid() {
  uidSeq += 1
  return `cm-${uidSeq}`
}

const emptyForm = () => ({
  name: '',
  description: '',
  definition_ids: [] as number[],
  line_mode: 'expense_detail',
  detail_key: 'expense_items',
  amount_source_key: 'amount',
  column_mappings: [] as ColumnMapping[],
  export_options: {} as Record<string, string | boolean>,
  is_active: true,
})

const form = reactive(emptyForm())

const definitionOpts = computed(() =>
  workflowDefinitions.value.map((d) => ({ label: d.name, value: d.id })),
)

const templateColumnOpts = computed(() =>
  templateColumns.value.map((c) => ({
    label: `${c.label}（${c.key}）`,
    value: c.key,
  })),
)

const workflowFieldOpts = computed(() =>
  workflowFields.value.map((f) => ({
    label: `[${f.group || f.scope}] ${f.label}（${f.key}）`,
    value: f.scope === 'detail' && f.detail_key ? `${f.detail_key}.${f.key}` : f.key,
  })),
)

const exportOptionKeyOpts = computed(() =>
  exportOptionRows.value.map((o) => ({ label: o.label, value: o.key })),
)

function lineModeLabel(mode: string) {
  return lineModeOpts.value.find((o) => o.value === mode)?.label || mode
}

function formatDefinitionNames(ids: number[]) {
  if (!ids?.length) return '未限定（按内置规则匹配）'
  return ids
    .map((id) => workflowDefinitions.value.find((d) => d.id === id)?.name || `#${id}`)
    .join('、')
}

function lookupCount(record: ColumnMapping) {
  return Object.keys(record.lookup || {}).filter((k) => k).length
}

function syncTemplateLabel(record: ColumnMapping, key: string) {
  const col = templateColumns.value.find((c) => c.key === key)
  record.template_label = col?.label || key
}

function addColumnMapping() {
  form.column_mappings.push({
    _uid: nextUid(),
    template_key: '',
    template_label: '',
    source_type: 'form',
    source_key: '',
    constant_value: '',
    lookup: {},
  })
}

function removeColumnMapping(uid: string) {
  const idx = form.column_mappings.findIndex((r) => r._uid === uid)
  if (idx >= 0) form.column_mappings.splice(idx, 1)
}

function openLookupEditor(record: ColumnMapping) {
  lookupTarget.value = record
  const lookup = record.lookup || {}
  lookupRows.value = Object.entries(lookup).map(([source, target]) => ({ source, target }))
  if (!lookupRows.value.length) lookupRows.value.push({ source: '', target: '' })
  lookupVisible.value = true
}

function applyLookup() {
  if (!lookupTarget.value) return
  const out: Record<string, string> = {}
  for (const row of lookupRows.value) {
    const s = row.source.trim()
    const t = row.target.trim()
    if (s && t) out[s] = t
  }
  lookupTarget.value.lookup = out
  lookupVisible.value = false
}

async function loadMeta() {
  const [colsRes, metaRes] = await Promise.all([
    api.get('/workflow/finance-export/template-columns') as Promise<{
      data: ApiResponse<TemplateColumn[]>
    }>,
    api.get('/workflow/finance-export/mapping-meta') as Promise<{
      data: ApiResponse<{
        line_modes: { value: string; label: string }[]
        source_types: { value: string; label: string }[]
        builtin_templates: { id: string; name: string }[]
      }>
    }>,
  ])
  if (colsRes.data.ok) templateColumns.value = colsRes.data.data
  if (metaRes.data.ok) {
    lineModeOpts.value = metaRes.data.data.line_modes
    sourceTypeOpts.value = metaRes.data.data.source_types
    builtinTemplates.value = metaRes.data.data.builtin_templates
  }
  const profRes = (await api.get('/workflow/finance-export/profiles')) as {
    data: ApiResponse<{ options: { key: string; label: string; type?: string; placeholder?: string }[] }[]>
  }
  if (profRes.data.ok && profRes.data.data.length) {
    const opts = profRes.data.data[0].options || []
    exportOptionRows.value = opts.map((o) => ({
      key: o.key,
      label: o.label,
      type: o.type,
      placeholder: o.placeholder,
    }))
  }
}

async function loadDefinitions() {
  if (!props.sectorId) {
    workflowDefinitions.value = []
    return
  }
  const res = (await api.get('/workflow/finance-export/workflow-definitions', {
    params: { sector_id: props.sectorId },
  })) as { data: ApiResponse<{ id: number; name: string }[]> }
  if (res.data.ok) workflowDefinitions.value = res.data.data
}

async function loadWorkflowFields(definitionIds: number[]) {
  if (!props.sectorId || !definitionIds.length) {
    workflowFields.value = []
    return
  }
  const res = (await api.get('/workflow/finance-export/workflow-fields', {
    params: {
      sector_id: props.sectorId,
      definition_ids: definitionIds.join(','),
    },
  })) as { data: ApiResponse<WorkflowField[]> }
  if (res.data.ok) workflowFields.value = res.data.data
}

async function loadMappings() {
  if (!props.sectorId) {
    mappings.value = []
    return
  }
  loading.value = true
  try {
    const res = (await api.get('/workflow/finance-export/mappings', {
      params: { sector_id: props.sectorId },
    })) as { data: ApiResponse<MappingRow[]> }
    if (res.data.ok) mappings.value = res.data.data
  } finally {
    loading.value = false
  }
}

function resetForm(data?: Partial<MappingRow>) {
  Object.assign(form, emptyForm())
  editorId.value = null
  if (!data) return
  editorId.value = data.id ?? null
  form.name = data.name || ''
  form.description = data.description || ''
  form.definition_ids = [...(data.definition_ids || [])]
  form.line_mode = data.line_mode || 'expense_detail'
  form.detail_key = data.detail_key || 'expense_items'
  form.amount_source_key = data.amount_source_key || 'amount'
  form.is_active = data.is_active !== false
  form.export_options = { ...(data.export_options || {}) }
  form.column_mappings = (data.column_mappings || []).map((cm) => ({
    ...cm,
    _uid: nextUid(),
    lookup: { ...(cm.lookup || {}) },
  }))
}

function openCreate() {
  resetForm()
  editorVisible.value = true
}

function openEdit(row: MappingRow) {
  resetForm(row)
  void loadWorkflowFields(form.definition_ids)
  editorVisible.value = true
}

async function cloneFromBuiltin(profileId: string) {
  if (!props.sectorId) return
  const res = (await api.get(`/workflow/finance-export/mappings/template/${profileId}`, {
    params: { sector_id: props.sectorId },
  })) as { data: ApiResponse<Partial<MappingRow>> }
  if (!res.data.ok) {
    Message.error(res.data.message || '加载模板失败')
    return
  }
  resetForm(res.data.data as MappingRow)
  editorVisible.value = true
}

function onDefinitionsChange(ids: number[]) {
  void loadWorkflowFields(ids)
}

function serializeForm() {
  return {
    name: form.name.trim(),
    description: form.description.trim(),
    definition_ids: form.definition_ids,
    line_mode: form.line_mode,
    detail_key: form.detail_key,
    amount_source_key: form.amount_source_key,
    is_active: form.is_active,
    export_options: form.export_options,
    column_mappings: form.column_mappings.map(({ _uid, ...rest }) => rest),
  }
}

async function saveMapping() {
  if (!props.sectorId) {
    Message.warning('请先选择业务板块')
    return false
  }
  if (!form.name.trim()) {
    Message.warning('请填写方案名称')
    return false
  }
  saving.value = true
  try {
    const body = { sector_id: props.sectorId, ...serializeForm() }
    if (editorId.value) {
      const res = (await api.put(`/workflow/finance-export/mappings/${editorId.value}`, body)) as {
        data: ApiResponse<MappingRow>
      }
      if (!res.data.ok) throw new Error(res.data.message || '保存失败')
    } else {
      const res = (await api.post('/workflow/finance-export/mappings', body)) as {
        data: ApiResponse<MappingRow>
      }
      if (!res.data.ok) throw new Error(res.data.message || '创建失败')
    }
    Message.success('映射方案已保存')
    editorVisible.value = false
    await loadMappings()
    return true
  } catch (err) {
    Message.error(err instanceof Error ? err.message : '保存失败')
    return false
  } finally {
    saving.value = false
  }
}

async function removeMapping(id: number) {
  const res = (await api.delete(`/workflow/finance-export/mappings/${id}`)) as {
    data: ApiResponse<unknown>
  }
  if (!res.data.ok) {
    Message.error(res.data.message || '删除失败')
    return
  }
  Message.success('已删除')
  await loadMappings()
}

watch(
  () => props.sectorId,
  async (id) => {
    if (id) {
      await loadDefinitions()
      await loadMappings()
    } else {
      mappings.value = []
      workflowDefinitions.value = []
    }
  },
  { immediate: true },
)

void loadMeta()
</script>

<style scoped>
.mapping-manager {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.mapping-toolbar {
  padding: 0.65rem 1rem 0;
}

.export-options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0 1rem;
}

.export-option-item {
  margin-bottom: 0.5rem;
}

.lookup-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.lookup-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.lookup-arrow {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.mt-2 {
  margin-top: 8px;
}

.mt-4 {
  margin-top: 16px;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid var(--border);
}
</style>
