<template>
  <div class="wf-print-attachments">
    <section
      v-for="(item, index) in items"
      :key="item.id"
      class="wf-print-att-page"
      :class="[`wf-print-att-${item.kind}`]"
    >
      <div class="wf-print-att-sheet">
        <header class="wf-print-att-hd">
          <div class="wf-print-att-hd-top">
            <span class="wf-print-att-badge">{{ t('print.attachment_badge') }}</span>
            <span class="wf-print-att-index">{{ index + 1 }} / {{ items.length }}</span>
            <span class="wf-print-att-sep">·</span>
            <span class="wf-print-att-no">{{ meta.displayNo || meta.id }}</span>
          </div>
          <div class="wf-print-att-field">{{ item.fieldLabel }}</div>
          <div class="wf-print-att-name">{{ item.name }}</div>
        </header>

        <div class="wf-print-att-body">
          <img
            v-if="item.kind === 'image' && item.url"
            :src="item.url"
            :alt="item.name"
            class="wf-print-att-img"
          />
          <div v-else-if="item.kind === 'pdf' && item.url" class="wf-print-att-pdf">
            <PrintPdfPages :url="item.url" :name="item.name" />
          </div>
        </div>

        <footer class="wf-print-att-ft">
          <span class="wf-print-att-ft-link">
            {{ t('print.related_link') }} · {{ meta.definitionName || title }} · {{ meta.displayNo || meta.id }}
          </span>
          <span v-if="meta.printedAt" class="wf-print-att-ft-time">
            {{ formatPrintDateTime(meta.printedAt) }}
          </span>
        </footer>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { PrintAttachmentItem } from '@/composables/usePrintAttachments'
import { formatPrintDateTime } from '@/utils/printFormat'
import type { PrintSheetMeta } from '@/components/print/WorkflowPrintSheet.vue'
import PrintPdfPages from '@/components/print/PrintPdfPages.vue'

defineProps<{
  items: PrintAttachmentItem[]
  meta: PrintSheetMeta
  title?: string
}>()

const { t } = useI18n()
</script>

<style scoped>
.wf-print-att-page {
  page-break-before: always;
  break-before: page;
}

.wf-print-att-sheet {
  font-family: 'Noto Sans SC', 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #000;
  background: #fff;
  box-sizing: border-box;
  padding: var(--wf-print-margin, 12mm);
  max-width: 210mm;
  margin: 0 auto;
  min-height: calc(297mm - var(--wf-print-margin, 12mm) * 2);
  display: flex;
  flex-direction: column;
}

.wf-print-att-hd {
  border: 1px solid #000;
  border-bottom: none;
  padding: 10px 12px 8px;
}

.wf-print-att-hd-top {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 9pt;
  color: #222;
  margin-bottom: 6px;
}

.wf-print-att-badge {
  display: inline-block;
  padding: 1px 8px;
  border: 1px solid #000;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.wf-print-att-index {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.wf-print-att-sep {
  color: #666;
}

.wf-print-att-no {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}

.wf-print-att-field {
  font-weight: 700;
  font-size: 11pt;
  margin-bottom: 2px;
}

.wf-print-att-name {
  font-size: 9.5pt;
  color: #333;
  word-break: break-all;
}

.wf-print-att-body {
  flex: 1;
  border: 1px solid #000;
  min-height: 180mm;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
  padding: 4px;
  box-sizing: border-box;
  overflow: hidden;
}

.wf-print-att-img {
  display: block;
  width: 100%;
  max-width: 100%;
  height: auto;
  max-height: 175mm;
  object-fit: contain;
  object-position: top center;
}

.wf-print-att-pdf {
  width: 100%;
  max-height: none;
  align-self: stretch;
}

.wf-print-att-pdf :deep(.wf-print-pdf-pages) {
  width: 100%;
  align-items: stretch;
}

.wf-print-att-pdf :deep(.wf-print-pdf-page),
.wf-print-att-pdf :deep(.wf-print-att-img) {
  width: 100%;
  max-width: 100%;
}

.wf-print-att-pdf-obj,
.wf-print-att-pdf-frame {
  display: none;
}

.wf-print-att-ft {
  border: 1px solid #000;
  border-top: none;
  padding: 6px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 8.5pt;
  color: #333;
}

.wf-print-att-ft-link {
  font-weight: 500;
}

.wf-print-att-ft-time {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

@media print {
  .wf-print-att-sheet {
    padding: 0;
    max-width: none;
    margin: 0;
    min-height: auto;
  }

  .wf-print-att-page {
    page-break-before: always;
    break-before: page;
  }

  .wf-print-att-body {
    min-height: 0;
    page-break-inside: avoid;
    padding: 0;
  }

  .wf-print-att-img {
    width: 100%;
    max-width: 100%;
    max-height: 240mm;
    object-fit: contain;
    object-position: top center;
  }

  .wf-print-att-pdf {
    height: auto;
  }
}
</style>
