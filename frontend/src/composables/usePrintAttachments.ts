import type { FormFieldDef, FormSchema } from '@/types/form'
import { buildLinkageContext, shouldDisplayField, shouldDisplaySection } from '@/composables/useFieldLinkage'
import { printT } from '@/utils/printI18n'

export type PrintAttachmentKind = 'image' | 'pdf' | 'other'

export interface PrintAttachmentItem {
  id: string
  name: string
  url: string
  path?: string
  size?: number
  fieldLabel: string
  sectionTitle: string
  kind: PrintAttachmentKind
}

const IMAGE_EXT = new Set(['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'])
const PDF_EXT = new Set(['.pdf'])

const ATTACHMENT_FIELD_TYPES = new Set(['attachment', 'image', 'smart_receipt'])

function fileExt(name: string): string {
  const base = (name || '').replace(/\\/g, '/').split('/').pop() || name
  const dot = base.lastIndexOf('.')
  return dot > 0 ? base.slice(dot).toLowerCase() : ''
}

export function attachmentMimeKind(name: string): PrintAttachmentKind {
  const ext = fileExt(name)
  if (IMAGE_EXT.has(ext)) return 'image'
  if (PDF_EXT.has(ext)) return 'pdf'
  return 'other'
}

/** 是否可随申请单一并打印（仅图片与 PDF） */
export function isPrintableAttachmentKind(kind: PrintAttachmentKind): boolean {
  return kind === 'image' || kind === 'pdf'
}

export function resolveAttachmentUrl(file: { url?: string; path?: string }): string {
  const url = (file.url || '').trim()
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('/')) {
    return url
  }
  const path = (file.path || url).replace(/^\//, '')
  if (!path) return ''
  const rel = path.startsWith('uploads/') ? path : `uploads/${path}`
  return `/api/v1/files/${rel}`
}

export function formatPrintFileSize(bytes?: number): string {
  if (bytes == null || Number.isNaN(bytes) || bytes <= 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function pushAttachmentFiles(
  items: PrintAttachmentItem[],
  files: unknown,
  ctx: { fieldLabel: string; sectionTitle: string },
) {
  if (!Array.isArray(files)) return
  for (const raw of files) {
    if (!raw || typeof raw !== 'object') continue
    const f = raw as Record<string, unknown>
    const name = String(f.name || f.filename || '').trim()
    const url = resolveAttachmentUrl({
      url: f.url != null ? String(f.url) : undefined,
      path: f.path != null ? String(f.path) : undefined,
    })
    if (!name && !url) continue
    const displayName = name || url.split('/').pop() || printT('print.unnamed_attachment')
    items.push({
      id: `${items.length}_${url || displayName}`,
      name: displayName,
      url,
      path: f.path != null ? String(f.path) : undefined,
      size: f.size != null ? Number(f.size) : undefined,
      fieldLabel: ctx.fieldLabel,
      sectionTitle: ctx.sectionTitle,
      kind: attachmentMimeKind(displayName),
    })
  }
}

function collectFromField(
  items: PrintAttachmentItem[],
  field: FormFieldDef,
  model: Record<string, unknown>,
  sectionTitle: string,
) {
  if (field.visible === false || field.printable === false) return
  if (!field.key && field.type !== 'detail') return

  if (field.type === 'detail') {
    const cols = ((field.props?.columns as FormFieldDef[]) || []).filter(
      (c) => c.key && ATTACHMENT_FIELD_TYPES.has(c.type) && c.printable !== false,
    )
    if (!cols.length) return
    const rawRows = Array.isArray(model[field.key!])
      ? (model[field.key!] as Record<string, unknown>[])
      : []
    rawRows.forEach((row, rowIndex) => {
      for (const col of cols) {
        const rowLabel =
          rawRows.length > 1
            ? `${field.label || printT('print.detail_field')} · ${printT('print.detail_row', { row: rowIndex + 1 })} · ${col.label || col.key}`
            : `${field.label || printT('print.detail_field')} · ${col.label || col.key}`
        pushAttachmentFiles(items, row[col.key!], {
          fieldLabel: rowLabel,
          sectionTitle,
        })
      }
    })
    return
  }

  if (!field.key || !ATTACHMENT_FIELD_TYPES.has(field.type)) return
  pushAttachmentFiles(items, model[field.key], {
    fieldLabel: field.label || field.key,
    sectionTitle,
  })
}

function collectAllPrintAttachments(
  schema: FormSchema,
  model: Record<string, unknown>,
): PrintAttachmentItem[] {
  const items: PrintAttachmentItem[] = []
  const linkageCtx = buildLinkageContext(schema)

  for (const sec of schema.sections || []) {
    if (!shouldDisplaySection(sec, schema, model, linkageCtx)) continue
    const sectionTitle = sec.title || printT('print.section_default')

    for (const field of sec.fields || []) {
      if (!shouldDisplayField(field, schema, model, linkageCtx)) continue
      collectFromField(items, field, model, sectionTitle)
    }
  }

  return items
}

/** 收集流程表单中可随申请单打印的附件（仅图片与 PDF，含明细表内附件） */
export function collectPrintAttachments(
  schema: FormSchema,
  model: Record<string, unknown>,
): PrintAttachmentItem[] {
  return collectAllPrintAttachments(schema, model).filter((item) =>
    isPrintableAttachmentKind(item.kind),
  )
}

/** 收集不支持合并打印的附件（Word/Excel 等，需用户自行打印） */
export function collectSkippedPrintAttachments(
  schema: FormSchema,
  model: Record<string, unknown>,
): PrintAttachmentItem[] {
  return collectAllPrintAttachments(schema, model).filter(
    (item) => !isPrintableAttachmentKind(item.kind),
  )
}

/** 打印前等待图片等资源加载（含 PDF 转图片） */
export async function waitForPrintAssets(container: HTMLElement, timeoutMs = 20000): Promise<void> {
  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    if (container.querySelector('.wf-print-pdf-loading')) {
      await new Promise<void>((resolve) => setTimeout(resolve, 250))
      continue
    }

    const imgs = Array.from(
      container.querySelectorAll('img.wf-print-att-img, img.wf-print-pdf-page'),
    ) as HTMLImageElement[]

    const pending = imgs.filter((img) => !(img.complete && img.naturalWidth > 0))
    if (!pending.length) {
      if (container.querySelector('.wf-print-pdf-error')) break
      if (container.querySelector('.wf-print-pdf-embed')) break
      if (imgs.length || !container.querySelector('.wf-print-att-pdf')) break
      await new Promise<void>((resolve) => setTimeout(resolve, 300))
      if (!container.querySelector('.wf-print-att-pdf')) break
      continue
    }

    await Promise.race([
      Promise.all(
        pending.map(
          (img) =>
            new Promise<void>((resolve) => {
              const done = () => resolve()
              img.addEventListener('load', done, { once: true })
              img.addEventListener('error', done, { once: true })
            }),
        ),
      ),
      new Promise<void>((resolve) => setTimeout(resolve, Math.max(0, deadline - Date.now()))),
    ])
    break
  }
}
