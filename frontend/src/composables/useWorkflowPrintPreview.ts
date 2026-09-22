import { computed, nextTick, ref, watch, type Ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import {
  collectPrintAttachments,
  collectSkippedPrintAttachments,
  waitForPrintAssets,
  type PrintAttachmentItem,
} from '@/composables/usePrintAttachments'
import {
  collectRelatedFormRefs,
  loadPrintRelatedBundles,
  type PrintRelatedBundle,
} from '@/composables/usePrintRelatedForms'
import { buildPrintSections, type PrintSectionBlock } from '@/composables/usePrintFormData'
import { loadCompanyDeptOptions } from '@/composables/useOrgDeptOptions'
import type { FormSchema } from '@/types/form'
import type { PrintTemplateSchema } from '@/types/printTemplate'
import type { ProcessGraph } from '@/utils/workflowFlowGraph'
import { printElement } from '@/utils/printDocument'
import { printT } from '@/utils/printI18n'

export interface WorkflowPrintPreviewMeta {
  id?: number
  displayNo?: string
  status?: string
  definitionName?: string
  initiatorName?: string
  companyName?: string
  departmentName?: string
  departmentPath?: string
  startedAt?: string | null
  printedAt?: string
  printerName?: string
}

export interface WorkflowPrintPreviewTimelineRow {
  id: number
  action: string
  comment?: string | null
  created_at?: string | null
  actor_name?: string
  node_id?: string
  node_name?: string
  signature_path?: string
  signature_data?: string
}

export interface WorkflowPrintPreviewInput {
  formSchema: FormSchema
  formValues: Record<string, unknown>
  meta: WorkflowPrintPreviewMeta
  timeline?: WorkflowPrintPreviewTimelineRow[]
  processGraph?: ProcessGraph
  companyId?: number
  definitionName?: string
  printTemplateSchema?: PrintTemplateSchema | null
  excludeInstanceUuid?: string
}

export function useWorkflowPrintPreview(documentRootRef: Ref<HTMLElement | null>) {
  const visible = ref(false)
  const preparing = ref(false)
  const ready = ref(false)
  const assetsReady = ref(false)
  const printSections = ref<PrintSectionBlock[]>([])
  const printMainAttachments = ref<PrintAttachmentItem[]>([])
  const printSkippedAttachments = ref<PrintAttachmentItem[]>([])
  const printRelatedBundles = ref<PrintRelatedBundle[]>([])
  const printTemplateSchema = ref<PrintTemplateSchema | null>(null)
  const userOpts = ref<{ label: string; value: number }[]>([])
  const deptOpts = ref<{ label: string; value: number }[]>([])

  const input = ref<WorkflowPrintPreviewInput | null>(null)

  const useCustomPrintTemplate = computed(() => {
    const pc = input.value?.formSchema?.print
    return pc?.templateMode === 'custom' && !!pc?.templateCode
  })

  let printClickGuard = 0

  async function loadPickerOpts(companyId?: number) {
    try {
      const res = await api.get<
        ApiResponse<{ id: number; display_name: string; username: string }[]>
      >('/workflow/users/options')
      if (res.data.ok) {
        userOpts.value = res.data.data.map((u) => ({
          label: `${u.display_name || u.username} (${u.username})`,
          value: u.id,
        }))
      }
    } catch {
      userOpts.value = []
    }
    if (companyId) {
      try {
        deptOpts.value = await loadCompanyDeptOptions(companyId)
      } catch {
        deptOpts.value = []
      }
    }
  }

  async function prepare(payload: WorkflowPrintPreviewInput) {
    input.value = payload
    ready.value = false
    assetsReady.value = false
    printMainAttachments.value = []
    printSkippedAttachments.value = []
    printRelatedBundles.value = []
    printTemplateSchema.value = payload.printTemplateSchema || null

    await loadPickerOpts(payload.companyId)

    if (useCustomPrintTemplate.value) {
      if (!printTemplateSchema.value && payload.formSchema.print?.templateCode) {
        try {
          const res = await api.get<ApiResponse<{ schema?: PrintTemplateSchema }>>(
            `/print-templates/${payload.formSchema.print.templateCode}`,
          )
          if (res.data.ok && res.data.data?.schema) {
            printTemplateSchema.value = res.data.data.schema
          }
        } catch {
          /* ignore */
        }
      }
      ready.value = !!printTemplateSchema.value
      return
    }

    printSections.value = await buildPrintSections(
      payload.formSchema,
      payload.formValues,
      userOpts.value,
      deptOpts.value,
      { companyId: payload.companyId },
    )
    printMainAttachments.value = collectPrintAttachments(payload.formSchema, payload.formValues)
    printSkippedAttachments.value = collectSkippedPrintAttachments(
      payload.formSchema,
      payload.formValues,
    )

    const refs = collectRelatedFormRefs(
      payload.formSchema,
      payload.formValues,
      payload.excludeInstanceUuid || '',
    )
    printRelatedBundles.value = await loadPrintRelatedBundles(
      refs,
      userOpts.value,
      deptOpts.value,
      {
        printedAt: payload.meta.printedAt || new Date().toISOString(),
        printerName: payload.meta.printerName || '',
      },
    )
    for (const rel of printRelatedBundles.value) {
      printSkippedAttachments.value.push(
        ...collectSkippedPrintAttachments(rel.schema, rel.formValues),
      )
    }
    ready.value = true
  }

  async function waitAssets() {
    assetsReady.value = false
    await nextTick()
    const root = documentRootRef.value?.querySelector('.wf-print-document') as HTMLElement | null
    if (root) {
      try {
        await waitForPrintAssets(root)
      } catch {
        /* ignore */
      }
    }
    assetsReady.value = true
  }

  async function open(payload: WorkflowPrintPreviewInput) {
    preparing.value = true
    try {
      await prepare(payload)
      if (!ready.value) {
        Message.warning(printT('print.prepare_failed'))
        return
      }
      visible.value = true
      await waitAssets()
    } finally {
      preparing.value = false
    }
  }

  function close() {
    visible.value = false
    assetsReady.value = false
  }

  function triggerBrowserPrint() {
    const now = Date.now()
    if (now - printClickGuard < 400) return
    printClickGuard = now

    if (!assetsReady.value) {
      Message.warning(printT('print.assets_loading'))
      return
    }
    const root = documentRootRef.value?.querySelector('.wf-print-document') as HTMLElement | null
    if (!root) {
      Message.error(printT('print.not_ready'))
      return
    }
    const title = input.value?.definitionName || input.value?.meta.definitionName || printT('print.default_title')
    try {
      printElement(root, title)
    } catch {
      Message.error(printT('print.failed'))
    }
  }

  watch(visible, async (v) => {
    if (v) await waitAssets()
    else assetsReady.value = false
  })

  return {
    visible,
    preparing,
    ready,
    assetsReady,
    input,
    printSections,
    printMainAttachments,
    printSkippedAttachments,
    printRelatedBundles,
    printTemplateSchema,
    useCustomPrintTemplate,
    userOpts,
    deptOpts,
    open,
    close,
    triggerBrowserPrint,
  }
}
