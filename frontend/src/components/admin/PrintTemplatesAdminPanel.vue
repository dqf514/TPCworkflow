<template>
  <a-card class="settings-card" :bordered="false">
    <div class="flex flex-wrap justify-between gap-2 mb-3">
      <p class="text-sm text-gray-500 m-0">管理可配置打印模板：文案、Logo、公章、明细表列与邮件模板。</p>
      <a-button type="primary" @click="openEdit()">新建模板</a-button>
    </div>

    <a-table :data="rows" :loading="loading" row-key="id" :pagination="false">
      <template #columns>
        <a-table-column title="编码" data-index="code" :width="160" />
        <a-table-column title="名称" data-index="name" />
        <a-table-column title="分类" data-index="category" :width="100" />
        <a-table-column title="状态" :width="88">
          <template #cell="{ record }">
            <a-tag :color="record.is_active ? 'green' : 'gray'">
              {{ record.is_active ? '启用' : '停用' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="类型" :width="88">
          <template #cell="{ record }">
            <a-tag v-if="record.is_builtin" color="arcoblue">内置</a-tag>
            <span v-else>自定义</span>
          </template>
        </a-table-column>
        <a-table-column title="操作" :width="220">
          <template #cell="{ record }">
            <a-space>
              <a-button size="mini" @click="openEdit(record)">编辑</a-button>
              <a-button size="mini" @click="openClone(record)">克隆</a-button>
              <a-popconfirm
                v-if="!record.is_builtin"
                content="确定删除该模板？"
                @ok="removeRow(record.id)"
              >
                <a-button size="mini" status="danger">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>

    <a-modal
      v-model:visible="modalVisible"
      :title="edit.id ? `编辑模板：${edit.name}` : '新建打印模板'"
      :width="1080"
      ok-text="保存"
      :ok-loading="saving"
      unmount-on-close
      @ok="save"
    >
      <a-tabs v-model:active-key="editTab">
        <a-tab-pane key="basic" title="基本设置">
          <a-form layout="vertical">
            <a-row :gutter="12">
              <a-col :span="8">
                <a-form-item label="模板编码" required>
                  <a-input v-model="edit.code" :disabled="!!edit.id && edit.is_builtin" placeholder="debit_note_imc" />
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="模板名称" required>
                  <a-input v-model="edit.name" />
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="启用">
                  <a-switch v-model="edit.is_active" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-form-item label="说明">
              <a-input v-model="edit.description" />
            </a-form-item>
            <a-row :gutter="12">
              <a-col :span="8">
                <a-form-item label="纸张">
                  <a-select v-model="edit.schema.page!.size">
                    <a-option value="A4">A4</a-option>
                    <a-option value="A3">A3</a-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="方向">
                  <a-select v-model="edit.schema.page!.orientation">
                    <a-option value="portrait">纵向</a-option>
                    <a-option value="landscape">横向</a-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="边距 (mm)">
                  <a-input-number v-model="edit.schema.page!.marginMm" :min="5" :max="30" />
                </a-form-item>
              </a-col>
            </a-row>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="assets" title="图片资源">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="Logo 路径/URL">
                <a-input v-model="edit.schema.assets!.logo!.url" placeholder="uploads/attachments/xxx.png 或 /api/v1/files/..." />
              </a-form-item>
              <a-form-item label="Logo 宽度 (mm)">
                <a-input-number v-model="edit.schema.assets!.logo!.widthMm" :min="10" :max="80" />
              </a-form-item>
              <input ref="logoInput" type="file" accept="image/*" class="hidden" @change="onLogoFile" />
              <a-button size="small" :loading="logoUploading" @click="logoInput?.click()">上传 Logo</a-button>
            </a-col>
            <a-col :span="12">
              <a-form-item label="公章 路径/URL">
                <a-input v-model="edit.schema.assets!.seal!.url" placeholder="uploads/attachments/seal.png" />
              </a-form-item>
              <a-form-item label="公章 宽度 (mm)">
                <a-input-number v-model="edit.schema.assets!.seal!.widthMm" :min="10" :max="80" />
              </a-form-item>
              <input ref="sealInput" type="file" accept="image/*" class="hidden" @change="onSealFile" />
              <a-button size="small" :loading="sealUploading" @click="sealInput?.click()">上传公章</a-button>
            </a-col>
          </a-row>
        </a-tab-pane>

        <a-tab-pane key="content" title="区块内容">
          <a-collapse :default-active-key="['company', 'table', 'bank', 'email']">
            <a-collapse-item key="company" header="公司信息 (headerRight)">
              <a-textarea
                v-model="blocks.company_info.content"
                :auto-size="{ minRows: 4, maxRows: 8 }"
                placeholder="多行公司地址..."
              />
            </a-collapse-item>
            <a-collapse-item key="table" header="明细表 (Particulars)">
              <a-row :gutter="12" class="mb-2">
                <a-col :span="8">
                  <a-input v-model="blocks.particulars_table.title" placeholder="表格标题" />
                </a-col>
                <a-col :span="8">
                  <a-input v-model="blocks.particulars_table.currencyLabel" placeholder="USD ($)" />
                </a-col>
                <a-col :span="8">
                  <a-input v-model="blocks.particulars_table.fieldKey" placeholder="明细字段 key" />
                </a-col>
              </a-row>
              <div v-for="(col, ci) in blocks.particulars_table.columns || []" :key="ci" class="col-row">
                <a-input v-model="col.header" placeholder="列标题" style="width: 140px" />
                <a-input v-model="col.key" placeholder="字段 key" style="width: 120px" />
                <a-input v-model="col.width" placeholder="42%" style="width: 80px" />
                <a-button size="mini" status="danger" @click="removeColumn(ci)">删列</a-button>
              </div>
              <a-button size="mini" class="mt-2" @click="addColumn">添加列</a-button>
            </a-collapse-item>
            <a-collapse-item key="bank" header="付款信息 (Payment Advice)">
              <p class="hint">左侧为固定银行信息；右侧可绑定表单字段。</p>
              <div v-for="(item, i) in blocks.payment_advice.left || []" :key="`bl-${i}`" class="kv-row">
                <a-input v-model="item.label" placeholder="标签" style="width: 120px" />
                <a-input v-model="item.value" placeholder="固定值" />
                <a-button size="mini" status="danger" @click="removeKv('left', i)">删</a-button>
              </div>
              <a-button size="mini" @click="addKv('left')">添加左侧行</a-button>
              <a-divider />
              <div v-for="(item, i) in blocks.payment_advice.right || []" :key="`br-${i}`" class="kv-row">
                <a-input v-model="item.label" placeholder="标签" style="width: 120px" />
                <a-input v-model="item.fieldKey" placeholder="表单 fieldKey" />
                <a-button size="mini" status="danger" @click="removeKv('right', i)">删</a-button>
              </div>
              <a-button size="mini" @click="addKv('right')">添加右侧行</a-button>
            </a-collapse-item>
            <a-collapse-item key="sign" header="签名区">
              <div v-for="(line, i) in blocks.seal_sign.lines || []" :key="i" class="kv-row">
                <a-input v-model="blocks.seal_sign.lines![i]" />
              </div>
              <a-button size="mini" @click="blocks.seal_sign.lines!.push('')">添加签名行</a-button>
            </a-collapse-item>
          </a-collapse>
        </a-tab-pane>

        <a-tab-pane key="email" title="邮件模板">
          <a-radio-group v-model="emailLang" type="button" class="mb-3">
            <a-radio value="en">English</a-radio>
            <a-radio value="zh">中文</a-radio>
          </a-radio-group>
          <a-form layout="vertical">
            <a-form-item label="邮件主题">
              <a-input v-model="currentEmail.subject" placeholder="Debit Note {{debit_note_no}}" />
            </a-form-item>
            <a-form-item label="称呼">
              <a-input v-model="currentEmail.greeting" placeholder="Dear {{recipient_name}}," />
            </a-form-item>
            <a-form-item label="正文">
              <a-textarea v-model="currentEmail.body" :auto-size="{ minRows: 6, maxRows: 12 }" />
            </a-form-item>
            <a-alert type="info">
              可用占位符：{{placeholderHint}}
            </a-alert>
          </a-form>
        </a-tab-pane>

        <a-tab-pane key="preview" title="预览">
          <div class="preview-frame">
            <ConfigurablePrintSheet
              v-if="edit.schema"
              :template-schema="edit.schema"
              :model-value="sampleData"
            />
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-modal>

    <a-modal v-model:visible="cloneVisible" title="克隆模板" @ok="doClone">
      <a-form layout="vertical">
        <a-form-item label="新编码" required>
          <a-input v-model="cloneForm.code" />
        </a-form-item>
        <a-form-item label="新名称" required>
          <a-input v-model="cloneForm.name" />
        </a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import ConfigurablePrintSheet from '@/components/print/ConfigurablePrintSheet.vue'
import type { PrintDetailColumn, PrintFieldItem, PrintTemplateRow, PrintTemplateSchema } from '@/types/printTemplate'
import { DEFAULT_PRINT_TEMPLATE_SCHEMA } from '@/types/printTemplate'

const loading = ref(false)
const saving = ref(false)
const rows = ref<PrintTemplateRow[]>([])
const modalVisible = ref(false)
const editTab = ref('basic')
const logoInput = ref<HTMLInputElement | null>(null)
const sealInput = ref<HTMLInputElement | null>(null)
const logoUploading = ref(false)
const sealUploading = ref(false)
const sampleData = ref<Record<string, unknown>>({})
const emailLang = ref('en')
const cloneVisible = ref(false)
const cloneSourceId = ref(0)
const cloneForm = reactive({ code: '', name: '' })

const edit = reactive({
  id: 0,
  code: '',
  name: '',
  description: '',
  category: 'invoice',
  is_builtin: false,
  is_active: true,
  schema: DEFAULT_PRINT_TEMPLATE_SCHEMA() as PrintTemplateSchema,
})

const placeholderHint = '{{debit_note_no}} {{re_subject}} {{issue_date}} {{total_amount}} {{currency}} {{recipient_name}} {{company_name}}'

const blocks = computed(() => {
  const b = edit.schema.blocks || {}
  if (!b.company_info) b.company_info = { type: 'richtext', content: '', align: 'right' }
  if (!b.particulars_table) {
    b.particulars_table = {
      type: 'detail_table',
      fieldKey: 'particulars',
      title: 'PARTICULARS',
      currencyLabel: 'USD ($)',
      columns: [],
      showTotal: true,
      totalLabel: 'Total',
      totalFieldKey: 'total_amount',
    }
  }
  if (!b.payment_advice) b.payment_advice = { type: 'kv_section', showDivider: true, left: [], right: [] }
  if (!b.seal_sign) b.seal_sign = { type: 'signature', showSeal: true, lines: [] }
  if (!edit.schema.assets) edit.schema.assets = { logo: {}, seal: {} }
  if (!edit.schema.assets.logo) edit.schema.assets.logo = {}
  if (!edit.schema.assets.seal) edit.schema.assets.seal = {}
  if (!edit.schema.page) edit.schema.page = { size: 'A4', orientation: 'portrait', marginMm: 10 }
  if (!edit.schema.emailTemplates) edit.schema.emailTemplates = { en: {}, zh: {} }
  edit.schema.blocks = b
  return b
})

const currentEmail = computed({
  get() {
    if (!edit.schema.emailTemplates) edit.schema.emailTemplates = {}
    if (!edit.schema.emailTemplates[emailLang.value]) {
      edit.schema.emailTemplates[emailLang.value] = { subject: '', greeting: '', body: '' }
    }
    return edit.schema.emailTemplates[emailLang.value]!
  },
  set(v) {
    if (!edit.schema.emailTemplates) edit.schema.emailTemplates = {}
    edit.schema.emailTemplates[emailLang.value] = v
  },
})

async function load() {
  loading.value = true
  try {
    const res = await api.get<ApiResponse<PrintTemplateRow[]>>('/admin/print-templates')
    if (res.data.ok) rows.value = res.data.data
  } finally {
    loading.value = false
  }
}

async function loadSample() {
  const res = await api.get<ApiResponse<Record<string, unknown>>>('/print-templates/sample-data')
  if (res.data.ok) sampleData.value = res.data.data
}

function resetEdit() {
  edit.id = 0
  edit.code = ''
  edit.name = ''
  edit.description = ''
  edit.category = 'custom'
  edit.is_builtin = false
  edit.is_active = true
  edit.schema = DEFAULT_PRINT_TEMPLATE_SCHEMA()
}

async function openEdit(row?: PrintTemplateRow) {
  resetEdit()
  editTab.value = 'basic'
  if (row?.id) {
    const res = await api.get<ApiResponse<PrintTemplateRow>>(`/admin/print-templates/${row.id}`)
    if (!res.data.ok) return
    const d = res.data.data
    edit.id = d.id
    edit.code = d.code
    edit.name = d.name
    edit.description = d.description || ''
    edit.category = d.category || 'custom'
    edit.is_builtin = !!d.is_builtin
    edit.is_active = d.is_active !== false
    edit.schema = JSON.parse(JSON.stringify(d.schema || DEFAULT_PRINT_TEMPLATE_SCHEMA()))
  }
  modalVisible.value = true
}

function openClone(row: PrintTemplateRow) {
  cloneSourceId.value = row.id
  cloneForm.code = `${row.code}_copy`
  cloneForm.name = `${row.name} (副本)`
  cloneVisible.value = true
}

async function doClone() {
  await api.post(`/admin/print-templates/${cloneSourceId.value}/clone`, {
    code: cloneForm.code.trim(),
    name: cloneForm.name.trim(),
  })
  Message.success('已克隆')
  cloneVisible.value = false
  await load()
}

async function save() {
  saving.value = true
  try {
    const payload = {
      code: edit.code.trim(),
      name: edit.name.trim(),
      description: edit.description,
      category: edit.category,
      is_active: edit.is_active,
      schema: edit.schema,
    }
    if (edit.id) {
      await api.put(`/admin/print-templates/${edit.id}`, payload)
    } else {
      await api.post('/admin/print-templates', payload)
    }
    Message.success('已保存')
    modalVisible.value = false
    await load()
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeRow(id: number) {
  await api.delete(`/admin/print-templates/${id}`)
  Message.success('已删除')
  await load()
}

function addColumn() {
  const cols = blocks.value.particulars_table.columns || []
  cols.push({ key: '', header: '', width: '20%' } as PrintDetailColumn)
  blocks.value.particulars_table.columns = cols
}

function removeColumn(i: number) {
  blocks.value.particulars_table.columns?.splice(i, 1)
}

function addKv(side: 'left' | 'right') {
  const list = side === 'left' ? blocks.value.payment_advice.left : blocks.value.payment_advice.right
  if (!list) {
    if (side === 'left') blocks.value.payment_advice.left = []
    else blocks.value.payment_advice.right = []
  }
  ;(side === 'left' ? blocks.value.payment_advice.left : blocks.value.payment_advice.right)!.push({
    label: '',
    value: '',
  } as PrintFieldItem)
}

function removeKv(side: 'left' | 'right', i: number) {
  if (side === 'left') blocks.value.payment_advice.left?.splice(i, 1)
  else blocks.value.payment_advice.right?.splice(i, 1)
}

async function uploadImage(file: File, target: 'logo' | 'seal') {
  const fd = new FormData()
  fd.append('file', file)
  const loadingRef = target === 'logo' ? logoUploading : sealUploading
  loadingRef.value = true
  try {
    const res = await api.post<ApiResponse<{ path?: string; url?: string }>>('/uploads/attachments', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (res.data.ok) {
      const path = res.data.data.path || res.data.data.url || ''
      if (target === 'logo') edit.schema.assets!.logo!.url = path
      else edit.schema.assets!.seal!.url = path
      Message.success('上传成功')
    }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '上传失败')
  } finally {
    loadingRef.value = false
  }
}

function onLogoFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) void uploadImage(f, 'logo')
  ;(e.target as HTMLInputElement).value = ''
}

function onSealFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) void uploadImage(f, 'seal')
  ;(e.target as HTMLInputElement).value = ''
}

watch(modalVisible, (v) => {
  if (v && !Object.keys(sampleData.value).length) void loadSample()
})

onMounted(() => {
  void load()
  void loadSample()
})
</script>

<style scoped>
.hidden {
  display: none;
}
.col-row,
.kv-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}
.preview-frame {
  border: 1px solid #e5e7eb;
  background: #f3f4f6;
  padding: 12px;
  max-height: 70vh;
  overflow: auto;
}
.hint {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 8px;
}
</style>
