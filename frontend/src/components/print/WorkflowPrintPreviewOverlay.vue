<template>
  <Teleport to="body">
    <div v-if="visible" class="wf-print-preview-overlay">
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
        <div ref="rootRef" class="wf-print-mount wf-print-onscreen wf-print-preview-doc">
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
import { computed, ref } from 'vue'
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
import type { ProcessGraph } from '@/utils/workflowFlowGraph'
import type { WorkflowPrintPreviewTimelineRow } from '@/composables/useWorkflowPrintPreview'

const rootRef = ref<HTMLElement | null>(null)
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

defineExpose({ open, close, preparing, visible })
</script>

<style scoped>
.wf-print-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 1900;
  display: flex;
  flex-direction: column;
  background: #eef0f3;
}

.wf-print-preview-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #e5e6eb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.wf-print-preview-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
}

.wf-print-preview-actions {
  display: flex;
  gap: 8px;
}

.wf-print-skipped-banner {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 8px 16px 0;
  padding: 10px 14px;
  background: #fff7e8;
  border: 1px solid #ffcf8b;
  border-radius: 4px;
}

.wf-print-skipped-icon {
  flex-shrink: 0;
  margin-top: 2px;
  font-size: 16px;
  color: #ff7d00;
}

.wf-print-skipped-text {
  min-width: 0;
}

.wf-print-skipped-title {
  margin: 0 0 4px;
  font-size: 13px;
  font-weight: 600;
  color: #1d2129;
}

.wf-print-skipped-desc {
  margin: 0 0 6px;
  font-size: 12px;
  color: #4e5969;
  line-height: 1.5;
}

.wf-print-skipped-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #1d2129;
  line-height: 1.6;
}

.wf-print-preview-scroll {
  flex: 1;
  overflow: auto;
  padding: 16px;
  -webkit-overflow-scrolling: touch;
}

.wf-print-preview-doc {
  position: static !important;
  left: auto !important;
  top: auto !important;
  width: 100% !important;
  max-width: 210mm;
  margin: 0 auto 24px;
  opacity: 1 !important;
  pointer-events: auto !important;
  overflow: visible !important;
  height: auto !important;
}
</style>
