<template>
  <div class="form-studio page-shell" :class="{ 'is-editing': editing }">
    <template v-if="!editing">
      <div class="studio-header flex flex-wrap justify-between gap-2 mb-4">
        <div>
          <h1 class="text-xl sm:text-2xl font-bold">{{ t('studio.title') }}</h1>
          <p class="text-sm text-gray-500 mt-1">
            {{ t('studio.subtitle') }}
          </p>
        </div>
        <a-button type="primary" @click="startCreate">{{ t('studio.new_form') }}</a-button>
      </div>

      <a-table
        :data="displayRows"
        :loading="loading"
        row-key="id"
        :pagination="listPagination"
        @page-change="onListPage"
        @page-size-change="onListPageSize"
        @sorter-change="onListSorterChange"
        @row-click="(r) => openEdit(r.id)"
      >
      <template #columns>
        <a-table-column :title="t('studio.col_name')" data-index="name" />
        <a-table-column :title="t('studio.col_key')" data-index="key" />
        <a-table-column
          :title="t('studio.col_sector')"
          data-index="sector_name"
          :width="168"
          :sortable="{ sortDirections: ['ascend', 'descend'] }"
          :sort-order="listSort.field === 'sector_name' ? listSort.direction || undefined : undefined"
        >
          <template #cell="{ record }">
            <a-select
              :model-value="record.business_sector_id as number | undefined"
              :options="sectorOpts"
              :placeholder="t('studio.sector_unset')"
              allow-clear
              size="small"
              class="studio-sector-select"
              :loading="sectorSavingId === record.id"
              @click.stop
              @change="(v: number | string | undefined) => saveRowSector(record, v)"
            />
          </template>
        </a-table-column>
        <a-table-column
          :title="t('studio.col_status')"
          data-index="status"
          :sortable="{ sortDirections: ['ascend', 'descend'] }"
          :sort-order="listSort.field === 'status' ? listSort.direction || undefined : undefined"
        >
          <template #cell="{ record }">
            <a-tag :color="record.status === 'published' ? 'green' : record.status === 'archived' ? 'gray' : 'orange'">
              {{
                record.status === 'published'
                  ? t('studio.status_published')
                  : record.status === 'archived'
                    ? t('studio.status_archived')
                    : t('studio.status_draft')
              }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column :title="t('studio.col_flow_id')" data-index="workflow_definition_id" />
        <a-table-column :title="t('studio.col_actions')" :width="300">
          <template #cell="{ record }">
            <a-space @click.stop>
              <a-button
                size="small"
                type="primary"
                :loading="editLoadingId === record.id"
                @click="openEdit(record.id)"
              >
                {{ t('studio.design') }}
              </a-button>
              <a-popconfirm
                v-if="record.status === 'published'"
                type="warning"
                :title="t('studio.unpublish_confirm_title')"
                :content="unpublishConfirmText(record)"
                :ok-text="t('studio.unpublish')"
                :cancel-text="t('common.cancel')"
                :ok-button-props="{ status: 'warning' }"
                @ok="unpublishForm(record.id as number)"
              >
                <a-button size="small">{{ t('studio.unpublish') }}</a-button>
              </a-popconfirm>
              <a-popconfirm
                v-if="record.status !== 'archived'"
                type="warning"
                :title="t('studio.archive_confirm_title')"
                :content="archiveConfirmText(record)"
                :ok-text="t('studio.delete')"
                :cancel-text="t('common.cancel')"
                :ok-button-props="{ status: 'danger' }"
                @ok="archiveForm(record.id)"
              >
                <a-button size="small" status="danger">{{ t('studio.delete') }}</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table-column>
      </template>
      </a-table>
    </template>

    <div v-else class="studio-editor">
      <header class="editor-toolbar">
        <div class="editor-meta-wrap min-w-0 flex-1">
          <table class="editor-meta-table">
            <tbody>
              <tr>
                <th>{{ t('studio.process_name') }}</th>
                <td class="col-grow">
                  <a-input
                    v-model="formMeta.name"
                    :placeholder="t('studio.form_name_ph')"
                    size="small"
                    @input="syncFormTitle"
                  />
                </td>
                <th>{{ t('studio.form_key_label') }}</th>
                <td class="col-key">
                  <a-input
                    v-model="formMeta.key"
                    :placeholder="t('studio.form_key_ph')"
                    size="small"
                    :disabled="!!formMeta.id"
                  />
                </td>
              </tr>
              <tr>
                <th>{{ t('studio.col_sector') }}</th>
                <td class="col-sector">
                  <a-select
                    v-model="formMeta.business_sector_id"
                    :options="sectorOpts"
                    :placeholder="t('studio.sector_ph')"
                    size="small"
                    allow-clear
                  />
                </td>
                <th>{{ t('studio.process_icon') }}</th>
                <td>
                  <div class="icon-cell">
                    <ProcessIcon :icon="formMeta.icon" :size="32" />
                    <a-button size="mini" @click="iconPickerOpen = true">{{ t('studio.pick_icon') }}</a-button>
                  </div>
                </td>
              </tr>
              <tr>
                <th class="align-top">{{ t('studio.form_description') }}</th>
                <td colspan="3">
                  <a-textarea
                    v-model="formMeta.description"
                    :placeholder="t('studio.form_description_ph')"
                    :auto-size="{ minRows: 1, maxRows: 3 }"
                    size="small"
                    @input="syncFormDescription"
                  />
                  <p class="form-desc-hint">{{ t('studio.form_description_hint') }}</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="toolbar-actions-col shrink-0">
          <a-space wrap>
            <a-button @click="openList">{{ t('studio.back_list') }}</a-button>
            <a-button type="primary" :loading="saving" @click="saveAll">{{ t('studio.save') }}</a-button>
            <a-button
              v-if="formMeta.status !== 'published'"
              type="primary"
              status="success"
              :loading="publishing"
              @click="publishAll"
            >
              {{ t('studio.publish') }}
            </a-button>
            <a-popconfirm
              v-else
              type="warning"
              :title="t('studio.unpublish_confirm_title')"
              :content="unpublishEditorConfirmText()"
              :ok-text="t('studio.unpublish')"
              :cancel-text="t('common.cancel')"
              :ok-button-props="{ status: 'warning' }"
              @ok="unpublishAll"
            >
              <a-button status="warning" :loading="unpublishing">{{ t('studio.unpublish') }}</a-button>
            </a-popconfirm>
            <a-popconfirm
              v-if="formMeta.id && formMeta.status !== 'archived'"
              type="warning"
              :title="t('studio.archive_confirm_title')"
              :content="archiveEditorConfirmText()"
              :ok-text="t('studio.delete')"
              :cancel-text="t('common.cancel')"
              :ok-button-props="{ status: 'danger' }"
              @ok="archiveForm(formMeta.id)"
            >
              <a-button status="danger">{{ t('studio.delete') }}</a-button>
            </a-popconfirm>
          </a-space>
          <p class="form-version-line">
            {{ formMeta.status === 'published' ? t('studio.current_version') : t('studio.status_draft') }}
            <span v-if="publishedVersionDate">
              ({{ formMeta.status === 'published' ? '' : `${t('studio.last_published')} ` }}{{ publishedVersionDate }})
            </span>
            <span v-else class="form-version-unpublished">({{ t('studio.version_unpublished') }})</span>
          </p>
        </div>
      </header>

      <a-tabs v-model:active-key="activeTab" type="rounded" class="studio-tabs" lazy-load>
        <a-tab-pane key="form" :title="t('studio.tab_form')">
          <div class="tab-panel">
            <FormDesigner v-model="schema" :current-form-key="formMeta.key" />
          </div>
        </a-tab-pane>
        <a-tab-pane key="flow" :title="t('studio.tab_flow')">
          <div class="tab-panel tab-panel-flow">
            <WorkflowDesigner
              ref="flowDesignerRef"
              v-model="processGraph"
              :form-schema="schema"
              min-height="min(65vh, 640px)"
            />
          </div>
        </a-tab-pane>
        <a-tab-pane key="settings" :title="t('studio.tab_settings')">
          <div class="tab-panel overflow-auto">
            <WorkflowSettingsPanel v-model="workflowSettings" v-model:scope-type="workflowScope" :form-schema="schema" />
          </div>
        </a-tab-pane>
        <a-tab-pane key="print" :title="t('studio.tab_print')">
          <div class="tab-panel print-settings bg-white p-4 rounded-lg border overflow-auto">
              <a-form layout="vertical">
                <a-form-item :label="t('studio.print_enable')">
                  <a-switch v-model="schema.print.enabled" />
                </a-form-item>
                <a-form-item label="模板类型">
                  <a-radio-group v-model="printTemplateMode" type="button">
                    <a-radio value="default">通用审批单</a-radio>
                    <a-radio value="custom">专用打印模板</a-radio>
                  </a-radio-group>
                </a-form-item>
                <a-form-item v-if="printTemplateMode === 'custom'" label="选择打印模板">
                  <a-select
                    v-model="printTemplateCode"
                    :options="printTemplateOpts"
                    allow-search
                    allow-clear
                    placeholder="从模板库选择"
                    class="w-full max-w-xl"
                    :trigger-props="{ updateAtScroll: true }"
                  />
                  <p class="text-xs text-gray-500 mt-1">
                    可在系统设置 → 打印模板 中调整 Logo、文案与银行信息。
                  </p>
                </a-form-item>
                <a-row :gutter="16">
                  <a-col :span="8">
                    <a-form-item :label="t('studio.print_paper')">
                      <a-select v-model="schema.print.pageSize">
                        <a-option value="A4">A4</a-option>
                        <a-option value="A3">A3</a-option>
                      </a-select>
                    </a-form-item>
                  </a-col>
                  <a-col :span="8">
                    <a-form-item :label="t('studio.print_orientation')">
                      <a-select v-model="schema.print.orientation">
                        <a-option value="portrait">{{ t('studio.print_portrait') }}</a-option>
                        <a-option value="landscape">{{ t('studio.print_landscape') }}</a-option>
                      </a-select>
                    </a-form-item>
                  </a-col>
                  <a-col :span="8">
                    <a-form-item :label="t('studio.print_margin')">
                      <a-input-number v-model="schema.print.marginMm" :min="5" :max="30" />
                    </a-form-item>
                  </a-col>
                </a-row>
                <a-form-item v-if="printTemplateMode === 'default'" :label="t('studio.print_header_opts')">
                  <a-checkbox v-model="schema.print.showTitle">{{ t('studio.print_show_title') }}</a-checkbox>
                  <a-checkbox v-model="schema.print.showDescription" class="ml-4">{{ t('studio.print_show_desc') }}</a-checkbox>
                  <a-checkbox v-model="schema.print.showInitiator" class="ml-4">{{ t('studio.print_show_initiator') }}</a-checkbox>
                  <a-checkbox v-model="schema.print.showCompany" class="ml-4">{{ t('studio.print_show_company') }}</a-checkbox>
                  <a-checkbox v-model="schema.print.showPrintTime" class="ml-4">{{ t('studio.print_show_time') }}</a-checkbox>
                  <a-checkbox v-model="schema.print.showApprovalHistory" class="ml-4">{{ t('studio.print_show_history') }}</a-checkbox>
                </a-form-item>
                <a-alert v-if="printTemplateMode === 'custom'" type="info">
                  专用模板模式下，打印输出由模板库配置驱动；请在「流程设置 → 单据投递」绑定收件人邮箱等字段。
                </a-alert>
                <a-alert v-else type="info">
                  {{ t('studio.print_field_hint') }}
                </a-alert>
              </a-form>
            </div>
          </a-tab-pane>
        <a-tab-pane key="preview" :title="t('studio.tab_preview')">
          <div class="tab-panel preview-wrap overflow-auto">
              <a-radio-group v-model="previewDevice" type="button" size="small" class="mb-3">
                <a-radio value="desktop">{{ t('designer.desktop') }}</a-radio>
                <a-radio value="mobile">{{ t('designer.mobile') }}</a-radio>
              </a-radio-group>
              <div :class="`device-frame frame-${previewDevice}`">
                <FormRenderer v-model="previewData" :schema="schema" :device="previewDevice" />
              </div>
              <a-button class="mt-3" @click="printPreview">{{ t('studio.preview_print') }}</a-button>
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>

    <a-modal
      v-model:visible="iconPickerOpen"
      :title="t('studio.pick_icon')"
      :width="560"
      unmount-on-close
    >
      <ProcessIconPicker v-model="formMeta.icon" />
    </a-modal>

    <a-modal
      v-model:visible="createModalVisible"
      :title="t('studio.create_modal_title')"
      :width="520"
      :mask-closable="false"
      @cancel="createModalVisible = false"
    >
      <a-form layout="vertical">
        <a-form-item :label="t('studio.form_name')" required>
          <a-input v-model="createForm.name" :placeholder="t('studio.form_name_ph')" />
        </a-form-item>
        <a-form-item :label="t('studio.form_key_label')" required>
          <a-input v-model="createForm.key" :placeholder="t('studio.form_key_ph')" :disabled="false" />
        </a-form-item>
        <a-form-item :label="t('studio.create_mode')">
          <a-radio-group v-model="createMode">
            <a-radio value="blank">{{ t('studio.create_blank') }}</a-radio>
            <a-radio value="builtin" :disabled="!builtinTemplateOptions.length">{{ t('studio.create_builtin') }}</a-radio>
            <a-radio value="copy" :disabled="!templateOptions.length">{{ t('studio.create_copy') }}</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item v-if="createMode === 'builtin'" :label="t('studio.pick_builtin')" required>
          <a-select
            v-model="createBuiltinKey"
            :placeholder="t('studio.builtin_ph')"
            allow-search
            :options="builtinTemplateOptions"
          />
          <p class="text-xs text-gray-500 mt-1">{{ t('studio.builtin_hint') }}</p>
        </a-form-item>
        <a-form-item v-if="createMode === 'copy'" :label="t('studio.pick_template')" required>
          <a-select
            v-model="createTemplateId"
            :placeholder="t('studio.template_ph')"
            allow-search
            :options="templateOptions"
          />
          <p v-if="!templateOptions.length" class="text-xs text-gray-500 mt-1">
            {{ t('studio.no_template') }}
          </p>
        </a-form-item>
        <a-alert v-if="createMode === 'builtin'" type="info" class="mt-2">
          {{ t('studio.builtin_alert') }}
        </a-alert>
        <a-alert v-if="createMode === 'copy'" type="info" class="mt-2">
          {{ t('studio.copy_hint') }}
        </a-alert>
      </a-form>
      <template #footer>
        <a-button @click="createModalVisible = false">{{ t('common.cancel') }}</a-button>
        <a-button type="primary" :loading="createLoading" @click="confirmCreate">{{ t('studio.start_design') }}</a-button>
      </template>
    </a-modal>

    <UnsavedLeaveModal
      v-model:visible="leaveModalVisible"
      :saving="leaveSaving"
      @cancel="cancelLeave"
      @discard="discardLeave"
      @save-and-leave="saveAndLeave"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import FormDesigner from '@/components/form/FormDesigner.vue'
import FormRenderer from '@/components/form/FormRenderer.vue'
import WorkflowDesigner from '@/components/WorkflowDesigner.vue'
import WorkflowSettingsPanel from '@/components/form/WorkflowSettingsPanel.vue'
import ProcessIcon from '@/components/apply/ProcessIcon.vue'
import ProcessIconPicker from '@/components/apply/ProcessIconPicker.vue'
import UnsavedLeaveModal from '@/components/common/UnsavedLeaveModal.vue'
import { useUnsavedLeaveGuard } from '@/composables/useUnsavedLeaveGuard'
import { DEFAULT_FORM_SCHEMA, type FormSchema } from '@/types/form'
import {
  DEFAULT_WORKFLOW_SETTINGS,
  mergeWorkflowSettings,
  type WorkflowSettings,
} from '@/types/workflowSettings'
import type { PrintTemplateRow } from '@/types/printTemplate'

const { t } = useI18n()

function formatPublishedVersionDate(raw: string | null | undefined) {
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function defaultProcessGraph() {
  return {
    nodes: [
      { id: 'start', type: 'start', x: 120, y: 280 },
      {
        id: 'approve1',
        type: 'approver',
        x: 360,
        y: 280,
        config: { assignee_type: 'flow_role', flow_role_code: 'dept_leader', apv_rel: 'or' },
      },
      { id: 'end', type: 'end', x: 600, y: 280 },
    ],
    edges: [
      { source: 'start', target: 'approve1' },
      { source: 'approve1', target: 'end' },
    ],
  }
}

const LIST_PAGE_SIZE_KEY = 'form-studio-list-page-size'

function readListPageSize() {
  try {
    const raw = localStorage.getItem(LIST_PAGE_SIZE_KEY)
    const n = raw ? Number(raw) : 20
    return [10, 20, 50, 100].includes(n) ? n : 20
  } catch {
    return 20
  }
}

const listPagination = reactive({
  current: 1,
  pageSize: readListPageSize(),
  total: 0,
  showTotal: true,
  showPageSize: true,
  pageSizeOptions: [10, 20, 50, 100],
})

function onListPage(page: number) {
  listPagination.current = page
}

function onListPageSize(size: number) {
  listPagination.pageSize = size
  listPagination.current = 1
  try {
    localStorage.setItem(LIST_PAGE_SIZE_KEY, String(size))
  } catch {
    /* ignore */
  }
}

function syncListPaginationTotal() {
  listPagination.total = displayRows.value.length
  const maxPage = Math.max(1, Math.ceil(displayRows.value.length / listPagination.pageSize) || 1)
  if (listPagination.current > maxPage) {
    listPagination.current = maxPage
  }
}

const STATUS_SORT_ORDER: Record<string, number> = {
  published: 0,
  draft: 1,
  archived: 2,
}

const listSort = reactive<{
  field: 'sector_name' | 'status' | null
  direction: 'ascend' | 'descend' | null
}>({
  field: null,
  direction: null,
})

function compareFormRowName(a: Record<string, unknown>, b: Record<string, unknown>) {
  return String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN')
}

function formDisplayName(record: Record<string, unknown>) {
  return String(record.name || record.key || '').trim()
}

function unpublishConfirmText(record: Record<string, unknown>) {
  return t('studio.unpublish_confirm_named', { name: formDisplayName(record) })
}

function archiveConfirmText(record: Record<string, unknown>) {
  const name = formDisplayName(record)
  if (record.status === 'published') {
    return t('studio.archive_confirm_published', { name })
  }
  return t('studio.archive_confirm_named', { name })
}

function unpublishEditorConfirmText() {
  return t('studio.unpublish_confirm_named', {
    name: (formMeta.name || formMeta.key || '').trim(),
  })
}

function archiveEditorConfirmText() {
  const name = (formMeta.name || formMeta.key || '').trim()
  if (formMeta.status === 'published') {
    return t('studio.archive_confirm_published', { name })
  }
  return t('studio.archive_confirm_named', { name })
}

function sectorSortKey(raw: unknown) {
  const name = String(raw || '').trim()
  return name || '\uFFFF'
}

const displayRows = computed(() => {
  const list = [...rows.value]
  if (!listSort.field || !listSort.direction) return list
  const dir = listSort.direction === 'ascend' ? 1 : -1
  return list.sort((a, b) => {
    let cmp = 0
    if (listSort.field === 'status') {
      const av = STATUS_SORT_ORDER[String(a.status)] ?? 99
      const bv = STATUS_SORT_ORDER[String(b.status)] ?? 99
      cmp = av - bv
    } else {
      cmp = sectorSortKey(a.sector_name).localeCompare(sectorSortKey(b.sector_name), 'zh-CN')
    }
    return cmp * dir || compareFormRowName(a, b)
  })
})

function onListSorterChange(dataIndex: string, direction: 'ascend' | 'descend' | '') {
  if (!direction) {
    listSort.field = null
    listSort.direction = null
  } else if (dataIndex === 'sector_name' || dataIndex === 'status') {
    listSort.field = dataIndex
    listSort.direction = direction
  }
  listPagination.current = 1
  syncListPaginationTotal()
}

const rows = ref<Record<string, unknown>[]>([])
const loading = ref(false)
const editLoadingId = ref<number | null>(null)
const editing = ref(false)
const saving = ref(false)
const publishing = ref(false)
const unpublishing = ref(false)
const activeTab = ref('form')
const previewDevice = ref<'desktop' | 'mobile'>('desktop')
const previewData = ref<Record<string, unknown>>({})
const flowDesignerRef = ref<{ resize?: () => void } | null>(null)

const iconPickerOpen = ref(false)
const formMeta = reactive({
  id: 0,
  key: '',
  name: '',
  description: '',
  business_sector_id: undefined as number | undefined,
  icon: 'general',
  status: 'draft' as string,
  published_at: null as string | null,
})

const publishedVersionDate = computed(() => formatPublishedVersionDate(formMeta.published_at))
const sectorOpts = ref<{ label: string; value: number }[]>([])
const sectorSavingId = ref<number | null>(null)
const schema = ref<FormSchema>(DEFAULT_FORM_SCHEMA())
const processGraph = ref<{ nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] }>(
  defaultProcessGraph(),
)
const workflowSettings = ref<WorkflowSettings>(DEFAULT_WORKFLOW_SETTINGS())
const workflowScope = ref('global')
const workflowDefId = ref<number>()
const savedSnapshot = ref('')
const createModalVisible = ref(false)
const createLoading = ref(false)
const createMode = ref<'blank' | 'copy' | 'builtin'>('blank')
const createTemplateId = ref<number>()
const createBuiltinKey = ref<string>()
const createForm = reactive({ key: '', name: '' })

const builtinTemplates = ref<{ key: string; name: string; description?: string; icon?: string }[]>([])
const printTemplateOpts = ref<{ label: string; value: string }[]>([])

function ensurePrintConfig(s: FormSchema) {
  if (!s.print) s.print = DEFAULT_FORM_SCHEMA().print
  if (!s.print.templateMode) s.print.templateMode = 'default'
  if (s.print.templateCode === undefined) s.print.templateCode = ''
}

const printTemplateMode = computed({
  get: () => schema.value.print?.templateMode || 'default',
  set: (v: 'default' | 'custom') => {
    if (!schema.value.print) schema.value.print = DEFAULT_FORM_SCHEMA().print
    schema.value.print.templateMode = v
    if (v === 'custom') {
      if (schema.value.print.templateCode === undefined) schema.value.print.templateCode = ''
      schema.value.print.showTitle = false
      schema.value.print.showInitiator = false
      schema.value.print.showCompany = false
      schema.value.print.showPrintTime = false
      schema.value.print.showApprovalHistory = false
    }
  },
})

const printTemplateCode = computed({
  get: () => schema.value.print?.templateCode || '',
  set: (code: string | undefined) => {
    if (!schema.value.print) schema.value.print = DEFAULT_FORM_SCHEMA().print
    schema.value.print.templateCode = code || ''
  },
})

async function loadPrintTemplates() {
  try {
    const res = await api.get<ApiResponse<PrintTemplateRow[]>>('/print-templates')
    if (res.data.ok) {
      printTemplateOpts.value = res.data.data.map((r) => ({
        label: `${r.name} (${r.code})`,
        value: r.code,
      }))
    }
  } catch {
    printTemplateOpts.value = []
  }
}

const templateOptions = computed(() =>
  rows.value.map((r) => ({
    label: `${r.name}（${r.status === 'published' ? t('studio.status_published') : t('studio.status_draft')}）`,
    value: r.id as number,
  })),
)

const builtinTemplateOptions = computed(() =>
  builtinTemplates.value.map((item) => ({
    label: item.name,
    value: item.key,
  })),
)

function resizeFlowDesigner() {
  nextTick(() => flowDesignerRef.value?.resize?.())
}

watch(activeTab, (tab) => {
  if (tab === 'flow' && editing.value) resizeFlowDesigner()
  // 打印/流程等 Tab 直接改父级 schema，回到表单 Tab 时触发 FormDesigner 重新同步
  if (tab === 'form' && editing.value) {
    schema.value = JSON.parse(JSON.stringify(schema.value))
  }
})

watch(editing, (open) => {
  if (open) resizeFlowDesigner()
})

async function loadBuiltinTemplates() {
  try {
    const res = await api.get<
      ApiResponse<{ key: string; name: string; description?: string; icon?: string }[]>
    >('/forms/builtin-templates')
    if (res.data.ok) builtinTemplates.value = res.data.data
  } catch {
    builtinTemplates.value = []
  }
}

async function load() {
  loading.value = true
  const res = await api.get<ApiResponse<Record<string, unknown>[]>>('/forms/definitions')
  if (res.data.ok) rows.value = res.data.data
  syncListPaginationTotal()
  loading.value = false
}

async function archiveForm(id: number) {
  try {
    await api.delete(`/forms/definitions/${id}`)
    Message.success(t('studio.archived_ok'))
    if (formMeta.id === id) editing.value = false
    await load()
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('studio.delete_failed'))
  }
}

function openList() {
  requestLeave(() => {
    editing.value = false
    savedSnapshot.value = ''
    load()
  })
}

function resetWorkflowSettings() {
  workflowSettings.value = DEFAULT_WORKFLOW_SETTINGS()
  workflowScope.value = 'global'
}

function syncFormDescription() {
  schema.value.description = formMeta.description || ''
}

function syncFormTitle() {
  schema.value.title = formMeta.name || schema.value.title
}

function applyBlankDraft(key: string, name: string, description = '') {
  Object.assign(formMeta, { id: 0, key, name, description, icon: 'general', status: 'draft', published_at: null })
  schema.value = DEFAULT_FORM_SCHEMA()
  ensurePrintConfig(schema.value)
  schema.value.title = name
  syncFormDescription()
  processGraph.value = defaultProcessGraph()
  resetWorkflowSettings()
  workflowDefId.value = undefined
}

function applyFromTemplate(data: Record<string, unknown>, key: string, name: string) {
  Object.assign(formMeta, {
    id: 0,
    key,
    name,
    description: (data.description as string) || '',
    icon: (data.icon as string) || 'general',
    status: 'draft',
    published_at: null,
  })
  schema.value = JSON.parse(JSON.stringify(data.schema)) as FormSchema
  ensurePrintConfig(schema.value)
  schema.value.title = name
  if (!formMeta.description && schema.value.description) {
    formMeta.description = schema.value.description
  }
  syncFormDescription()
  const wf = data.workflow as Record<string, unknown> | undefined
  if (wf?.process_graph) {
    processGraph.value = JSON.parse(JSON.stringify(wf.process_graph)) as typeof processGraph.value
    const s = wf.settings as Partial<WorkflowSettings> | undefined
    if (s) workflowSettings.value = mergeWorkflowSettings(s)
    workflowScope.value = (wf.scope_type as string) || 'global'
  } else {
    processGraph.value = defaultProcessGraph()
    resetWorkflowSettings()
  }
  workflowDefId.value = undefined
}

function startCreate() {
  createForm.key = ''
  createForm.name = ''
  createMode.value = 'blank'
  createTemplateId.value = undefined
  createBuiltinKey.value = builtinTemplates.value[0]?.key
  createModalVisible.value = true
}

async function confirmCreate() {
  const key = createForm.key.trim()
  const name = createForm.name.trim()
  if (!key || !name) {
    Message.warning(t('studio.fill_name_key'))
    return
  }
  if (rows.value.some((r) => r.key === key)) {
    Message.warning(t('studio.key_exists'))
    return
  }
  if (createMode.value === 'builtin') {
    if (!createBuiltinKey.value) {
      Message.warning(t('studio.pick_builtin_template'))
      return
    }
    createLoading.value = true
    try {
      const res = await api.get<ApiResponse<Record<string, unknown>>>(
        `/forms/builtin-templates/${createBuiltinKey.value}`,
      )
      if (!res.data.ok) return
      applyFromTemplate(res.data.data, key, name)
      createModalVisible.value = false
      activeTab.value = 'form'
      editing.value = true
      resizeFlowDesigner()
      enterEditingMode()
      Message.success(t('studio.builtin_loaded_ok'))
    } catch (e) {
      Message.error(e instanceof Error ? e.message : t('studio.load_template_failed'))
    } finally {
      createLoading.value = false
    }
    return
  }
  if (createMode.value === 'copy') {
    if (!createTemplateId.value) {
      Message.warning(t('studio.pick_copy_template'))
      return
    }
    createLoading.value = true
    try {
      const res = await api.get<ApiResponse<Record<string, unknown>>>(
        `/forms/definitions/${createTemplateId.value}`,
      )
      if (!res.data.ok) return
      applyFromTemplate(res.data.data, key, name)
      createModalVisible.value = false
      activeTab.value = 'form'
      editing.value = true
      resizeFlowDesigner()
      enterEditingMode()
      Message.success(t('studio.copied_ok'))
    } catch (e) {
      Message.error(e instanceof Error ? e.message : t('studio.load_template_failed'))
    } finally {
      createLoading.value = false
    }
    return
  }
  applyBlankDraft(key, name)
  createModalVisible.value = false
  activeTab.value = 'form'
  editing.value = true
  resizeFlowDesigner()
  enterEditingMode()
}

function openEdit(id?: number) {
  if (!id) {
    startCreate()
    return
  }
  void loadFormForEdit(id)
}

async function loadFormForEdit(id: number) {
  editLoadingId.value = id
  try {
    const res = await api.get<ApiResponse<Record<string, unknown>>>(`/forms/definitions/${id}`)
    if (!res.data.ok) {
      Message.error(res.data.message || t('studio.load_failed'))
      return
    }
    const d = res.data.data
    formMeta.id = d.id as number
    formMeta.key = d.key as string
    formMeta.name = d.name as string
    formMeta.description = (d.description as string) || ''
    formMeta.business_sector_id = (d.business_sector_id as number) || undefined
    formMeta.icon = (d.icon as string) || 'general'
    formMeta.status = (d.status as string) || 'draft'
    formMeta.published_at = (d.published_at as string) || null
    schema.value = (d.schema as FormSchema) || DEFAULT_FORM_SCHEMA()
    ensurePrintConfig(schema.value)
    schema.value.title = schema.value.title || formMeta.name
    if (!formMeta.description && schema.value.description) {
      formMeta.description = schema.value.description
    }
    syncFormDescription()
    const wf = d.workflow as Record<string, unknown> | undefined
    if (wf) {
      workflowDefId.value = wf.id as number
      processGraph.value = (wf.process_graph as typeof processGraph.value) || processGraph.value
      const s = wf.settings as Partial<WorkflowSettings>
      if (s) workflowSettings.value = mergeWorkflowSettings(s)
      workflowScope.value = (wf.scope_type as string) || 'global'
    } else {
      workflowDefId.value = undefined
    }
    editing.value = true
    resizeFlowDesigner()
    enterEditingMode()
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('studio.load_failed'))
  } finally {
    editLoadingId.value = null
  }
}

function payload() {
  schema.value.title = formMeta.name || schema.value.title
  syncFormDescription()
  return {
    key: formMeta.key,
    name: formMeta.name,
    description: formMeta.description,
    business_sector_id: formMeta.business_sector_id,
    icon: formMeta.icon,
    schema: schema.value,
    workflow: {
      id: workflowDefId.value,
      key: formMeta.key,
      name: formMeta.name,
      scope_type: workflowScope.value,
      process_graph: processGraph.value,
      settings: { ...workflowSettings.value },
      business_sector_id: formMeta.business_sector_id,
    },
  }
}

async function loadSectors() {
  const res = await api.get('/workflow/business-sectors') as {
    data: ApiResponse<{ id: number; name: string }[]>
  }
  if (res.data.ok) {
    sectorOpts.value = res.data.data.map((s) => ({ label: s.name, value: s.id }))
  }
}

async function saveRowSector(record: Record<string, unknown>, sectorId: number | string | undefined) {
  const formId = record.id as number
  if (!formId) return
  const nextId =
    sectorId === undefined || sectorId === null || sectorId === ''
      ? null
      : Number(sectorId)
  const prev = record.business_sector_id as number | null | undefined
  if (prev === nextId || (prev == null && nextId == null)) return
  sectorSavingId.value = formId
  record.business_sector_id = nextId
  try {
    const res = await api.put<ApiResponse<{ business_sector_id?: number | null; sector_name?: string }>>(
      `/forms/definitions/${formId}`,
      { business_sector_id: nextId },
    )
    if (res.data.ok) {
      record.business_sector_id = res.data.data.business_sector_id ?? null
      record.sector_name = res.data.data.sector_name || ''
      if (formMeta.id === formId) {
        formMeta.business_sector_id = (record.business_sector_id as number | undefined) || undefined
      }
      Message.success(t('studio.sector_saved'))
    } else {
      record.business_sector_id = prev
    }
  } catch (e) {
    record.business_sector_id = prev
    Message.error(e instanceof Error ? e.message : t('studio.sector_save_failed'))
  } finally {
    sectorSavingId.value = null
  }
}

function syncFlowGraph() {
  flowDesignerRef.value?.exportGraph?.()
}

function buildEditorSnapshot() {
  syncFlowGraph()
  schema.value.title = formMeta.name || schema.value.title
  return JSON.stringify(payload())
}

function markEditorSaved() {
  savedSnapshot.value = buildEditorSnapshot()
}

function isEditorDirty() {
  if (!editing.value) return false
  return savedSnapshot.value !== buildEditorSnapshot()
}

const {
  modalVisible: leaveModalVisible,
  saving: leaveSaving,
  cancelLeave,
  discardLeave,
  saveAndLeave,
  requestLeave,
} = useUnsavedLeaveGuard({
  enabled: () => editing.value,
  isDirty: isEditorDirty,
  onSave: async () => saveAll(true),
  markSaved: markEditorSaved,
})

function enterEditingMode() {
  nextTick(() => markEditorSaved())
}

async function saveAll(silent = false): Promise<boolean> {
  if (!formMeta.key || !formMeta.name) {
    Message.warning(t('studio.fill_key_name'))
    return false
  }
  syncFlowGraph()
  saving.value = true
  try {
    if (formMeta.id) {
      await api.put(`/forms/definitions/${formMeta.id}`, payload())
    } else {
      const res = await api.post<ApiResponse<{ id: number }>>('/forms/definitions', payload())
      if (res.data.ok) formMeta.id = res.data.data.id
    }
    markEditorSaved()
    if (!silent) Message.success(t('studio.saved'))
    await load()
    return true
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('studio.save_failed'))
    return false
  } finally {
    saving.value = false
  }
}

async function publishAll() {
  await saveAll()
  if (!formMeta.id) return
  publishing.value = true
  try {
    const res = await api.post<ApiResponse<{ published_at?: string; status?: string }>>(
      `/forms/definitions/${formMeta.id}/publish`,
    )
    if (res.data.ok) {
      if (res.data.data?.published_at) formMeta.published_at = res.data.data.published_at
      formMeta.status = res.data.data?.status || 'published'
    }
    Message.success(t('studio.published_ok'))
    editing.value = false
    savedSnapshot.value = ''
    await load()
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('studio.publish_failed'))
  } finally {
    publishing.value = false
  }
}

async function unpublishAll() {
  if (!formMeta.id) return
  unpublishing.value = true
  try {
    const res = await api.post<ApiResponse<{ status?: string; active_instance_count?: number }>>(
      `/forms/definitions/${formMeta.id}/unpublish`,
    )
    if (res.data.ok) {
      formMeta.status = res.data.data?.status || 'draft'
      Message.success(res.data.message || t('studio.unpublished_ok'))
      await load()
    }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('studio.unpublish_failed'))
  } finally {
    unpublishing.value = false
  }
}

async function unpublishForm(id: number) {
  try {
    const res = await api.post<ApiResponse<{ status?: string }>>(`/forms/definitions/${id}/unpublish`)
    if (res.data.ok) {
      Message.success(res.data.message || t('studio.unpublished_ok'))
      if (formMeta.id === id) formMeta.status = res.data.data?.status || 'draft'
      await load()
    }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('studio.unpublish_failed'))
  }
}

function printPreview() {
  const w = window.open('', '_blank')
  if (!w) return
  w.document.write(`<html><head><title>${t('studio.preview_print')}</title></head><body><p>${t('studio.print_preview_body')}</p></body></html>`)
  Message.info(t('studio.print_preview_hint'))
}

onMounted(() => {
  loadSectors()
  void loadBuiltinTemplates()
  void loadPrintTemplates()
  load()
  const q = new URLSearchParams(window.location.search)
  if (q.get('new')) startCreate()
})
</script>

<style scoped>
.form-studio.is-editing {
  margin: -0.75rem -1.5rem;
  padding: 0.75rem 1.5rem;
  min-height: calc(100dvh - 3.5rem);
  display: flex;
  flex-direction: column;
}

@media (min-width: 640px) {
  .form-studio.is-editing {
    margin: -1.5rem;
    padding: 1.5rem;
  }
}

.studio-editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-height: calc(100dvh - 8rem);
}

.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e5e6eb;
  flex-shrink: 0;
}

.editor-meta-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.editor-meta-table th {
  width: 72px;
  padding: 3px 8px 3px 0;
  text-align: right;
  font-weight: 500;
  font-size: 12px;
  color: var(--text-secondary, #86909c);
  white-space: nowrap;
  vertical-align: middle;
}

.editor-meta-table th.align-top {
  padding-top: 7px;
  vertical-align: top;
}

.editor-meta-table td {
  padding: 3px 12px 3px 0;
  vertical-align: middle;
}

.editor-meta-table tr:last-child td,
.editor-meta-table tr:last-child th {
  padding-bottom: 0;
}

.editor-meta-table .col-grow {
  width: 38%;
}

.editor-meta-table .col-key {
  width: 28%;
}

.editor-meta-table .col-sector {
  max-width: 220px;
}

.icon-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-actions-col {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.form-version-line {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary, #86909c);
  line-height: 1.4;
  text-align: right;
}

.form-version-unpublished {
  color: var(--text-tertiary, #c9cdd4);
}

.form-desc-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-tertiary, #86909c);
  line-height: 1.4;
}

.studio-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-top: 8px;
}

:deep(.studio-tabs) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 仅作用于 Form Studio 顶层 Tab，避免误伤流程节点抽屉内的嵌套 Tab */
:deep(.studio-tabs > .arco-tabs-content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

:deep(.studio-tabs > .arco-tabs-content > .arco-tabs-content-list) {
  height: 100%;
}

:deep(.studio-tabs > .arco-tabs-content > .arco-tabs-content-list > .arco-tabs-content-item > .arco-tabs-pane) {
  height: 100%;
  overflow: hidden;
}

:deep(.studio-tabs > .arco-tabs-content > .arco-tabs-content-list > .arco-tabs-content-item:not(.arco-tabs-content-item-active)) {
  pointer-events: none;
}

.tab-panel {
  height: 100%;
  min-height: min(72vh, 680px);
  overflow: auto;
}

.tab-panel-flow {
  display: flex;
  flex-direction: column;
  overflow: auto;
}

.flow-options {
  flex-shrink: 0;
}

.device-frame {
  background: #fff;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 16px;
  margin: 0 auto;
}

.frame-desktop {
  max-width: 100%;
}

.frame-mobile {
  max-width: 390px;
}

@media print {
  .studio-header,
  .studio-tabs :deep(.arco-tabs-nav) {
    display: none !important;
  }
}

.studio-sector-select {
  width: 100%;
  max-width: 152px;
}
</style>
