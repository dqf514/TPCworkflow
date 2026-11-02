<template>
  <Teleport to="body">
    <div
      v-if="visible"
      ref="overlayRef"
      class="wf-print-preview-overlay"
      role="dialog"
      aria-modal="true"
      :aria-label="overlayTitle"
    >
      <header class="wf-print-preview-head no-print">
        <span class="wf-print-preview-title">{{ overlayTitle }}</span>
        <div class="wf-print-preview-actions">
          <a-button size="small" @click="close">{{ t('print.close') }}</a-button>
          <a-button size="small" type="primary" :disabled="!assetsReady" @click="triggerBrowserPrint">
            {{ assetsReady ? t('print.print_btn') : t('print.loading') }}
          </a-button>
        </div>
      </header>
      <div v-if="printSkippedAttachments.length" class="wf-print-skipped-banner no-print">
        <icon-info-circle class="wf-print-skipped-icon" />
        <div class="wf-print-skipped-text">
          <p class="wf-print-skipped-title">{{ t('print.skipped_attachments_title') }}</p>
          <p class="wf-print-skipped-desc">{{ t('print.skipped_attachments_desc') }}</p>
          <ul class="wf-print-skipped-list">
            <li v-for="item in printSkippedAttachments" :key="item.id">{{ item.name }}</li>
          </ul>
        </div>
      </div>
      <div class="wf-print-preview-scroll">
        <div
          ref="rootRef"
          class="wf-print-mount wf-print-onscreen wf-print-preview-doc"
          :style="mountStyle"
        >
          <div v-if="ready" class="wf-print-document">
            <ConfigurablePrintSheet
              v-if="useCustomPrintTemplate && printTemplateSchema"
              :template-schema="printTemplateSchema"
              :model-value="formValues"
            />
            <template v-else-if="formSchema">
              <WorkflowPrintSheet
                :schema="formSchema"
                :model-value="formValues"
                :meta="printMeta"
                :timeline="timeline"
                :process-graph="processGraph"
                :sections="printSections"
                :user-opts="userOpts"
                :dept-opts="deptOpts"
                :attachment-count="printMainAttachments.length"
                :related-count="printRelatedBundles.length"
              />
              <WorkflowPrintAttachmentPages
                v-if="printMainAttachments.length"
                :items="printMainAttachments"
                :meta="printMeta"
                :title="definitionName"
              />
              <template v-for="rel in printRelatedBundles" :key="rel.key">
                <div class="wf-print-related-block">
                  <WorkflowPrintSheet
                    :schema="rel.schema"
                    :model-value="rel.formValues"
                    :meta="rel.meta"
                    :timeline="rel.timeline"
                    :process-graph="rel.processGraph"
                    :sections="rel.sections"
                    :user-opts="userOpts"
                    :dept-opts="deptOpts"
                    :attachment-count="rel.attachments.length"
                    :footer-tag="t('print.related_request')"
                    :link-label="rel.linkLabel"
                  />
                  <WorkflowPrintAttachmentPages
                    v-if="rel.attachments.length"
                    :items="rel.attachments"
                    :meta="rel.meta"
                    :title="rel.meta.definitionName"
                  />
                </div>
              </template>
            </template>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { IconInfoCircle } from '@arco-design/web-vue/es/icon'
import { useI18n } from 'vue-i18n'
import ConfigurablePrintSheet from '@/components/print/ConfigurablePrintSheet.vue'
import WorkflowPrintAttachmentPages from '@/components/print/WorkflowPrintAttachmentPages.vue'
import WorkflowPrintSheet from '@/components/print/WorkflowPrintSheet.vue'
import {
  useWorkflowPrintPreview,
  type WorkflowPrintPreviewInput,
} from '@/composables/useWorkflowPrintPreview'
import type { FormSchema } from '@/types/form'
import { printPageVars } from '@/utils/printPageSetup'
import type { ProcessGraph } from '@/utils/workflowFlowGraph'
import type { WorkflowPrintPreviewTimelineRow } from '@/composables/useWorkflowPrintPreview'

const rootRef = ref<HTMLElement | null>(null)
const overlayRef = ref<HTMLElement | null>(null)
const preview = useWorkflowPrintPreview(rootRef)
const { t } = useI18n()

const formSchema = ref<FormSchema | null>(null)
const formValues = ref<Record<string, unknown>>({})
const printMeta = ref<Record<string, unknown>>({})
const timeline = ref<WorkflowPrintPreviewTimelineRow[]>([])
const processGraph = ref<ProcessGraph | undefined>()
const definitionName = ref('')

const visible = preview.visible
const preparing = preview.preparing
const ready = preview.ready
const assetsReady = preview.assetsReady
const printSections = preview.printSections
const printMainAttachments = preview.printMainAttachments
const printSkippedAttachments = preview.printSkippedAttachments
const printRelatedBundles = preview.printRelatedBundles
const printTemplateSchema = preview.printTemplateSchema
const useCustomPrintTemplate = preview.useCustomPrintTemplate
const userOpts = preview.userOpts
const deptOpts = preview.deptOpts

const overlayTitle = computed(
  () => definitionName.value || (printMeta.value.definitionName as string) || t('print.preview_title'),
)

/**
 * 打印纸张设置：写在打印容器（.wf-print-mount）上，
 * 主打印稿、附件页、关联申请单页共享同一份设置，@page 由 printElement() 动态注入。
 */
const pageSetup = computed(() => {
  if (useCustomPrintTemplate.value && printTemplateSchema.value?.page) {
    const p = printTemplateSchema.value.page
    return { size: p.size, orientation: p.orientation, marginMm: p.marginMm }
  }
  const p = formSchema.value?.print
  return { size: p?.pageSize, orientation: p?.orientation, marginMm: p?.marginMm }
})

const mountStyle = computed(() => printPageVars(pageSetup.value))

async function open(payload: WorkflowPrintPreviewInput) {
  formSchema.value = payload.formSchema
  formValues.value = payload.formValues
  printMeta.value = payload.meta
  timeline.value = payload.timeline || []
  processGraph.value = payload.processGraph
  definitionName.value = payload.definitionName || payload.meta.definitionName || ''
  await preview.open(payload)
}

function close() {
  preview.close()
}

function triggerBrowserPrint() {
  preview.triggerBrowserPrint()
}

/** 遮罩层内可聚焦元素，用于焦点陷阱 */
const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  'a[href]',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

/** Esc 关闭 + Tab 焦点循环（弹层为模态，需把焦点限制在层内） */
function onOverlayKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.preventDefault()
    e.stopPropagation()
    close()
    return
  }
  if (e.key !== 'Tab') return
  const root = overlayRef.value
  if (!root) return
  const focusables = Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (el) => el.offsetParent !== null || el === document.activeElement,
  )
  if (!focusables.length) return
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  const active = document.activeElement as HTMLElement | null
  if (!active || !root.contains(active)) {
    e.preventDefault()
    first.focus()
    return
  }
  if (e.shiftKey && active === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && active === last) {
    e.preventDefault()
    first.focus()
  }
}

watch(visible, (v) => {
  if (v) {
    document.addEventListener('keydown', onOverlayKeydown, true)
    // 打开后把焦点移入弹层，读屏用户能直接进入内容
    void nextTick(() => {
      overlayRef.value?.querySelector<HTMLElement>('button')?.focus()
    })
  } else {
    document.removeEventListener('keydown', onOverlayKeydown, true)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onOverlayKeydown, true)
})

defineExpose({ open, close, preparing, visible })
</script>

<style scoped>
.wf-print-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 1900;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}

.wf-print-preview-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--app-space-md);
  padding: var(--app-space-10) var(--app-space-lg);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
}

.wf-print-preview-title {
  font-size: var(--app-font-md);
  font-weight: 600;
  color: var(--text);
}

.wf-print-preview-actions {
  display: flex;
  gap: var(--app-space-sm);
}

.wf-print-skipped-banner {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  gap: var(--app-space-10);
  margin: var(--app-space-sm) var(--app-space-lg) 0;
  padding: var(--app-space-10) var(--app-space-14);
  background: var(--warning-soft);
  border: 1px solid color-mix(in srgb, var(--warning) 45%, transparent);
  border-radius: var(--radius-sm);
}

.wf-print-skipped-icon {
  flex-shrink: 0;
  margin-top: var(--app-space-2);
  font-size: var(--app-font-lg);
  color: var(--warning);
}

.wf-print-skipped-text {
  min-width: 0;
}

.wf-print-skipped-title {
  margin: 0 0 var(--app-space-xs);
  font-size: var(--app-font-sm);
  font-weight: 600;
  color: var(--text);
}

.wf-print-skipped-desc {
  margin: 0 0 var(--app-space-6);
  font-size: var(--app-font-xs);
  color: var(--text-secondary);
  line-height: 1.5;
}

.wf-print-skipped-list {
  margin: 0;
  padding-left: var(--app-space-18);
  font-size: var(--app-font-xs);
  color: var(--text);
  line-height: 1.6;
}

.wf-print-preview-scroll {
  flex: 1;
  overflow: auto;
  padding: var(--app-space-lg);
  -webkit-overflow-scrolling: touch;
}

.wf-print-preview-doc {
  position: static !important;
  left: auto !important;
  top: auto !important;
  width: 100% !important;
  max-width: 210mm;
  margin: 0 auto var(--app-space-xl);
  opacity: 1 !important;
  pointer-events: auto !important;
  overflow: visible !important;
  height: auto !important;
}

/* 窄屏适配：手机端放开纸张宽度限制并压缩外边距，避免出现大片空白 */
@media (max-width: 768px) {
  .wf-print-preview-scroll {
    padding: var(--app-space-sm);
  }

  .wf-print-preview-doc {
    max-width: 100%;
    margin-bottom: var(--app-space-md);
  }

  .wf-print-preview-head {
    flex-wrap: wrap;
    gap: var(--app-space-xs);
    padding: var(--app-space-8) var(--app-space-md);
  }

  .wf-print-skipped-banner {
    margin: var(--app-space-xs) var(--app-space-md) 0;
  }
}
</style>
