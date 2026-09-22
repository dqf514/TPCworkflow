import { api, type ApiResponse } from '@/api/client'
import type { PrintSheetMeta, PrintTimelineItem } from '@/components/print/WorkflowPrintSheet.vue'
import { collectPrintAttachments, type PrintAttachmentItem } from '@/composables/usePrintAttachments'
import { buildPrintSections, type PrintSectionBlock } from '@/composables/usePrintFormData'
import { buildLinkageContext, shouldDisplayField, shouldDisplaySection } from '@/composables/useFieldLinkage'
import type { FormSchema, RelatedFormValue } from '@/types/form'
import type { ProcessGraph } from '@/utils/workflowFlowGraph'
import { printT } from '@/utils/printI18n'

export interface RelatedFormRef {
  publicUuid: string
  fieldLabel: string
  title: string
}

export interface PrintRelatedBundle {
  key: string
  linkLabel: string
  schema: FormSchema
  formValues: Record<string, unknown>
  meta: PrintSheetMeta
  timeline: PrintTimelineItem[]
  sections: PrintSectionBlock[]
  attachments: PrintAttachmentItem[]
  processGraph?: ProcessGraph | null
}

function isRelatedFormValue(v: unknown): v is RelatedFormValue {
  if (!v || typeof v !== 'object') return false
  const o = v as RelatedFormValue
  return Boolean(o.instance_id || o.public_uuid)
}

/** 从表单数据中收集可打印的关联申请单（去重，不含本单） */
export function collectRelatedFormRefs(
  schema: FormSchema,
  model: Record<string, unknown>,
  excludeUuid?: string,
): RelatedFormRef[] {
  const seen = new Set<string>()
  const out: RelatedFormRef[] = []
  const linkageCtx = buildLinkageContext(schema)
  const exclude = (excludeUuid || '').trim()

  for (const sec of schema.sections || []) {
    if (!shouldDisplaySection(sec, schema, model, linkageCtx)) continue
    for (const field of sec.fields || []) {
      if (field.type !== 'related_form' || field.printable === false || field.visible === false) continue
      if (!shouldDisplayField(field, schema, model, linkageCtx)) continue
      if (!field.key) continue

      const raw = model[field.key]
      const picked: RelatedFormValue[] = []
      if (Array.isArray(raw)) {
        for (const item of raw) {
          if (isRelatedFormValue(item)) picked.push(item)
        }
      } else if (isRelatedFormValue(raw)) {
        picked.push(raw)
      }

      for (const item of picked) {
        const uuid = String(item.public_uuid || '').trim()
        if (!uuid || seen.has(uuid) || (exclude && uuid === exclude)) continue
        seen.add(uuid)
        out.push({
          publicUuid: uuid,
          fieldLabel: field.label || printT('print.related_request'),
          title: item.title || '',
        })
      }
    }
  }

  return out
}

/** 拉取关联申请单详情并构建打印数据 */
export async function loadPrintRelatedBundles(
  refs: RelatedFormRef[],
  userOpts: { label: string; value: number }[],
  deptOpts: { label: string; value: number }[],
  printContext: { printedAt: string; printerName: string },
): Promise<PrintRelatedBundle[]> {
  const bundles: PrintRelatedBundle[] = []

  for (const ref of refs) {
    try {
      const res = await api.get<ApiResponse<Record<string, unknown>>>(
        `/workflow/instances/${ref.publicUuid}`,
      )
      if (!res.data.ok) continue

      const data = res.data.data
      const schema = data.form_schema as FormSchema | undefined
      if (!schema?.sections?.length) continue

      const formValues =
        (data.variables as { form?: Record<string, unknown> } | undefined)?.form || {}

      const meta: PrintSheetMeta = {
        id: Number(data.id) || 0,
        displayNo: String(data.display_no || data.id || ''),
        status: String(data.status || ''),
        definitionName: String(data.definition_name || ref.title || ''),
        initiatorName: String(data.initiator_name || ''),
        departmentName: String(data.department_name || ''),
        departmentPath: String(
          data.apply_department_path || data.department_name || '',
        ),
        companyName: String(data.company_name || ''),
        startedAt: (data.started_at as string | null) ?? null,
        printedAt: printContext.printedAt,
        printerName: printContext.printerName,
      }

      const sections = await buildPrintSections(schema, formValues, userOpts, deptOpts, {
        companyId: Number(data.company_id) || undefined,
      })
      const attachments = collectPrintAttachments(schema, formValues)
      const flow = data.flow_progress as { process_graph?: ProcessGraph } | undefined

      bundles.push({
        key: ref.publicUuid,
        linkLabel: ref.fieldLabel,
        schema,
        formValues,
        meta,
        timeline: (data.timeline as PrintTimelineItem[]) || [],
        sections,
        attachments,
        processGraph: flow?.process_graph,
      })
    } catch {
      // 无权限或已删除的关联单跳过
    }
  }

  return bundles
}
