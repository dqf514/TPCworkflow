<template>
  <div class="page-shell pb-20 md:pb-8">
    <a-spin :loading="loading" class="w-full">
      <template v-if="inst">
        <div class="flex justify-end mb-4">
          <a-button size="small" type="primary" :loading="printPreviewLoading" @click="openPrintPreview">
            {{ t('print.print_btn') }}
          </a-button>
        </div>

        <div class="rounded-xl border bg-white p-4 sm:p-6 mb-4">
          <InstanceContextHeader
            :title="inst.definition_name || '申请详情'"
            :meta="contextMeta"
          />
          <FormRenderer
            v-if="formSchema"
            :schema="formSchema"
            :model-value="formValues"
            :company-id="inst.company_id"
            :holiday-user-id="inst.initiator_id"
            readonly
            :device="formDevice"
          />
          <a-empty v-else description="无表单数据" />
        </div>

        <WorkflowProgressPanel
          v-if="flowProgress?.process_graph?.nodes?.length || inst.timeline?.length"
          class="mb-4"
          :status="inst.status"
          :status-label="instanceStatusLabel"
          :process-graph="flowProgress?.process_graph"
          :form-schema="formSchema || undefined"
          :form-data="formValues"
          :current-node-ids="flowProgress?.current_node_ids"
          :completed-node-ids="flowProgress?.completed_node_ids"
          :step-started-at="flowProgress?.step_started_at"
          :timeline="inst.timeline"
        />

        <div class="flex justify-end mt-4">
          <a-button size="small" type="primary" :loading="printPreviewLoading" @click="openPrintPreview">
            {{ t('print.print_btn') }}
          </a-button>
        </div>
      </template>
    </a-spin>

    <WorkflowPrintPreviewOverlay ref="printPreviewRef" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { api, type ApiResponse } from '@/api/client'
import InstanceContextHeader from '@/components/instance/InstanceContextHeader.vue'
import FormRenderer from '@/components/form/FormRenderer.vue'
import type { ProcessGraph } from '@/utils/workflowFlowGraph'
import WorkflowPrintPreviewOverlay from '@/components/print/WorkflowPrintPreviewOverlay.vue'
import WorkflowProgressPanel from '@/components/workflow/WorkflowProgressPanel.vue'
import { formatInstanceStatus } from '@/composables/useWorkflowLabels'
import type { FormSchema } from '@/types/form'
import type { PrintTemplateSchema } from '@/types/printTemplate'
import { DEFAULT_FORM_SCHEMA } from '@/types/form'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowBadgesStore } from '@/stores/workflowBadges'
import { useBreakpoint } from '@/composables/useBreakpoint'

interface TimelineRow {
  id: number
  action: string
  comment?: string
  created_at?: string | null
  actor_name?: string
  node_id?: string
  node_name?: string
  signature_path?: string
  signature_data?: string
}

const { t } = useI18n()
const route = useRoute()
const auth = useAuthStore()
const badges = useWorkflowBadgesStore()
const { isMobile } = useBreakpoint()
const formDevice = computed(() => (isMobile.value ? 'mobile' : 'desktop'))
const loading = ref(true)
const printPreviewLoading = ref(false)
const printPreviewRef = ref<InstanceType<typeof WorkflowPrintPreviewOverlay> | null>(null)

const inst = ref<{
  id: number
  status: string
  current_node_label?: string | null
  definition_id?: number
  definition_name?: string
  form_schema?: FormSchema
  variables?: { form?: Record<string, unknown> }
  initiator_name?: string
  company_name?: string
  department_name?: string
  apply_department_path?: string
  started_at?: string | null
  company_id?: number
  display_no?: string
  public_uuid?: string
  timeline: TimelineRow[]
  flow_progress?: {
    process_graph?: ProcessGraph
    current_node_ids?: string[]
    completed_node_ids?: string[]
    step_started_at?: string | null
  }
  print_template_schema?: PrintTemplateSchema
  print_config?: { templateMode?: string; templateCode?: string }
} | null>(null)

const flowProgress = computed(() => inst.value?.flow_progress)

const formSchema = computed(() => {
  const s = inst.value?.form_schema
  if (s && (s as FormSchema).sections) return s as FormSchema
  return null
})

const formValues = computed(() => inst.value?.variables?.form || {})

const instanceStatusLabel = computed(() =>
  formatInstanceStatus(inst.value?.status, t, inst.value?.current_node_label),
)

const contextMeta = computed(() => ({
  id: inst.value?.id || 0,
  displayNo: inst.value?.display_no || String(inst.value?.id || ''),
  status: inst.value?.status || '',
  definitionName: inst.value?.definition_name,
  initiatorName: inst.value?.initiator_name || '',
  companyName: inst.value?.company_name || '',
  departmentName: inst.value?.department_name || '',
  departmentPath: inst.value?.apply_department_path || inst.value?.department_name || '',
  startedAt: inst.value?.started_at,
}))

async function openPrintPreview() {
  if (!formSchema.value || !inst.value) return
  printPreviewLoading.value = true
  try {
    await printPreviewRef.value?.open({
      formSchema: formSchema.value,
      formValues: formValues.value,
      definitionName: inst.value.definition_name,
      companyId: inst.value.company_id,
      excludeInstanceUuid: inst.value.public_uuid || String(route.params.uuid || ''),
      printTemplateSchema: inst.value.print_template_schema || null,
      timeline: inst.value.timeline,
      processGraph: flowProgress.value?.process_graph,
      meta: {
        ...contextMeta.value,
        printedAt: new Date().toISOString(),
        printerName: auth.user?.display_name || auth.user?.username || '',
      },
    })
  } finally {
    printPreviewLoading.value = false
  }
}

onMounted(async () => {
  try {
    const res = await api.get<ApiResponse<Record<string, unknown>>>(
      `/workflow/instances/${route.params.uuid}`,
    )
    if (res.data.ok) {
      inst.value = res.data.data as typeof inst.value
      const fs = res.data.data.form_schema as FormSchema
      if (!fs?.sections) inst.value!.form_schema = DEFAULT_FORM_SCHEMA()
      void badges.refresh(true)
    }
  } catch {
    inst.value = null
  } finally {
    loading.value = false
  }
})
</script>
