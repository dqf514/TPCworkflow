<template>
  <div class="workflow-settings-panel">
    <a-form layout="vertical" class="w-full">
      <a-card :title="t('wfSettings.apply_visibility')" class="mb-4 rounded-lg">
        <p class="text-sm text-gray-500 mb-3">{{ t('wfSettings.apply_visibility_hint') }}</p>
        <a-radio-group v-model="model.apply_visibility_mode" direction="vertical">
          <a-radio value="all">{{ t('wfSettings.apply_all') }}</a-radio>
          <a-radio value="restricted">{{ t('wfSettings.apply_restricted') }}</a-radio>
        </a-radio-group>
        <template v-if="model.apply_visibility_mode === 'restricted'">
          <a-alert
            v-if="!model.visible_department_ids.length && !model.visible_user_ids.length"
            type="warning"
            class="mt-3"
          >
            {{ t('wfSettings.apply_empty_warn') }}
          </a-alert>
          <a-form-item :label="t('wfSettings.visible_departments')" class="mt-4 !mb-2">
            <a-select
              v-model="model.visible_department_ids"
              :options="deptOpts"
              multiple
              allow-search
              :max-tag-count="4"
              :placeholder="t('wfSettings.visible_departments_ph')"
              class="w-full max-w-2xl"
            />
          </a-form-item>
          <a-form-item :label="t('wfSettings.visible_users')" class="!mb-0">
            <a-select
              v-model="model.visible_user_ids"
              :options="userOpts"
              multiple
              allow-search
              :max-tag-count="4"
              :placeholder="t('wfSettings.visible_users_ph')"
              class="w-full max-w-2xl"
            />
          </a-form-item>
          <p class="text-xs text-gray-400 mt-2">{{ t('wfSettings.apply_union_hint') }}</p>
        </template>
      </a-card>

      <a-card :title="t('wfSettings.comment_sign')" class="mb-4 rounded-lg">
        <a-checkbox v-model="model.require_comment">{{ t('wfSettings.require_comment') }}</a-checkbox>
        <a-checkbox v-model="model.require_handler_comment" class="mt-2 block">
          {{ t('wfSettings.require_handle') }}
        </a-checkbox>
        <a-checkbox v-model="model.require_handwritten_sign" class="mt-2 block">
          {{ t('wfSettings.require_sign') }}
        </a-checkbox>
      </a-card>

      <a-card :title="t('wfSettings.auto_approve')" class="mb-4 rounded-lg">
        <p class="text-sm text-gray-500 mb-3">{{ t('wfSettings.auto_hint') }}</p>
        <a-radio-group v-model="model.duplicate_approver_mode" direction="vertical">
          <a-radio value="first_only">{{ t('wfSettings.auto_first') }}</a-radio>
          <a-radio value="consecutive_only">{{ t('wfSettings.auto_consecutive') }}</a-radio>
          <a-radio value="every_node">{{ t('wfSettings.auto_every') }}</a-radio>
        </a-radio-group>
      </a-card>

      <a-card :title="t('wfSettings.approver_exception')" class="mb-4 rounded-lg">
        <a-form-item :label="t('wfSettings.empty_member')">
          <a-radio-group v-model="model.approver_empty_action" direction="vertical">
            <a-radio value="auto_approve">{{ t('wfSettings.auto_approve_opt') }}</a-radio>
            <a-radio value="transfer">{{ t('wfSettings.transfer') }}</a-radio>
            <a-radio value="admin_handover">{{ t('wfSettings.admin_handover') }}</a-radio>
          </a-radio-group>
          <a-select
            v-if="model.approver_empty_action === 'transfer'"
            v-model="model.approver_empty_transfer_user_id"
            :options="userOpts"
            :placeholder="t('wfSettings.pick_member')"
            allow-search
            class="mt-2 w-full max-w-md"
          />
        </a-form-item>
        <a-form-item :label="t('wfSettings.left_member')">
          <a-radio-group v-model="model.approver_resigned_action" direction="vertical">
            <a-radio value="auto_transfer">{{ t('wfSettings.auto_transfer') }}</a-radio>
            <a-radio value="admin_handover">{{ t('wfSettings.admin_manual') }}</a-radio>
          </a-radio-group>
          <a-select
            v-if="model.approver_resigned_action === 'auto_transfer'"
            v-model="model.approver_resigned_transfer_user_id"
            :options="userOpts"
            :placeholder="t('wfSettings.pick_member')"
            allow-search
            class="mt-2 w-full max-w-md"
          />
        </a-form-item>
      </a-card>

      <a-card :title="t('wfSettings.handler_exception')" class="mb-4 rounded-lg">
        <a-form-item :label="t('wfSettings.empty_member')">
          <a-radio-group v-model="model.handler_empty_action" direction="vertical">
            <a-radio value="auto_approve">{{ t('wfSettings.auto_approve_opt') }}</a-radio>
            <a-radio value="transfer">{{ t('wfSettings.transfer') }}</a-radio>
            <a-radio value="admin_handover">{{ t('wfSettings.admin_handover') }}</a-radio>
          </a-radio-group>
          <a-select
            v-if="model.handler_empty_action === 'transfer'"
            v-model="model.handler_empty_transfer_user_id"
            :options="userOpts"
            :placeholder="t('wfSettings.pick_member')"
            allow-search
            class="mt-2 w-full max-w-md"
          />
        </a-form-item>
        <a-form-item :label="t('wfSettings.left_member')">
          <a-radio-group v-model="model.handler_resigned_action" direction="vertical">
            <a-radio value="auto_transfer">{{ t('wfSettings.auto_transfer') }}</a-radio>
            <a-radio value="admin_handover">{{ t('wfSettings.admin_manual') }}</a-radio>
          </a-radio-group>
          <a-select
            v-if="model.handler_resigned_action === 'auto_transfer'"
            v-model="model.handler_resigned_transfer_user_id"
            :options="userOpts"
            :placeholder="t('wfSettings.pick_member')"
            allow-search
            class="mt-2 w-full max-w-md"
          />
        </a-form-item>
      </a-card>

      <a-card
        v-if="showDocumentDelivery"
        title="单据投递（审批通过后发邮件）"
        class="mb-4 rounded-lg"
      >
        <p class="text-sm text-gray-500 mb-3">
          仅当打印模板类型为「专用模板」时可用。使用系统 SMTP 发送，邮件语言由表单字段控制（默认英文）。
        </p>
        <a-checkbox v-model="model.document_delivery.enabled">审批通过后自动发送邮件</a-checkbox>
        <template v-if="model.document_delivery.enabled">
          <a-form-item label="打印模板编码" class="mt-3">
            <a-select
              v-model="model.document_delivery.template_code"
              :options="printTemplateOpts"
              allow-search
              placeholder="选择与打印 Tab 一致的模板"
            />
          </a-form-item>
          <a-form-item label="收件人邮箱字段">
            <a-select v-model="model.document_delivery.recipient_email_field" :options="fieldOpts" allow-search />
          </a-form-item>
          <a-form-item label="收件人姓名字段">
            <a-select v-model="model.document_delivery.recipient_name_field" :options="fieldOpts" allow-search />
          </a-form-item>
          <a-form-item label="邮件语言字段">
            <a-select v-model="model.document_delivery.email_language_field" :options="fieldOpts" allow-search />
          </a-form-item>
          <a-form-item label="抄送邮箱字段">
            <a-select v-model="model.document_delivery.cc_email_field" :options="fieldOpts" allow-search />
          </a-form-item>
        </template>
      </a-card>

      <a-card :title="t('wfSettings.permission_other')" class="mb-4 rounded-lg">
        <a-checkbox v-model="model.allow_transfer">{{ t('wfSettings.allow_transfer') }}</a-checkbox>
        <a-checkbox v-model="model.allow_revoke_after_approved" class="mt-2 block">
          {{ t('wfSettings.allow_revoke') }}
        </a-checkbox>
        <a-checkbox v-model="model.allow_add_sign" class="mt-2 block">
          {{ t('wfSettings.allow_add_sign') }}
        </a-checkbox>
        <a-divider />
        <a-form-item :label="t('wfSettings.scope')">
          <a-select v-model="scopeType" class="w-48">
            <a-option value="global">{{ t('wfSettings.scope_global') }}</a-option>
            <a-option value="company">{{ t('wfSettings.scope_company') }}</a-option>
          </a-select>
          <p class="text-xs text-gray-400 mt-1">{{ t('wfSettings.scope_company_hint') }}</p>
        </a-form-item>
      </a-card>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api, type ApiResponse } from '@/api/client'
import { loadCompanyDeptOptions } from '@/composables/useOrgDeptOptions'
import type { FormSchema } from '@/types/form'
import type { PrintTemplateRow } from '@/types/printTemplate'
import {
  DEFAULT_DOCUMENT_DELIVERY,
  DEFAULT_WORKFLOW_SETTINGS,
  mergeWorkflowSettings,
  type WorkflowSettings,
} from '@/types/workflowSettings'

const props = defineProps<{
  formSchema?: FormSchema | null
}>()

const { t } = useI18n()
const model = defineModel<WorkflowSettings>({ required: true })
const scopeType = defineModel<string>('scopeType', { default: 'global' })

const userOpts = ref<{ label: string; value: number }[]>([])
const deptOpts = ref<{ label: string; value: number }[]>([])
const printTemplateOpts = ref<{ label: string; value: string }[]>([])

const showDocumentDelivery = computed(
  () => props.formSchema?.print?.templateMode === 'custom' && !!props.formSchema?.print?.templateCode,
)

const fieldOpts = computed(() => {
  const out: { label: string; value: string }[] = []
  for (const sec of props.formSchema?.sections || []) {
    for (const f of sec.fields || []) {
      if (f.key && !['divider', 'text_block', 'section_title', 'leave_calendar'].includes(f.type)) {
        out.push({ label: `${f.label} (${f.key})`, value: f.key })
      }
    }
  }
  return out
})

function normalizeWorkflowSettings(v?: WorkflowSettings | null): WorkflowSettings {
  const merged = mergeWorkflowSettings(v || undefined)
  if (!merged.document_delivery) merged.document_delivery = DEFAULT_DOCUMENT_DELIVERY()
  return merged
}

async function loadDeptOptions() {
  const primary = await api.get<ApiResponse<{ id: number }>>('/org/primary')
  if (!primary.data.ok || !primary.data.data?.id) {
    deptOpts.value = []
    return
  }
  deptOpts.value = await loadCompanyDeptOptions(primary.data.data.id)
}

onMounted(async () => {
  model.value = normalizeWorkflowSettings(model.value)
  const users = await api.get<ApiResponse<{ id: number; display_name: string; username: string }[]>>(
    '/workflow/users/options',
  )
  if (users.data.ok) {
    userOpts.value = users.data.data.map((u) => ({
      label: u.display_name || u.username,
      value: u.id,
    }))
  }
  try {
    const tpl = await api.get<ApiResponse<PrintTemplateRow[]>>('/print-templates')
    if (tpl.data.ok) {
      printTemplateOpts.value = tpl.data.data.map((r) => ({ label: `${r.name} (${r.code})`, value: r.code }))
    }
  } catch {
    printTemplateOpts.value = []
  }
  await loadDeptOptions()
})

watch(
  () => props.formSchema?.print?.templateCode,
  (code) => {
    if (code && model.value.document_delivery && !model.value.document_delivery.template_code) {
      model.value.document_delivery.template_code = code
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.workflow-settings-panel {
  padding: 8px 4px;
  overflow: auto;
  max-height: calc(100vh - 200px);
}
</style>
