import { readonly, ref } from 'vue'
import type { AttachmentFileItem } from '@/components/form/AttachmentField.vue'
import { attachmentMimeKind, resolveAttachmentUrl } from '@/composables/usePrintAttachments'

export interface AttachmentPreviewItem {
  name: string
  url: string
  path?: string
  size?: number
  kind: 'image' | 'pdf' | 'other'
  fieldLabel?: string
}

const visible = ref(false)
const current = ref<AttachmentPreviewItem | null>(null)

export function toAttachmentPreviewItem(
  file: AttachmentFileItem | { name?: string; url?: string; path?: string; size?: number },
  fieldLabel?: string,
): AttachmentPreviewItem | null {
  const name = String(file.name || '').trim()
  const url = resolveAttachmentUrl({
    url: file.url != null ? String(file.url) : undefined,
    path: file.path != null ? String(file.path) : undefined,
  })
  if (!url) return null
  const displayName = name || url.split('/').pop() || '未命名附件'
  return {
    name: displayName,
    url,
    path: file.path != null ? String(file.path) : undefined,
    size: file.size != null ? Number(file.size) : undefined,
    kind: attachmentMimeKind(displayName),
    fieldLabel,
  }
}

export function openAttachmentPreview(
  file: AttachmentFileItem | { name?: string; url?: string; path?: string; size?: number },
  fieldLabel?: string,
) {
  const item = toAttachmentPreviewItem(file, fieldLabel)
  if (!item) return
  current.value = item
  visible.value = true
}

export function closeAttachmentPreview() {
  visible.value = false
}

export function useAttachmentPreviewState() {
  return {
    visible: readonly(visible),
    current: readonly(current),
    openAttachmentPreview,
    closeAttachmentPreview,
  }
}
