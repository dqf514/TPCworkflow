<template>
  <div class="attachment-field">
    <template v-if="readonly">
      <span v-if="!files.length" class="att-empty">—</span>
      <span v-else-if="countOnly">{{ files.length }} 个附件</span>
      <ul v-else class="att-list">
        <li v-for="(f, i) in files" :key="i">
          <AttachmentFileLink v-if="f.url" :file="f" :field-label="fieldLabel" />
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
        :show-file-list="!countOnly"
        :show-link="false"
        :custom-request="handleUpload"
        @change="onArcoChange"
        @before-remove="beforeRemove"
        @preview="onPreviewFile"
      >
        <template #upload-button>
          <a-tooltip v-if="uploadTooltip" :content="uploadTooltip" position="top">
            <a-button type="outline" size="small">
              <icon-upload /> 上传
            </a-button>
          </a-tooltip>
          <a-button v-else type="outline" size="small">
            <icon-upload /> 上传
          </a-button>
        </template>
      </a-upload>
      <span v-if="countOnly && files.length" class="att-count">{{ files.length }} 个附件</span>
      <p v-if="!countOnly && policyHintFull" class="att-hint">{{ policyHintFull }}</p>
      <p v-if="!countOnly && pdfPrintTip" class="att-hint att-hint--tip">{{ pdfPrintTip }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { IconUpload } from '@arco-design/web-vue/es/icon'
import type { FileItem, RequestOption } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import AttachmentFileLink from '@/components/form/AttachmentFileLink.vue'
import {
  ATTACHMENT_PDF_PRINT_TIP,
  buildAttachmentUploadHint,
  buildAttachmentUploadTooltip,
  shouldShowAttachmentPdfPrintTip,
  type AttachmentPolicy,
  uploadErrorMessage,
  validateAttachmentFileLocal,
} from '@/utils/attachmentUpload'
import { openAttachmentPreview } from '@/composables/useAttachmentPreview'

export interface AttachmentFileItem {
  name: string
  path: string
  url?: string
  size?: number
  uid?: string
}

const props = withDefaults(
  defineProps<{
    modelValue?: AttachmentFileItem[] | unknown
    readonly?: boolean
    accept?: string
    maxCount?: number
    countOnly?: boolean
    imageOnly?: boolean
    fieldLabel?: string
  }>(),
  {
    readonly: false,
    accept: '',
    maxCount: 20,
    countOnly: false,
    imageOnly: false,
  },
)

const emit = defineEmits<{ 'update:modelValue': [AttachmentFileItem[]] }>()

const policy = ref<AttachmentPolicy | null>(null)

const acceptAttr = computed(() => {
  if (props.accept) return props.accept
  if (props.imageOnly) return 'image/*'
  return policy.value?.accept || undefined
})

const policyHintFull = computed(() => {
  if (props.readonly || props.accept) return ''
  if (props.imageOnly) return buildAttachmentUploadHint(null)
  return buildAttachmentUploadHint(policy.value)
})

const pdfPrintTip = computed(() => {
  if (props.readonly || props.countOnly) return ''
  if (
    !shouldShowAttachmentPdfPrintTip({
      imageOnly: props.imageOnly,
      accept: props.accept,
    })
  ) {
    return ''
  }
  return ATTACHMENT_PDF_PRINT_TIP
})

const uploadTooltip = computed(() => {
  if (props.readonly) return ''
  if (props.accept) return pdfPrintTip.value
  return buildAttachmentUploadTooltip(policy.value, {
    imageOnly: props.imageOnly,
    accept: props.accept,
  })
})

const files = computed(() => {
  const v = props.modelValue
  if (!Array.isArray(v)) return [] as AttachmentFileItem[]
  return v.filter((x) => x && typeof x === 'object') as AttachmentFileItem[]
})

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

function validateLocal(file: File): string | null {
  return validateAttachmentFileLocal(file, policy.value)
}

async function loadPolicy() {
  if (props.imageOnly || props.readonly) return
  try {
    const res = await api.get<ApiResponse<AttachmentPolicy>>('/uploads/attachment-policy')
    if (res.data.ok) policy.value = res.data.data
  } catch {
    /* 使用服务端校验 */
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
  } catch (e: unknown) {
    const msg = uploadErrorMessage(e)
    Message.error(msg)
    onError?.({ message: msg })
  }
}

function onArcoChange(_list: FileItem[], file: FileItem) {
  if (file.status === 'error') return
}

function onPreviewFile(file: FileItem) {
  const hit = files.value.find(
    (f) => (f.uid || f.path) === file.uid || f.name === file.name,
  )
  if (hit) {
    openAttachmentPreview(hit, props.fieldLabel)
    return
  }
  if (file.url) {
    openAttachmentPreview({ name: file.name || '附件', url: file.url, path: file.uid }, props.fieldLabel)
  }
}

function beforeRemove(file: FileItem) {
  const next = files.value.filter(
    (f) => (f.uid || f.path) !== file.uid && f.name !== file.name,
  )
  emitFiles(next)
  return true
}
</script>

<style scoped>
.attachment-field {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
}

.attachment-field :deep(.arco-upload) {
  display: block;
  width: 100%;
  max-width: 100%;
}

.attachment-field :deep(.arco-upload-list),
.attachment-field :deep(.arco-upload-list-item) {
  max-width: 100%;
  box-sizing: border-box;
}

.attachment-field :deep(.arco-upload-list-item-content) {
  overflow: hidden;
  min-width: 0;
}

.attachment-field :deep(.arco-upload-list-item-name) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.att-empty {
  color: var(--text-tertiary, #9699a6);
  font-size: 0.875rem;
}

.att-count {
  display: inline-block;
  margin-top: 4px;
  font-size: 0.8125rem;
  color: var(--text-secondary, #676879);
}

.att-hint {
  margin: 4px 0 0;
  font-size: 0.75rem;
  color: var(--text-tertiary, #9699a6);
  line-height: 1.4;
  word-break: break-word;
}

.att-hint--tip {
  color: var(--text-secondary, #676879);
}

.att-list {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.875rem;
}

.att-list a {
  color: var(--brand, #5034ff);
}
</style>
