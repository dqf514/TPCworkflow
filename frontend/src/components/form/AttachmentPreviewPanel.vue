<template>
  <Teleport to="body">
    <div
      v-if="visible && current"
      class="att-preview-layer"
      @mousedown.self="closeAttachmentPreview"
    >
      <div
        ref="panelRef"
        class="att-preview-panel"
        :class="{ 'is-maximized': maximized }"
        :style="panelStyle"
        role="dialog"
        aria-modal="true"
        :aria-label="current.name"
      >
        <header class="att-preview-head" @mousedown="onDragStart">
          <div class="att-preview-head-text">
            <span class="att-preview-title">{{ current.name }}</span>
            <span v-if="current.fieldLabel" class="att-preview-field">{{ current.fieldLabel }}</span>
          </div>
          <div class="att-preview-actions" @mousedown.stop>
            <a-button-group size="mini">
              <a-button type="text" title="缩小" @click="zoomOut">−</a-button>
              <a-button type="text" class="att-zoom-label" @click="resetZoom">{{ zoomLabel }}</a-button>
              <a-button type="text" title="放大" @click="zoomIn">+</a-button>
            </a-button-group>
            <a-button type="text" size="mini" @click="toggleMaximize">
              {{ maximized ? '还原' : '最大化' }}
            </a-button>
            <a-button type="text" size="mini" @click.stop="downloadCurrent">下载</a-button>
            <a-button type="text" size="mini" @click.stop="closeAttachmentPreview">
              <icon-close />
            </a-button>
          </div>
        </header>

        <div
          ref="bodyRef"
          class="att-preview-body"
          @wheel="onWheel"
        >
          <div v-if="loading" class="att-preview-state">加载中…</div>
          <div v-else-if="error" class="att-preview-state att-preview-state--error">{{ error }}</div>

          <div
            v-else
            class="att-preview-zoom-stage"
            :style="zoomStageStyle"
          >
            <img
              v-if="current.kind === 'image'"
              :src="imageUrl"
              :alt="current.name"
              class="att-preview-image"
            />

            <div v-else-if="current.kind === 'pdf'" class="att-preview-pdf">
              <PrintPdfPages v-if="current.url" :url="current.url" :name="current.name" />
            </div>

            <div v-else class="att-preview-fallback">
              <div class="att-preview-fallback-icon">文</div>
              <p class="att-preview-fallback-name">{{ current.name }}</p>
              <p v-if="sizeText" class="att-preview-fallback-meta">{{ sizeText }}</p>
              <p class="att-preview-fallback-note">此格式暂不支持在线预览，请下载后查看。</p>
              <a-button type="primary" size="small" @click="downloadCurrent">下载文件</a-button>
            </div>
          </div>
        </div>

        <footer class="att-preview-foot">
          拖动标题栏移动；滚轮或 +/- 缩放；Ctrl+滚轮快速缩放
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { IconClose } from '@arco-design/web-vue/es/icon'
import { Message } from '@arco-design/web-vue'
import PrintPdfPages from '@/components/print/PrintPdfPages.vue'
import { formatPrintFileSize } from '@/composables/usePrintAttachments'
import {
  closeAttachmentPreview,
  useAttachmentPreviewState,
} from '@/composables/useAttachmentPreview'
import { encodeUrlPath } from '@/utils/pdfRender'
import { api } from '@/api/client'

const { visible, current } = useAttachmentPreviewState()

const panelRef = ref<HTMLElement | null>(null)
const bodyRef = ref<HTMLElement | null>(null)
const pos = ref({ x: 0, y: 0 })
const positioned = ref(false)
const maximized = ref(false)
const loading = ref(false)
const error = ref('')
const imageUrl = ref('')
const zoom = ref(1)

const ZOOM_MIN = 0.35
const ZOOM_MAX = 3
const ZOOM_STEP = 0.15

const panelStyle = computed(() => {
  if (maximized.value) return {}
  return { transform: `translate(${pos.value.x}px, ${pos.value.y}px)` }
})

const zoomStageStyle = computed(() => ({
  transform: `scale(${zoom.value})`,
  transformOrigin: 'top center',
}))

const zoomLabel = computed(() => `${Math.round(zoom.value * 100)}%`)

const sizeText = computed(() => formatPrintFileSize(current.value?.size))

let dragStart = { x: 0, y: 0, px: 0, py: 0 }

function resetPosition() {
  const w = window.innerWidth
  const panelW = Math.min(960, w - 32)
  pos.value = {
    x: Math.max(16, (w - panelW) / 2),
    y: Math.max(16, 48),
  }
  positioned.value = true
}

function resetZoom() {
  zoom.value = 1
}

function zoomIn() {
  zoom.value = Math.min(ZOOM_MAX, Math.round((zoom.value + ZOOM_STEP) * 100) / 100)
}

function zoomOut() {
  zoom.value = Math.max(ZOOM_MIN, Math.round((zoom.value - ZOOM_STEP) * 100) / 100)
}

function toggleMaximize() {
  maximized.value = !maximized.value
  if (!maximized.value) resetPosition()
}

function onWheel(e: WheelEvent) {
  if (!current.value || current.value.kind === 'other') return
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP
    zoom.value = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round((zoom.value + delta) * 100) / 100))
    return
  }
  if (current.value.kind === 'pdf' || current.value.kind === 'image') {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP
    zoom.value = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round((zoom.value + delta) * 100) / 100))
  }
}

function onDragStart(e: MouseEvent) {
  if (maximized.value) return
  if (e.button !== 0) return
  dragStart = { x: e.clientX, y: e.clientY, px: pos.value.x, py: pos.value.y }
  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
  e.preventDefault()
}

function onDragMove(e: MouseEvent) {
  const dx = e.clientX - dragStart.x
  const dy = e.clientY - dragStart.y
  const panel = panelRef.value
  const maxX = window.innerWidth - (panel?.offsetWidth || 720)
  const maxY = window.innerHeight - 120
  pos.value = {
    x: Math.min(Math.max(8, dragStart.px + dx), Math.max(8, maxX)),
    y: Math.min(Math.max(8, dragStart.py + dy), Math.max(8, maxY)),
  }
}

function onDragEnd() {
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
}

async function loadImagePreview(url: string) {
  loading.value = true
  error.value = ''
  imageUrl.value = ''
  try {
    const encoded = encodeUrlPath(url)
    if (
      encoded.startsWith('http://') ||
      encoded.startsWith('https://') ||
      encoded.startsWith('blob:') ||
      encoded.startsWith('data:')
    ) {
      if (encoded.startsWith(window.location.origin)) {
        const apiPath = new URL(encoded).pathname.replace(/^\/api\/v1/, '')
        const res = await api.get<Blob>(apiPath, { responseType: 'blob' })
        imageUrl.value = URL.createObjectURL(res.data)
      } else {
        imageUrl.value = encoded
      }
    } else {
      const apiPath = encoded.replace(/^\/api\/v1/, '')
      const res = await api.get<Blob>(apiPath, { responseType: 'blob' })
      imageUrl.value = URL.createObjectURL(res.data)
    }
  } catch {
    error.value = '图片加载失败，请尝试下载查看'
  } finally {
    loading.value = false
  }
}

function revokeImageUrl() {
  if (imageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(imageUrl.value)
  }
  imageUrl.value = ''
}

async function downloadCurrent() {
  const item = current.value
  if (!item?.url) return
  try {
    const encoded = encodeUrlPath(item.url)
    let blob: Blob
    if (encoded.startsWith('http://') || encoded.startsWith('https://')) {
      if (encoded.startsWith(window.location.origin)) {
        const apiPath = new URL(encoded).pathname.replace(/^\/api\/v1/, '')
        const res = await api.get<Blob>(apiPath, { responseType: 'blob' })
        blob = res.data
      } else {
        const res = await fetch(encoded, { credentials: 'include' })
        blob = await res.blob()
      }
    } else {
      const apiPath = encoded.replace(/^\/api\/v1/, '')
      const res = await api.get<Blob>(apiPath, { responseType: 'blob' })
      blob = res.data
    }
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = item.name
    a.click()
    URL.revokeObjectURL(a.href)
  } catch {
    Message.error('下载失败，请稍后重试')
  }
}

watch(
  () => [visible.value, current.value?.url, current.value?.kind] as const,
  ([v, url, kind]) => {
    revokeImageUrl()
    error.value = ''
    loading.value = false
    resetZoom()
    maximized.value = false
    if (!v || !url) return
    if (!positioned.value) resetPosition()
    if (kind === 'image') void loadImagePreview(url)
  },
  { immediate: true },
)

watch(visible, (v) => {
  document.body.classList.toggle('att-preview-open', v)
  if (!v) {
    revokeImageUrl()
    positioned.value = false
    maximized.value = false
    resetZoom()
  }
})

onBeforeUnmount(() => {
  onDragEnd()
  revokeImageUrl()
  document.body.classList.remove('att-preview-open')
})
</script>

<style scoped>
.att-preview-layer {
  position: fixed;
  inset: 0;
  z-index: 2000;
  pointer-events: none;
  background: rgba(15, 23, 42, 0.12);
}

.att-preview-panel {
  position: fixed;
  top: 0;
  left: 0;
  width: min(960px, calc(100vw - 32px));
  max-height: min(92vh, 980px);
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  border: 1px solid #e5e6eb;
  background: #fff;
  box-shadow: 0 16px 48px rgba(15, 23, 42, 0.22);
  pointer-events: auto;
  overflow: hidden;
}

.att-preview-panel.is-maximized {
  inset: 12px;
  width: auto !important;
  max-height: none !important;
  height: auto;
  transform: none !important;
  border-radius: 10px;
}

.att-preview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid #f2f3f5;
  background: linear-gradient(180deg, #fafbfc 0%, #fff 100%);
  cursor: move;
  user-select: none;
  flex-shrink: 0;
}

.att-preview-panel.is-maximized .att-preview-head {
  cursor: default;
}

.att-preview-head-text {
  min-width: 0;
  flex: 1;
}

.att-preview-title {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
  line-height: 1.4;
  word-break: break-all;
}

.att-preview-field {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: #86909c;
}

.att-preview-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  cursor: default;
}

.att-zoom-label {
  min-width: 44px;
  font-variant-numeric: tabular-nums;
}

.att-preview-body {
  flex: 1;
  min-height: 360px;
  max-height: calc(92vh - 96px);
  overflow: auto;
  background: #eef0f3;
  padding: 16px;
  overscroll-behavior: contain;
}

.att-preview-panel.is-maximized .att-preview-body {
  max-height: calc(100vh - 120px);
  min-height: 480px;
}

.att-preview-zoom-stage {
  width: 100%;
  transition: transform 0.08s ease-out;
  will-change: transform;
}

.att-preview-state {
  padding: 48px 16px;
  text-align: center;
  color: #86909c;
  font-size: 14px;
}

.att-preview-state--error {
  color: #f53f3f;
}

.att-preview-image {
  display: block;
  width: 100%;
  max-width: 100%;
  height: auto;
  margin: 0 auto;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.att-preview-pdf {
  width: 100%;
}

.att-preview-pdf :deep(.wf-print-pdf-pages) {
  gap: 16px;
}

.att-preview-pdf :deep(.wf-print-att-img),
.att-preview-pdf :deep(.wf-print-pdf-embed) {
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.att-preview-pdf :deep(.wf-print-pdf-embed) {
  min-height: 70vh;
}

.att-preview-pdf :deep(.wf-print-pdf-embed-obj),
.att-preview-pdf :deep(.wf-print-pdf-embed-frame) {
  min-height: 68vh;
}

.att-preview-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 16px;
  text-align: center;
  background: #fff;
  border-radius: 8px;
}

.att-preview-fallback-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: #e8f3ff;
  color: #165dff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 12px;
}

.att-preview-fallback-name {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
  word-break: break-all;
}

.att-preview-fallback-meta {
  margin: 6px 0 0;
  font-size: 12px;
  color: #86909c;
}

.att-preview-fallback-note {
  margin: 12px 0 16px;
  font-size: 13px;
  color: #4e5969;
  line-height: 1.6;
}

.att-preview-foot {
  padding: 8px 12px;
  border-top: 1px solid #f2f3f5;
  font-size: 12px;
  color: #86909c;
  text-align: center;
  background: #fff;
  flex-shrink: 0;
}
</style>
