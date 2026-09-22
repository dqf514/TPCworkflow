/** 前端上传硬上限（与反向代理 client_max_body_size 对齐，避免 413） */
export const FRONTEND_UPLOAD_MAX_BYTES = 5 * 1024 * 1024
export const FRONTEND_UPLOAD_MAX_MB = 5

export interface AttachmentPolicy {
  allowed_extensions: string[]
  max_bytes: number
  max_mb: number
  accept: string
}

export function getEffectiveUploadLimit(policy: AttachmentPolicy | null | undefined) {
  if (!policy || policy.max_bytes <= 0) {
    return { max_bytes: FRONTEND_UPLOAD_MAX_BYTES, max_mb: FRONTEND_UPLOAD_MAX_MB }
  }
  const max_bytes = Math.min(policy.max_bytes, FRONTEND_UPLOAD_MAX_BYTES)
  return { max_bytes, max_mb: Math.round((max_bytes / (1024 * 1024)) * 100) / 100 }
}

export function fileExtension(name: string): string {
  const base = name.replace(/\\/g, '/').split('/').pop() || name
  const i = base.lastIndexOf('.')
  return i >= 0 ? base.slice(i + 1).toLowerCase() : ''
}

export function validateAttachmentFileLocal(
  file: File,
  policy: AttachmentPolicy | null | undefined,
): string | null {
  if (file.size <= 0) return '文件为空'
  const limit = getEffectiveUploadLimit(policy)
  if (file.size > limit.max_bytes) {
    return `文件大小不能超过 ${limit.max_mb} MB`
  }
  if (policy && !policy.allowed_extensions.includes('*')) {
    const ext = fileExtension(file.name)
    if (!ext || !policy.allowed_extensions.includes(ext)) {
      return '该文件类型不在允许列表中'
    }
  }
  return null
}

export function buildAttachmentUploadHint(
  policy: AttachmentPolicy | null | undefined,
  options?: { recognition?: boolean },
): string {
  const limit = getEffectiveUploadLimit(policy)
  const sizePart = `单文件不超过 ${limit.max_mb} MB`
  if (!policy) {
    if (options?.recognition) return `${sizePart}；支持图片与 PDF`
    return sizePart
  }
  const exts = policy.allowed_extensions.includes('*')
    ? '任意类型（仍禁止可执行文件）'
    : policy.allowed_extensions.map((e) => `.${e}`).join('、')
  return `允许：${exts}；${sizePart}`
}

/** 建议用户上传 PDF，便于打印与审批查看 */
export const ATTACHMENT_PDF_PRINT_TIP =
  '为获得更好的打印与审批体验，建议将 Word、Excel 等文件在 Office 中「另存为 PDF」后再上传。'

export function shouldShowAttachmentPdfPrintTip(options?: {
  imageOnly?: boolean
  recognition?: boolean
  accept?: string
}): boolean {
  if (options?.imageOnly || options?.recognition) return false
  const accept = (options?.accept || '').trim().toLowerCase()
  if (!accept) return true
  if (accept === 'image/*') return false
  if (accept.startsWith('image/') && !accept.includes('pdf')) return false
  return true
}

export function buildAttachmentUploadTooltip(
  policy: AttachmentPolicy | null | undefined,
  options?: { recognition?: boolean; imageOnly?: boolean; accept?: string },
): string {
  const hint = buildAttachmentUploadHint(policy, options)
  const parts = [hint]
  if (shouldShowAttachmentPdfPrintTip(options)) {
    parts.push(ATTACHMENT_PDF_PRINT_TIP)
  }
  return parts.filter(Boolean).join('\n')
}

export function uploadErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    const msg = err.message
    if (/413|Content Too Large|too large/i.test(msg)) {
      return `文件过大，单文件不能超过 ${FRONTEND_UPLOAD_MAX_MB} MB`
    }
    return msg
  }
  return '上传失败'
}

export interface AttachmentFieldProps {
  allowMultiple?: boolean
  maxCount?: number
}

/** 解析附件列上传限制：单文件模式 maxCount=1，有文件时隐藏上传按钮 */
export function resolveAttachmentUploadLimit(props?: AttachmentFieldProps | null) {
  if (props?.allowMultiple === false) {
    return { maxCount: 1, allowMultiple: false }
  }
  if (props?.allowMultiple === true) {
    const maxCount = Math.max(2, Number(props.maxCount) || 5)
    return { maxCount, allowMultiple: true }
  }
  // 兼容旧表单：未配置 allowMultiple 时沿用 maxCount
  const maxCount = Math.max(1, Number(props?.maxCount) || 5)
  return { maxCount, allowMultiple: maxCount > 1 }
}

export function canShowAttachmentUpload(fileCount: number, props?: AttachmentFieldProps | null) {
  const { maxCount } = resolveAttachmentUploadLimit(props)
  return fileCount < maxCount
}
