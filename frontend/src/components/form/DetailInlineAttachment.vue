<template>
  <div class="detail-inline-att" :class="{ 'detail-inline-att--block': !compact }">
    <template v-if="readonly">
      <span v-if="!files.length" class="dia-empty">—</span>
      <ul v-else class="dia-files">
        <li v-for="(f, i) in files" :key="i">
          <AttachmentFileLink
            v-if="f.url"
            :file="f"
            :truncate="compact"
            :field-label="column.label"
          />
          <span v-else>{{ shortName(f.name) }}</span>
        </li>
      </ul>
    </template>
    <template v-else>
      <div v-if="showUploadButton || recognizing" class="dia-toolbar">
        <a-upload
          v-if="showUploadButton"
          :file-list="[]"
          :limit="maxCount"
          :accept="acceptAttr"
          :multiple="allowMultiple"
          :show-file-list="false"
          :custom-request="handleUpload"
        >
          <template #upload-button>
            <a-tooltip v-if="uploadTooltip" :content="uploadTooltip" position="top">
              <a-button type="outline" size="mini" :loading="uploading">
                <icon-upload /> {{ uploadLabel }}
              </a-button>
            </a-tooltip>
            <a-button v-else type="outline" size="mini" :loading="uploading">
              <icon-upload /> {{ uploadLabel }}
            </a-button>
          </template>
        </a-upload>
        <a-tag v-if="recognizing" size="small" color="arcoblue">识别中…</a-tag>
      </div>

      <p v-if="pdfPrintTip && showUploadButton" class="dia-hint">{{ pdfPrintTip }}</p>

      <ul v-if="files.length" class="dia-files">
        <li v-for="(f, i) in files" :key="f.uid || f.path || i" class="dia-file-item">
          <AttachmentFileLink
            v-if="f.url"
            :file="f"
            :truncate="compact"
            :field-label="column.label"
          />
          <span v-else :title="f.name">{{ shortName(f.name) }}</span>
          <a-button type="text" size="mini" status="danger" @click="removeFile(f)">×</a-button>
        </li>
      </ul>

      <a-alert v-if="recognizeError" type="warning" :title="recognizeError" class="dia-alert" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { IconUpload } from '@arco-design/web-vue/es/icon'
import type { RequestOption } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import type { AttachmentFileItem } from '@/components/form/AttachmentField.vue'
import AttachmentFileLink from '@/components/form/AttachmentFileLink.vue'
import {
  ATTACHMENT_PDF_PRINT_TIP,
  buildAttachmentUploadTooltip,
  canShowAttachmentUpload,
  resolveAttachmentUploadLimit,
  shouldShowAttachmentPdfPrintTip,
  type AttachmentPolicy,
  uploadErrorMessage,
  validateAttachmentFileLocal,
} from '@/utils/attachmentUpload'
import type { FormFieldDef, FormSchema } from '@/types/form'
import type { ReceiptRecognitionResult } from '@/constants/receiptExtractKeys'
import { applyReceiptToDetailRow } from '@/composables/useSmartReceiptFill'
import {
  requestReceiptRecognition,
  resolveDetailRecognitionConfig,
} from '@/composables/useReceiptRecognition'
import { formatReceiptDuplicateMessage, isReceiptDuplicate } from '@/composables/useReceiptDuplicate'

const props = withDefaults(
  defineProps<{
    column: FormFieldDef
    modelValue?: unknown
    readonly?: boolean
    rowIndex: number
    columns: FormFieldDef[]
    detailKey: string
    /** 表格内联模式：窄列；卡片/手机端为 false，纵向全宽 */
    compact?: boolean
  }>(),
  { compact: true },
)

const emit = defineEmits<{
  'update:modelValue': [AttachmentFileItem[]]
  'fill-row': [Record<string, unknown>]
}>()

const formSchema = inject<FormSchema | null>('formSchema', null)
const applyContext = inject<{ companyId?: number; excludeInstanceRef?: string } | null>(
  'formApplyContext',
  null,
)

const uploading = ref(false)
const recognizing = ref(false)
const recognizeError = ref('')
const pendingResult = ref<ReceiptRecognitionResult | null>(null)
const pendingFile = ref<AttachmentFileItem | null>(null)

const policy = ref<AttachmentPolicy | null>(null)

const uploadLimit = computed(() => resolveAttachmentUploadLimit(props.column.props))
const maxCount = computed(() => uploadLimit.value.maxCount)
const allowMultiple = computed(() => uploadLimit.value.allowMultiple)
const imageOnly = computed(() => props.column.type === 'image')
const recognitionConfig = computed(() =>
  resolveDetailRecognitionConfig(props.column, props.columns),
)
const uploadLabel = computed(() => (recognitionConfig.value ? '上传票据' : '上传'))

const files = computed(() => {
  const v = props.modelValue
  if (!Array.isArray(v)) return [] as AttachmentFileItem[]
  return v.filter((x) => x && typeof x === 'object') as AttachmentFileItem[]
})

const showUploadButton = computed(() =>
  canShowAttachmentUpload(files.value.length, props.column.props),
)

const acceptAttr = computed(() => {
  const custom = String(props.column.props?.accept || '')
  if (custom) return custom
  if (imageOnly.value) return 'image/*'
  if (recognitionConfig.value) return 'image/jpeg,image/png,image/webp,image/gif,.pdf'
  return policy.value?.accept || undefined
})

const pdfPrintTip = computed(() => {
  if (props.readonly) return ''
  const customAccept = String(props.column.props?.accept || '')
  if (
    !shouldShowAttachmentPdfPrintTip({
      imageOnly: imageOnly.value,
      recognition: !!recognitionConfig.value,
      accept: customAccept,
    })
  ) {
    return ''
  }
  return ATTACHMENT_PDF_PRINT_TIP
})

const uploadTooltip = computed(() => {
  if (props.readonly || imageOnly.value) return pdfPrintTip.value
  const customAccept = String(props.column.props?.accept || '')
  return buildAttachmentUploadTooltip(policy.value, {
    recognition: !!recognitionConfig.value,
    imageOnly: imageOnly.value,
    accept: customAccept,
  })
})

function shortName(name: string) {
  if (name.length <= 14) return name
  return `${name.slice(0, 6)}…${name.slice(-5)}`
}

function emitFiles(list: AttachmentFileItem[]) {
  emit('update:modelValue', list)
}

function validateLocal(file: File): string | null {
  return validateAttachmentFileLocal(file, policy.value)
}

async function loadPolicy() {
  if (imageOnly.value || props.readonly) return
  try {
    const res = await api.get<ApiResponse<AttachmentPolicy>>('/uploads/attachment-policy')
    if (res.data.ok) policy.value = res.data.data
  } catch {
    /* 服务端校验兜底 */
  }
}

onMounted(() => {
  void loadPolicy()
})

async function handleUpload(option: RequestOption) {
  const { fileItem, onError, onSuccess } = option
  const raw = fileItem.file
  if (!raw) {
    onError?.({ message: '无效文件' })
    return
  }
  const localErr = validateLocal(raw as File)
  if (localErr) {
    Message.warning(localErr)
    onError?.({ message: localErr })
    return
  }

  uploading.value = true
  recognizeError.value = ''
  pendingResult.value = null
  pendingFile.value = null

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
    emitFiles(allowMultiple.value ? [...files.value, item] : [item])
    onSuccess?.(res.data)

    if (recognitionConfig.value && props.column.key) {
      pendingFile.value = item
      await recognizeUploaded(item)
    }
  } catch (e: unknown) {
    const msg = uploadErrorMessage(e)
    Message.error(msg)
    onError?.({ message: msg })
  } finally {
    uploading.value = false
  }
}

async function recognizeUploaded(file: AttachmentFileItem) {
  const cfg = recognitionConfig.value
  if (!cfg || !props.column.key) return

  recognizing.value = true
  recognizeError.value = ''
  try {
    const result = await requestReceiptRecognition({
      filePath: file.path,
      scene: cfg.scene,
      providerId: cfg.providerId,
      mappings: cfg.mappings,
      schema: formSchema || undefined,
      categoryFieldKey: cfg.categoryFieldKey,
      detailKey: props.detailKey,
      columns: props.columns,
      attachColumnKey: props.column.key,
      fillMode: 'detail_row',
      companyId: applyContext?.companyId,
      excludeInstanceRef: applyContext?.excludeInstanceRef,
    })
    if (isReceiptDuplicate(result.duplicate)) {
      recognizeError.value = formatReceiptDuplicateMessage(result.duplicate!)
      Message.error(recognizeError.value)
      return
    }
    pendingResult.value = result
    confirmFill()
  } catch (e: unknown) {
    recognizeError.value = e instanceof Error ? e.message : '识别失败'
  } finally {
    recognizing.value = false
  }
}

function confirmFill() {
  if (!pendingResult.value || !props.column.key) return
  const patch = applyReceiptToDetailRow(
    {},
    pendingResult.value.fill_suggestions,
    props.column.key,
  )
  emit('fill-row', patch)
  pendingResult.value = null
  pendingFile.value = null
  Message.success('已自动填入本行')
}

function dismissResult() {
  pendingResult.value = null
  pendingFile.value = null
  recognizeError.value = ''
}

function removeFile(file: AttachmentFileItem) {
  emitFiles(files.value.filter((f) => (f.uid || f.path) !== (file.uid || file.path)))
  if (pendingFile.value && pendingFile.value.path === file.path) {
    dismissResult()
  }
}
</script>

<style scoped>
.detail-inline-att {
  min-width: 108px;
  max-width: 180px;
}

.detail-inline-att--block {
  min-width: 0;
  max-width: none;
  width: 100%;
  box-sizing: border-box;
}

.detail-inline-att--block .dia-toolbar {
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
}

.detail-inline-att--block :deep(.arco-upload) {
  display: block;
  width: 100%;
  max-width: 100%;
}

.detail-inline-att--block :deep(.arco-btn) {
  width: 100%;
  justify-content: center;
}

.detail-inline-att--block .dia-file-item a,
.detail-inline-att--block .dia-file-item span {
  white-space: normal;
  word-break: break-all;
}

.detail-inline-att--block .dia-alert {
  max-width: 100%;
}

.dia-empty {
  color: var(--color-text-3, #86909c);
  font-size: 0.8125rem;
}

.dia-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.dia-hint {
  margin: 4px 0 0;
  font-size: 0.6875rem;
  color: var(--color-text-3, #86909c);
  line-height: 1.4;
  word-break: break-word;
}

.dia-files {
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
}

.dia-file-item {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 0.75rem;
  line-height: 1.3;
}

.dia-file-item a,
.dia-file-item span,
.dia-file-item :deep(.att-file-link) {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgb(var(--primary-6));
}

.dia-alert {
  margin-top: 4px;
}
</style>
