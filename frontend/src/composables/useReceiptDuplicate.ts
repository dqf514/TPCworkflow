import type { ReceiptDuplicateInfo } from '@/constants/receiptExtractKeys'

export function formatReceiptDuplicateMessage(dup: ReceiptDuplicateInfo): string {
  const label = dup.display_no || String(dup.instance_id || '')
  const doc = dup.document_number || dup.file_path?.split('/').pop() || '该票据'
  if (dup.reason === 'file_path') {
    return `附件 ${doc} 已在已通过申请 ${label} 中使用，不可重复上传`
  }
  return `票号 ${doc} 已在已通过申请 ${label} 中使用，不可重复报销`
}

export function isReceiptDuplicate(dup?: ReceiptDuplicateInfo | null): boolean {
  return !!dup?.used
}
