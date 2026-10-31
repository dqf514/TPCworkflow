<template>
  <div
    class="page-shell task-detail-page"
    :class="{
      'task-detail-page--mobile': !isDesktop,
      'task-detail-page--above-tab': hasMobileTabBar,
    }"
  >
    <div v-if="task && !loading" class="task-page-header no-print">
      <InstanceContextHeader
        v-if="applyOrg"
        :title="task.instance?.definition_name || '审批'"
        :meta="taskContextMeta"
        class="task-page-header-ctx"
      />
      <div class="task-page-header-side">
        <span class="task-node-chip">任务 #{{ task.id }} · {{ taskNodeLabel }}</span>
        <a-button
          v-if="formSchema"
          size="small"
          type="outline"
          :loading="printPreviewLoading"
          @click="openPrintPreview"
        >
          {{ t('print.preview_title') }}
        </a-button>
      </div>
    </div>

    <a-spin :loading="loading" class="w-full">
      <template v-if="task">

        <a-alert
          v-if="task.is_add_sign_task"
          type="info"
          class="mb-4 rounded-xl"
          :title="addSignBannerTitle"
        />

        <a-card title="表单内容" class="rounded-xl mb-4" v-if="formSchema">
          <FormRenderer
            :schema="formSchema"
            v-model="formEditValues"
            :company-id="task.instance?.company_id"
            :holiday-user-id="task.instance?.initiator_id"
            :readonly="formReadonly"
            :field-permissions="fieldPermissions"
            :field-node-required="fieldNodeRequired"
            :field-must-modify="fieldMustModify"
            :device="formDevice"
          />
        </a-card>

        <a-card v-if="canActOnTask" :title="t('workflow.comment')" class="rounded-xl mb-4">
          <p class="text-xs text-gray-500 mb-2">{{ t('workflow.comment_quick_hint') }}</p>
          <div class="flex flex-wrap gap-2 mb-3">
            <a-tag
              v-for="phrase in quickComments"
              :key="phrase"
              class="cursor-pointer select-none"
              @click="applyQuickComment(phrase)"
            >
              {{ phrase }}
            </a-tag>
          </div>
          <a-textarea v-model="comment" :auto-size="{ minRows: 3 }" :placeholder="t('workflow.comment_ph')" />
          <div v-if="task.settings?.require_handwritten_sign" class="mt-4">
            <div class="text-sm mb-2">{{ t('workflow.signature') }}</div>
            <HandSignPad v-model="signatureData" />
          </div>
        </a-card>

        <a-card v-if="timeline.length" title="审批记录" class="rounded-xl mb-4">
          <ApprovalTimeline :items="timeline" :show-actor="false" />
        </a-card>

        <a-modal v-model:visible="showTransfer" title="转交" @ok="doTransfer">
          <a-select v-model="transferUserId" :options="userOpts" placeholder="选择用户" />
        </a-modal>

        <a-modal
          v-model:visible="showCommentModal"
          :title="commentModalTitle"
          :ok-loading="acting"
          @ok="confirmCommentModal"
          @cancel="closeCommentModal"
        >
          <p class="text-sm text-gray-500 mb-3">{{ t('workflow.comment_modal_hint') }}</p>
          <div class="flex flex-wrap gap-2 mb-3">
            <a-tag
              v-for="phrase in modalQuickComments"
              :key="phrase"
              class="cursor-pointer select-none"
              @click="applyModalQuickComment(phrase)"
            >
              {{ phrase }}
            </a-tag>
          </div>
          <a-textarea
            v-model="modalComment"
            :auto-size="{ minRows: 3 }"
            :placeholder="t('workflow.comment_ph')"
          />
        </a-modal>

        <a-modal
          v-model:visible="showAddSignModal"
          :title="t('workflow.add_sign_title')"
          :ok-loading="acting"
          @ok="submitAddSign"
        >
          <p class="text-sm text-gray-500 mb-3">{{ t('workflow.add_sign_hint') }}</p>
          <a-radio-group v-model="addSignMode" direction="vertical" class="mb-4">
            <a-radio value="before">{{ t('workflow.add_sign_mode_before') }}</a-radio>
            <a-radio value="after">{{ t('workflow.add_sign_mode_after') }}</a-radio>
          </a-radio-group>
          <a-form-item :label="t('workflow.add_sign_users')">
            <a-select
              v-model="addSignUserIds"
              :options="addSignUserOpts"
              multiple
              allow-search
              :placeholder="t('workflow.add_sign_users_ph')"
            />
          </a-form-item>
        </a-modal>
      </template>
    </a-spin>

    <Teleport to="body" :disabled="isDesktop">
      <div
        v-if="task"
        class="task-footer-actions safe-bottom"
        :class="{
          'task-footer-actions--desktop': isDesktop,
          'task-footer-actions--mobile': !isDesktop,
          'task-footer-actions--above-tab': hasMobileTabBar,
        }"
      >
        <div class="task-footer-actions-inner">
          <template v-if="canActOnTask">
            <a-button
              type="primary"
              class="task-action-btn"
              :loading="acting"
              @click="onActionClick('approve')"
            >
              {{ isHandlerNode ? t('workflow.handle_done') : t('workflow.approve') }}
            </a-button>
            <a-button
              v-if="!isHandlerNode"
              status="danger"
              class="task-action-btn"
              :loading="acting"
              @click="onActionClick('reject')"
            >
              {{ t('workflow.reject') }}
            </a-button>
            <a-button
              v-if="showAddSignBtn"
              class="task-action-btn"
              @click="openAddSign"
            >
              {{ t('workflow.add_sign') }}
            </a-button>
            <a-button
              v-if="task.settings?.allow_transfer"
              class="task-action-btn"
              @click="showTransfer = true"
            >
              {{ t('workflow.transfer') }}
            </a-button>
          </template>
          <a-button
            v-else
            type="primary"
            class="task-action-btn task-action-btn--close"
            @click="closeTaskPage"
          >
            {{ t('workflow.task_already_handled_close') }}
          </a-button>
        </div>
      </div>
    </Teleport>

    <WorkflowPrintPreviewOverlay ref="printPreviewRef" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import HandSignPad from '@/components/HandSignPad.vue'
import InstanceContextHeader from '@/components/instance/InstanceContextHeader.vue'
import FormRenderer from '@/components/form/FormRenderer.vue'
import ApprovalTimeline from '@/components/workflow/ApprovalTimeline.vue'
import WorkflowPrintPreviewOverlay from '@/components/print/WorkflowPrintPreviewOverlay.vue'
import type { FormSchema } from '@/types/form'
import type { PrintTemplateSchema } from '@/types/printTemplate'
import type { ProcessGraph } from '@/utils/workflowFlowGraph'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowBadgesStore } from '@/stores/workflowBadges'
import { useEmbedDesktop } from '@/composables/useEmbedDesktop'
import { validateNodeFieldRequirements } from '@/utils/nodeFieldRequirements'

interface TaskDetail {
  id: number
  status?: string
  node_id: string
  node_name?: string
  node_type?: string
  settings?: Record<string, boolean>
  is_add_sign_task?: boolean
  add_sign_mode?: string
  add_sign_requested_by_name?: string
  form_schema?: FormSchema
  print_template_schema?: PrintTemplateSchema
  variables?: { form?: Record<string, unknown> }
  node_config?: {
    field_permissions?: Record<string, 'hidden' | 'read' | 'edit'>
    field_node_required?: Record<string, boolean>
    field_must_modify?: Record<string, boolean>
  }
    instance?: {
    definition_name?: string
    id: number
    public_uuid?: string
    company_id?: number
    display_no?: string
    status?: string
    started_at?: string | null
    initiator_name?: string
    company_name?: string
    department_name?: string
    apply_department_path?: string
  }
  apply_org?: {
    initiator_name?: string
    company_name?: string
    department_name?: string
    apply_department_path?: string
  }
  initiator_name?: string
}

interface TimelineItem {
  id: number
  action: string
  comment?: string | null
  created_at?: string | null
  actor_name?: string
  signature_path?: string
  signature_data?: string
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const badges = useWorkflowBadgesStore()
const { isEmbedDesktop, notifyClient } = useEmbedDesktop()
const { isMobile, isDesktop, width } = useBreakpoint()
const hasMobileTabBar = computed(() => width.value < 768)
const formDevice = computed(() => (isMobile.value ? 'mobile' : 'desktop'))
const { t } = useI18n()
const task = ref<TaskDetail | null>(null)
const timeline = ref<TimelineItem[]>([])
const loading = ref(true)
const acting = ref(false)
const QUICK_COMMENT_KEYS = [
  'workflow.quick_comment_agree',
  'workflow.quick_comment_ok_read',
  'workflow.quick_comment_agree_draft',
  'workflow.quick_comment_verify',
  'workflow.quick_comment_reject',
  'workflow.quick_comment_supplement',
] as const

const AGREE_QUICK_COMMENT_KEYS = [
  'workflow.quick_comment_agree',
  'workflow.quick_comment_ok_read',
  'workflow.quick_comment_agree_draft',
  'workflow.quick_comment_verify',
] as const

const REJECT_QUICK_COMMENT_KEYS = [
  'workflow.quick_comment_reject',
  'workflow.quick_comment_supplement',
] as const

type TaskAction = 'approve' | 'reject'

const comment = ref('')
const quickComments = computed(() => QUICK_COMMENT_KEYS.map((k) => t(k)))

const showCommentModal = ref(false)
const pendingAction = ref<TaskAction | null>(null)
const modalComment = ref('')

const commentModalTitle = computed(() => {
  if (pendingAction.value === 'reject') {
    return t('workflow.comment_modal_reject_title')
  }
  if (isHandlerNode.value) {
    return t('workflow.comment_modal_handle_title')
  }
  return t('workflow.comment_modal_approve_title')
})

const modalQuickComments = computed(() => {
  const keys =
    pendingAction.value === 'reject' ? REJECT_QUICK_COMMENT_KEYS : AGREE_QUICK_COMMENT_KEYS
  return keys.map((k) => t(k))
})

function applyQuickComment(phrase: string) {
  comment.value = phrase
}

function hasCommentText() {
  return !!comment.value.trim()
}

function needsCommentForAction(action: TaskAction) {
  const settings = task.value?.settings
  if (!settings) return false
  if (
    action === 'approve' &&
    task.value?.node_type === 'handler' &&
    settings.require_handler_comment
  ) {
    return true
  }
  return !!settings.require_comment
}

function closeCommentModal() {
  showCommentModal.value = false
  pendingAction.value = null
  modalComment.value = ''
}

function onActionClick(action: TaskAction) {
  if (needsCommentForAction(action) && !hasCommentText()) {
    pendingAction.value = action
    modalComment.value = ''
    showCommentModal.value = true
    return
  }
  void complete(action)
}

function applyModalQuickComment(phrase: string) {
  if (!pendingAction.value) return
  comment.value = phrase
  const action = pendingAction.value
  closeCommentModal()
  void complete(action)
}

async function confirmCommentModal() {
  if (!pendingAction.value) return false
  if (!modalComment.value.trim()) {
    Message.warning(t('workflow.comment_required'))
    return false
  }
  comment.value = modalComment.value.trim()
  const action = pendingAction.value
  closeCommentModal()
  await complete(action)
}
const signatureData = ref('')
const showTransfer = ref(false)
const transferUserId = ref<number>()
const userOpts = ref<{ label: string; value: number }[]>([])
const formEditValues = reactive<Record<string, unknown>>({})
const originalFormSnapshot = ref<Record<string, unknown>>({})
const printPreviewRef = ref<InstanceType<typeof WorkflowPrintPreviewOverlay> | null>(null)
const printPreviewLoading = ref(false)
const instFlowProgress = ref<{
  process_graph?: ProcessGraph
  current_node_ids?: string[]
  completed_node_ids?: string[]
  step_started_at?: string | null
} | null>(null)
const instPrintTemplateSchema = ref<PrintTemplateSchema | null>(null)

const showAddSignModal = ref(false)
const addSignMode = ref<'before' | 'after'>('before')
const addSignUserIds = ref<number[]>([])

const canActOnTask = computed(() => task.value?.status === 'pending')

const isHandlerNode = computed(() => task.value?.node_type === 'handler')

const taskNodeLabel = computed(() => task.value?.node_name || task.value?.node_id || '')

const formSchema = computed(() => task.value?.form_schema || null)
const fieldPermissions = computed(() => task.value?.node_config?.field_permissions)
const fieldNodeRequired = computed(() => task.value?.node_config?.field_node_required)
const fieldMustModify = computed(() => task.value?.node_config?.field_must_modify)
const hasEditableFields = computed(() =>
  Object.values(fieldPermissions.value || {}).some((p) => p === 'edit'),
)
const hasNodeFieldRules = computed(() => {
  const cfg = task.value?.node_config
  if (!cfg) return false
  const perms = cfg.field_permissions || {}
  const maps = [cfg.field_node_required || {}, cfg.field_must_modify || {}]
  return maps.some((m) => Object.entries(m).some(([k, v]) => v && perms[k] === 'edit'))
})
const formReadonly = computed(() => !hasEditableFields.value)

const applyOrg = computed(() => task.value?.apply_org || task.value?.instance)

const showAddSignBtn = computed(
  () =>
    !!task.value?.settings?.allow_add_sign &&
    !task.value?.is_add_sign_task &&
    (task.value?.node_type === 'approver' || task.value?.node_type === 'handler' || !task.value?.node_type),
)
const addSignUserOpts = computed(() =>
  userOpts.value.filter((o) => o.value !== auth.user?.id),
)

const addSignBannerTitle = computed(() => {
  if (!task.value?.is_add_sign_task) return ''
  const mode =
    task.value.add_sign_mode === 'after'
      ? t('workflow.add_sign_mode_label_after')
      : t('workflow.add_sign_mode_label_before')
  const name = task.value.add_sign_requested_by_name || '—'
  return `${mode} · ${t('workflow.add_sign_banner', { name })}`
})

const taskContextMeta = computed(() => {
  const org = applyOrg.value
  const inst = task.value?.instance
  return {
    id: inst?.id || 0,
    displayNo: inst?.display_no || String(inst?.id || ''),
    status: inst?.status || '',
    initiatorName: org?.initiator_name || task.value?.initiator_name || '',
    companyName: org?.company_name || '',
    departmentName: org?.department_name || '',
    departmentPath: org?.apply_department_path || org?.department_name || '',
    startedAt: inst?.started_at,
  }
})

function openAddSign() {
  addSignMode.value = 'before'
  addSignUserIds.value = []
  showAddSignModal.value = true
}

function closeTaskPage() {
  if (isEmbedDesktop.value) {
    notifyClient({ type: 'navigate', path: '/tasks' })
    return
  }
  void router.push({ name: 'dashboard' })
  if (window.opener) {
    window.close()
  }
}

async function openPrintPreview() {
  if (!formSchema.value || !task.value) return
  printPreviewLoading.value = true
  try {
    const org = applyOrg.value
    const inst = task.value.instance
    await printPreviewRef.value?.open({
    formSchema: formSchema.value,
    formValues: { ...formEditValues },
    definitionName: inst?.definition_name || task.value.instance?.definition_name,
    companyId: inst?.company_id,
    excludeInstanceUuid: inst?.public_uuid || '',
    printTemplateSchema: instPrintTemplateSchema.value || task.value.print_template_schema || null,
    timeline: timeline.value,
    processGraph: instFlowProgress.value?.process_graph,
    meta: {
      id: inst?.id || 0,
      displayNo: inst?.display_no || String(inst?.id || ''),
      status: inst?.status || '',
      definitionName: inst?.definition_name,
      initiatorName: org?.initiator_name || task.value.initiator_name || '',
      companyName: org?.company_name || '',
      departmentName: org?.department_name || '',
      departmentPath: org?.apply_department_path || org?.department_name || '',
      startedAt: inst?.started_at,
      printedAt: new Date().toISOString(),
      printerName: auth.user?.display_name || auth.user?.username || '',
    },
    })
  } finally {
    printPreviewLoading.value = false
  }
}

async function load() {
  const id = route.params.id
  loading.value = true
  try {
    const res = await api.get<ApiResponse<TaskDetail>>(`/workflow/tasks/${id}`)
    if (res.data.ok) {
      task.value = res.data.data
      comment.value = ''
      const initialForm = res.data.data.variables?.form || {}
      Object.assign(formEditValues, initialForm)
      originalFormSnapshot.value = JSON.parse(JSON.stringify(initialForm))
      const instUuid = res.data.data.instance?.public_uuid
      if (instUuid) {
        const inst = await api.get<
          ApiResponse<{
            timeline: TimelineItem[]
            flow_progress?: typeof instFlowProgress.value
            print_template_schema?: PrintTemplateSchema
          }>
        >(`/workflow/instances/${instUuid}`)
        if (inst.data.ok) {
          timeline.value = inst.data.data.timeline
          instFlowProgress.value = inst.data.data.flow_progress || null
          instPrintTemplateSchema.value = inst.data.data.print_template_schema || null
        }
      }
    }
  } finally {
    loading.value = false
  }
}

async function buildActionMeta(): Promise<Record<string, unknown>> {
  const action_meta: Record<string, unknown> = {}
  if (signatureData.value) {
    const up = await api.post<ApiResponse<{ signature_path: string }>>('/uploads/signature', {
      signature_data: signatureData.value,
    })
    if (up.data.ok) action_meta.signature_path = up.data.data.signature_path
  }
  return action_meta
}

function afterTaskHandled() {
  void badges.refresh(true)
  if (isEmbedDesktop.value && task.value) {
    notifyClient({ type: 'task_completed', taskId: task.value.id })
    return
  }
  router.push({ name: 'tasks' })
}

async function complete(action: string, extraMeta?: Record<string, unknown>) {
  if (!task.value) return
  if (action === 'approve' && formSchema.value && task.value.node_config) {
    const nodeErrs = validateNodeFieldRequirements(
      formSchema.value,
      formEditValues,
      task.value.node_config,
      originalFormSnapshot.value,
    )
    if (nodeErrs.length) {
      Message.warning(nodeErrs.join('；'))
      return
    }
  }
  acting.value = true
  try {
    const action_meta = await buildActionMeta()
    Object.assign(action_meta, extraMeta || {})
    const body: Record<string, unknown> = {
      action,
      comment: comment.value,
      action_meta,
    }
    if ((hasEditableFields.value || hasNodeFieldRules.value) && action === 'approve') {
      body.form = { ...formEditValues }
    }
    await api.post(`/workflow/tasks/${task.value.id}/complete`, body)
    Message.success(t('common.success'))
    afterTaskHandled()
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '失败')
  } finally {
    acting.value = false
  }
}

async function submitAddSign() {
  if (!task.value || !addSignUserIds.value.length) {
    Message.warning(t('workflow.add_sign_users_ph'))
    return
  }
  if (addSignMode.value === 'before') {
    acting.value = true
    try {
      await api.post(`/workflow/tasks/${task.value.id}/complete`, {
        action: 'add_sign',
        comment: comment.value,
        action_meta: {
          mode: 'before',
          target_user_ids: addSignUserIds.value,
        },
      })
      Message.success(t('common.success'))
      showAddSignModal.value = false
      afterTaskHandled()
    } catch (e) {
      Message.error(e instanceof Error ? e.message : '失败')
    } finally {
      acting.value = false
    }
    return
  }
  showAddSignModal.value = false
  await complete('approve', {
    add_sign_mode: 'after',
    target_user_ids: addSignUserIds.value,
  })
}

async function doTransfer() {
  if (!task.value || !transferUserId.value) return
  await api.post(`/workflow/tasks/${task.value.id}/complete`, {
    action: 'transfer',
    action_meta: { target_user_id: transferUserId.value },
  })
  Message.success(t('common.success'))
  afterTaskHandled()
}

onMounted(async () => {
  await load()
  const u = await api.get<ApiResponse<{ id: number; display_name: string }[]>>('/workflow/users/options')
  if (u.data.ok) userOpts.value = u.data.data.map((x) => ({ label: x.display_name, value: x.id }))
})
</script>

<style scoped>
.task-detail-page--mobile {
  padding-bottom: var(--task-footer-height);
}

.task-detail-page--mobile.task-detail-page--above-tab {
  padding-bottom: calc(var(--task-footer-height) + var(--mobile-tab-bar-height));
}

.task-page-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px 16px;
  margin-bottom: 16px;
}

.task-page-header-ctx {
  flex: 1 1 420px;
  min-width: 0;
  margin-bottom: 0;
}

.task-page-header-side {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.task-node-chip {
  padding: 2px 9px;
  border-radius: var(--radius-pill);
  background: var(--surface-muted);
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.task-detail-page :deep(.arco-card) {
  border: 1px solid var(--border);
  box-shadow: var(--shadow-xs);
}

.task-detail-page :deep(.arco-card-header) {
  padding: 13px 18px;
  border-bottom: 1px solid var(--border);
}

.task-detail-page :deep(.arco-card-header-title) {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}

.task-detail-page :deep(.arco-card-body) {
  padding: 16px 18px;
}

@media (max-width: 767px) {
  .task-page-header-ctx {
    flex-basis: 100%;
  }
}

.task-footer-actions--mobile {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 55;
  padding: 12px;
  background: var(--color-bg-1, #fff);
  border-top: 1px solid var(--border, #e5e6eb);
  box-shadow: 0 -4px 16px rgba(16, 24, 40, 0.06);
}

.task-footer-actions--mobile.task-footer-actions--above-tab {
  bottom: var(--mobile-tab-bar-height);
}

.task-footer-actions-inner {
  display: flex;
  flex-wrap: nowrap;
  align-items: stretch;
  gap: 8px;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
}

.task-action-btn {
  flex: 1 1 0;
  min-width: 0;
  min-height: 44px;
  padding-left: 8px;
  padding-right: 8px;
}

.task-footer-actions--desktop {
  position: static;
  z-index: auto;
  padding: 16px 0 0;
  margin-top: 24px;
  background: transparent;
  border-top: 1px solid var(--border, #e5e6eb);
  box-shadow: none;
}

.task-footer-actions--desktop .task-footer-actions-inner {
  width: auto;
  margin-left: auto;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.task-footer-actions--desktop .task-action-btn {
  flex: 0 0 auto;
  width: auto;
  min-height: auto;
  padding-left: 15px;
  padding-right: 15px;
}

.task-action-btn--close {
  flex: 1 1 auto;
}

.task-footer-actions--desktop .task-action-btn--close {
  min-width: 160px;
}
</style>
