<template>
  <div class="smart-receipt-field">
    <template v-if="readonly">
      <span v-if="!files.length" class="sr-empty">—</span>
      <ul v-else class="sr-file-list">
        <li v-for="(f, i) in files" :key="i">
          <AttachmentFileLink v-if="f.url" :file="f" :field-label="fieldLabel || '智能票据'" />
          <span v-else>{{ f.name }}</span>
        </li>
      </ul>
    </template>
    <template v-else>
      <a-upload
        :file-list="arcoList"
        :limit="maxCount"
        :accept="acceptAttr"
        :multiple="maxCount !== 1"
        :show-file-list="true"
        :show-link="false"
        :custom-request="handleUpload"
        @before-remove="beforeRemove"
        @preview="onPreviewFile"
      >
        <template #upload-button>
          <a-button type="outline" size="small" :loading="uploading">
            <icon-upload /> 上传票据
          </a-button>
        </template>
      </a-upload>
      <p class="sr-hint">支持图片（JPG/PNG/WebP 等）与 PDF；可识别国内外发票、收据、小票等凭证；单文件不超过 {{ FRONTEND_UPLOAD_MAX_MB }} MB</p>

      <div v-for="item in pendingItems" :key="item.uid" class="sr-result-card">
        <div class="sr-result-head">
          <span class="sr-file-name">{{ item.file.name }}</span>
          <a-tag v-if="item.status === 'recognizing'" color="arcoblue" size="small">识别中…</a-tag>
          <a-tag v-else-if="item.status === 'error'" color="red" size="small">识别失败</a-tag>
          <a-tag v-else-if="item.result && isReceiptDuplicate(item.result.duplicate)" color="red" size="small">重复票据</a-tag>
          <a-tag v-else color="green" size="small">识别完成</a-tag>
        </div>

        <a-alert v-if="item.error" type="error" :title="item.error" class="sr-alert" />

        <template v-if="item.result">
          <div class="sr-summary">
            <div v-if="item.result.extracted.document_type">
              <span class="sr-label">票种</span>{{ item.result.extracted.document_type }}
            </div>
            <div v-if="item.result.extracted.merchant_name">
              <span class="sr-label">商户</span>{{ item.result.extracted.merchant_name }}
            </div>
            <div v-if="item.result.extracted.transaction_date">
              <span class="sr-label">日期</span>{{ item.result.extracted.transaction_date }}
            </div>
            <div v-if="item.result.extracted.total_amount != null">
              <span class="sr-label">金额</span>
              {{ formatAmount(item.result.extracted) }}
            </div>
            <div v-if="item.result.extracted.expense_category">
              <span class="sr-label">类别</span>{{ item.result.extracted.expense_category }}
            </div>
            <div v-if="item.result.extracted.confidence != null" class="sr-conf">
              置信度 {{ Math.round(Number(item.result.extracted.confidence) * 100) }}%
              <span v-if="item.result.provider_used"> · {{ item.result.provider_used }}</span>
            </div>
          </div>
          <a-alert
            v-for="(w, wi) in item.result.warnings || []"
            :key="wi"
            type="warning"
            :title="w"
            class="sr-alert"
          />
          <a-tag v-if="item.applied" color="green" size="small">已自动填入</a-tag>
        </template>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { IconUpload } from '@arco-design/web-vue/es/icon'
import type { FileItem, RequestOption } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import type { AttachmentFileItem } from '@/components/form/AttachmentField.vue'
import AttachmentFileLink from '@/components/form/AttachmentFileLink.vue'
import {
  FRONTEND_UPLOAD_MAX_MB,
  uploadErrorMessage,
  validateAttachmentFileLocal,
} from '@/utils/attachmentUpload'
import type {
  ReceiptExtracted,
  ReceiptRecognitionResult,
  SmartReceiptRecognitionConfig,
} from '@/constants/receiptExtractKeys'
import type { FormSchema } from '@/types/form'
import {
  applySmartReceiptFill,
  collectCategoryOptions,
} from '@/composables/useSmartReceiptFill'
import { collectFormFieldHints } from '@/composables/useReceiptRecognition'
import { formatReceiptDuplicateMessage, isReceiptDuplicate } from '@/composables/useReceiptDuplicate'
import { openAttachmentPreview } from '@/composables/useAttachmentPreview'

interface PendingItem {
  uid: string
  file: AttachmentFileItem
  status: 'recognizing' | 'done' | 'error'
  error?: string
  result?: ReceiptRecognitionResult
  applied?: boolean
}

const props = withDefaults(
  defineProps<{
    modelValue?: AttachmentFileItem[] | unknown
    readonly?: boolean
    accept?: string
    maxCount?: number
    recognition?: SmartReceiptRecognitionConfig
    schema: FormSchema
    fieldLabel?: string
  }>(),
  {
    readonly: false,
    accept: 'image/jpeg,image/png,image/webp,image/gif,.pdf',
    maxCount: 20,
    recognition: () => ({}),
  },
)

const emit = defineEmits<{
  'update:modelValue': [AttachmentFileItem[]]
  filled: []
}>()

const formModel = inject<Record<string, unknown> | null>('smartReceiptFormModel', null)
const applyContext = inject<{ companyId?: number; excludeInstanceRef?: string } | null>(
  'formApplyContext',
  null,
)

const uploading = ref(false)
const pendingItems = ref<PendingItem[]>([])

const files = computed(() => {
  const v = props.modelValue
  if (!Array.isArray(v)) return [] as AttachmentFileItem[]
  return v.filter((x) => x && typeof x === 'object') as AttachmentFileItem[]
})

const maxCount = computed(() => props.maxCount)
const acceptAttr = computed(() => props.accept)

const arcoList = computed<FileItem[]>(() =>
  files.value.map((f, i) => ({
    uid: f.uid || f.path || String(i),
    name: f.name,
    url: f.url,
    status: 'done' as const,
  })),
)

function emitFiles(list: AttachmentFileItem[]) {
  emit('update:modelValue', list)
}

function formatAmount(extracted: ReceiptExtracted) {
  const cur = extracted.currency || 'CNY'
  const amt = extracted.total_amount
  if (amt == null) return '—'
  return `${cur} ${Number(amt).toFixed(2)}`
}

async function handleUpload(option: RequestOption) {
  const { fileItem, onError, onSuccess } = option
  const raw = fileItem.file
  if (!raw) {
    onError?.({ message: '无效文件' })
    return
  }
  const localErr = validateAttachmentFileLocal(raw as File, null)
  if (localErr) {
    Message.warning(localErr)
    onError?.({ message: localErr })
    return
  }
  uploading.value = true
  const fd = new FormData()
  fd.append('file', raw as File)
  try {
    const res = await api.post<
      ApiResponse<{ name: string; path: string; url: string; size?: number }>
    >('/uploads/attachments', fd)
    if (!res.data.ok) throw new Error(res.data.message || '上传失败')
    const item: AttachmentFileItem = {
      name: res.data.data.name,
      path: res.data.data.path,
      url: res.data.data.url,
      size: res.data.data.size,
      uid: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    }
    emitFiles([...files.value, item])
    onSuccess?.(res.data)

    if (props.recognition?.enabled !== false) {
      void recognizeFile(item)
    }
  } catch (e: unknown) {
    const msg = uploadErrorMessage(e)
    Message.error(msg)
    onError?.({ message: msg })
  } finally {
    uploading.value = false
  }
}

async function recognizeFile(file: AttachmentFileItem) {
  const cfg = props.recognition || {}
  const uid = file.uid || file.path
  const pending: PendingItem = { uid, file, status: 'recognizing' }
  pendingItems.value = [...pendingItems.value, pending]

  const categoryFieldKey = cfg.categoryFieldKey || ''
  const detailKey = cfg.targetDetailKey || ''
  const scope = cfg.fillMode === 'main_fields' ? 'main' : 'detail'
  const categoryOptions = collectCategoryOptions(
    props.schema,
    categoryFieldKey,
    scope as 'main' | 'detail',
    detailKey,
  )
  const formFields = collectFormFieldHints({
    schema: props.schema,
    fillMode: cfg.fillMode,
    targetDetailKey: detailKey,
    attachColumnKey: cfg.attachToScope === 'detail' ? cfg.attachToFieldKey : undefined,
  })

  try {
    const res = await api.post<ApiResponse<ReceiptRecognitionResult>>('/ai/recognize-receipt', {
      file_path: file.path,
      scene: cfg.scene || 'expense',
      provider_id: cfg.providerId ?? null,
      mappings: cfg.mappings || [],
      category_options: categoryOptions,
      form_fields: formFields,
      company_id: applyContext?.companyId ?? null,
      exclude_instance_ref: applyContext?.excludeInstanceRef || null,
    })
    if (!res.data.ok) throw new Error(res.data.message || '识别失败')
    const result = res.data.data
    if (isReceiptDuplicate(result.duplicate)) {
      const dupMsg = formatReceiptDuplicateMessage(result.duplicate!)
      pendingItems.value = pendingItems.value.map((p) =>
        p.uid === uid ? { ...p, status: 'error', result, error: dupMsg } : p,
      )
      Message.error(dupMsg)
      return
    }
    pendingItems.value = pendingItems.value.map((p) =>
      p.uid === uid ? { ...p, status: 'done', result } : p,
    )
    if (cfg.autoFill !== false) {
      confirmFillByUid(uid)
    }
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '识别失败'
    pendingItems.value = pendingItems.value.map((p) =>
      p.uid === uid ? { ...p, status: 'error', error: msg } : p,
    )
    Message.warning(msg)
  }
}

function confirmFillByUid(uid: string) {
  const item = pendingItems.value.find((p) => p.uid === uid)
  if (!item?.result || !formModel) return
  applySmartReceiptFill(
    formModel,
    props.schema,
    props.recognition || {},
    item.result.fill_suggestions,
    item.file,
  )
  pendingItems.value = pendingItems.value.map((p) =>
    p.uid === uid ? { ...p, applied: true } : p,
  )
  emit('filled')
  Message.success('已自动填入表单')
}

function dismissPending(uid: string) {
  pendingItems.value = pendingItems.value.filter((p) => p.uid !== uid)
}

function onPreviewFile(file: FileItem) {
  const hit = files.value.find(
    (f) => (f.uid || f.path) === file.uid || f.name === file.name,
  )
  if (hit) {
    openAttachmentPreview(hit, props.fieldLabel || '智能票据')
    return
  }
  if (file.url) {
    openAttachmentPreview(
      { name: file.name || '票据', url: file.url, path: file.uid },
      props.fieldLabel || '智能票据',
    )
  }
}

function beforeRemove(file: FileItem) {
  const next = files.value.filter(
    (f) => (f.uid || f.path) !== file.uid && f.name !== file.name,
  )
  emitFiles(next)
  pendingItems.value = pendingItems.value.filter((p) => p.file.name !== file.name)
  return true
}
</script>

<style scoped>
.smart-receipt-field {
  width: 100%;
  min-width: 0;
  max-width: 100%;
}

.smart-receipt-field :deep(.arco-upload) {
  max-width: 100%;
}

.smart-receipt-field :deep(.arco-upload-list),
.smart-receipt-field :deep(.arco-upload-list-item) {
  max-width: 100%;
  box-sizing: border-box;
}

.smart-receipt-field :deep(.arco-upload-list-item-content) {
  overflow: hidden;
  min-width: 0;
}

.smart-receipt-field :deep(.arco-upload-list-item-name) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sr-empty {
  color: var(--color-text-3, #86909c);
  font-size: 0.875rem;
}

.sr-hint {
  margin: 6px 0 0;
  font-size: 0.75rem;
  color: var(--color-text-3, #86909c);
  line-height: 1.4;
  word-break: break-word;
}

.sr-file-list {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.875rem;
}

.sr-file-list a {
  color: rgb(var(--primary-6));
}

.sr-result-card {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--color-border-2, #e5e6eb);
  border-radius: 8px;
  background: var(--color-fill-1, #f7f8fa);
}

.sr-result-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.sr-file-name {
  flex: 1;
  font-size: 0.8125rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sr-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 12px;
  font-size: 0.8125rem;
  margin-bottom: 8px;
}

.sr-label {
  color: var(--color-text-3, #86909c);
  margin-right: 6px;
}

.sr-conf {
  grid-column: 1 / -1;
  font-size: 0.75rem;
  color: var(--color-text-3, #86909c);
  word-break: break-word;
}

@media (max-width: 640px) {
  .sr-summary {
    grid-template-columns: 1fr;
  }
}

.sr-alert {
  margin-bottom: 8px;
}
</style>
