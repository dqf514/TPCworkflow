<template>
  <div
    class="wf-print-root wf-print-sheet"
    :class="[`page-${pageSize}`, `orient-${orientation}`]"
    :style="pageStyle"
  >
    <!-- 单据头信息表为纯版式表格（label/value 排布），标记为 presentation 避免读屏误读为数据表 -->
    <table class="wf-pt wf-pt-title" role="presentation">
      <caption class="a11y-table-caption">{{ title }}</caption>
      <colgroup>
        <col class="wf-pt-col-label" />
        <col class="wf-pt-col-value" />
        <col class="wf-pt-col-label" />
        <col class="wf-pt-col-value" />
      </colgroup>
      <tbody>
        <tr v-if="linkLabel">
          <td colspan="4" class="wf-pt-related-banner">【{{ linkLabel }}】</td>
        </tr>
        <tr>
          <td colspan="4" class="wf-pt-doc-title">{{ title }}</td>
        </tr>
        <tr>
          <th class="wf-pt-th">{{ t('print.org') }}</th>
          <td class="wf-pt-td">{{ meta.companyName || '—' }}</td>
          <th class="wf-pt-th">{{ t('print.approval_no') }}</th>
          <td class="wf-pt-td wf-pt-mono">{{ meta.displayNo || meta.id || '—' }}</td>
        </tr>
        <tr>
          <th class="wf-pt-th">{{ t('print.applicant') }}</th>
          <td class="wf-pt-td">{{ meta.initiatorName || '—' }}</td>
          <th class="wf-pt-th">{{ t('print.department') }}</th>
          <td class="wf-pt-td">{{ meta.departmentPath || meta.departmentName || '—' }}</td>
        </tr>
        <tr>
          <th class="wf-pt-th">{{ t('print.submitted_at') }}</th>
          <td class="wf-pt-td">{{ formatPrintDateTime(meta.startedAt) }}</td>
          <th class="wf-pt-th">{{ t('print.status') }}</th>
          <td class="wf-pt-td">{{ instanceStatusLabel(meta.status) }}</td>
        </tr>
        <tr v-if="schema.description && showDescription">
          <th class="wf-pt-th">{{ t('print.description') }}</th>
          <td colspan="3" class="wf-pt-td">{{ schema.description }}</td>
        </tr>
      </tbody>
    </table>

    <template v-for="block in sections" :key="block.id">
      <!-- 分区信息表同样是纯版式表格 -->
      <table class="wf-pt wf-pt-section" role="presentation">
        <caption class="a11y-table-caption">{{ block.title }}</caption>
        <colgroup>
          <col class="wf-pt-col-label" />
          <col class="wf-pt-col-value" />
          <col class="wf-pt-col-label" />
          <col class="wf-pt-col-value" />
        </colgroup>
        <tbody>
          <tr>
            <td colspan="4" class="wf-pt-section-head">{{ block.title }}</td>
          </tr>
          <template
            v-for="(pair, pi) in pairPrintRows(block.rows)"
            :key="pair.left?.key || pair.right?.key || `pair-${pi}`"
          >
            <tr v-if="pair.left?.fullWidth" class="wf-pt-row-full">
              <th class="wf-pt-th">{{ pair.left.label }}</th>
              <td
                colspan="3"
                class="wf-pt-td wf-pt-pre"
                :class="{ 'wf-pt-td-money': pair.left.alignRight }"
              >
                {{ pair.left.value }}
              </td>
            </tr>
            <tr v-else>
              <th class="wf-pt-th">{{ pair.left?.label }}</th>
              <td class="wf-pt-td wf-pt-pre" :class="{ 'wf-pt-td-money': pair.left?.alignRight }">
                {{ pair.left?.value }}
              </td>
              <template v-if="pair.right">
                <th class="wf-pt-th">{{ pair.right.label }}</th>
                <td class="wf-pt-td wf-pt-pre" :class="{ 'wf-pt-td-money': pair.right.alignRight }">
                  {{ pair.right.value }}
                </td>
              </template>
              <template v-else>
                <th class="wf-pt-th wf-pt-empty"></th>
                <td class="wf-pt-td wf-pt-empty"></td>
              </template>
            </tr>
          </template>
        </tbody>
      </table>

      <div v-for="tb in block.textBlocks" :key="tb.id" class="wf-pt-text-block">
        <div v-if="tb.label" class="wf-pt-text-label">{{ tb.label }}</div>
        <div class="wf-pt-text-body">{{ tb.content }}</div>
      </div>

      <table
        v-for="dt in block.details"
        :key="dt.id"
        class="wf-pt wf-pt-detail"
      >
        <caption class="wf-pt-detail-caption">{{ dt.title }}</caption>
        <thead>
          <tr>
            <th v-for="col in dt.columns" :key="col.key" scope="col" class="wf-pt-th">{{ col.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!dt.rows.length">
            <td :colspan="dt.columns.length || 1" class="wf-pt-td wf-pt-muted">{{ t('print.no_detail') }}</td>
          </tr>
          <tr v-for="(row, ri) in dt.rows" :key="dt.rowKeys?.[ri] ?? ri">
            <td
              v-for="col in dt.columns"
              :key="col.key"
              class="wf-pt-td wf-pt-pre"
              :class="{ 'wf-pt-td-money': dt.moneyColumnKeys?.includes(col.key) }"
            >
              {{ row[col.key] }}
            </td>
          </tr>
          <tr v-for="(sum, si) in dt.summaryRows || []" :key="sum.key || sum.label || `s-${si}`" class="wf-pt-summary-row">
            <td
              :colspan="dt.columns.length || 1"
              class="wf-pt-td wf-pt-pre"
              :class="{ 'wf-pt-td-money': sum.alignRight }"
            >
              <span class="wf-pt-strong">{{ sum.label }}：</span>{{ sum.value }}
            </td>
          </tr>
        </tbody>
      </table>
    </template>

    <table v-if="showHistory && timeline.length" class="wf-pt wf-pt-approval">
      <colgroup>
        <col class="wf-pt-col-node" />
        <col class="wf-pt-col-actor" />
        <col class="wf-pt-col-record" />
      </colgroup>
      <thead>
        <tr>
          <td colspan="3" class="wf-pt-section-head">
            {{ t('print.approval_flow') }} — {{ instanceStatusLabel(meta.status) }}
          </td>
        </tr>
        <tr class="wf-pt-col-head">
          <th class="wf-pt-th wf-pt-th-node">{{ t('print.approval_node') }}</th>
          <th class="wf-pt-th wf-pt-th-actor">{{ t('print.handler') }}</th>
          <th class="wf-pt-th wf-pt-th-record">{{ t('print.operation_record') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in timeline" :key="item.id">
          <td class="wf-pt-td wf-pt-td-node">{{ timelineNodeLabel(item) }}</td>
          <td class="wf-pt-td wf-pt-td-actor">
            <div class="wf-pt-actor">{{ item.actor_name || '—' }}</div>
            <img
              v-if="signatureSrc(item)"
              :src="signatureSrc(item)!"
              :alt="t('print.signature_alt')"
              class="wf-pt-sign"
            />
          </td>
          <td class="wf-pt-td wf-pt-td-record">
            <span class="wf-pt-record-text">{{ timelineOperationText(item) }}</span>
            <span class="wf-pt-time-inline">{{ formatPrintDateTime(item.created_at) }}</span>
          </td>
        </tr>
      </tbody>
    </table>

    <footer class="wf-pt-footer">
      <div class="wf-pt-footer-line">
        <span class="wf-pt-footer-tag">{{ meta.displayNo || meta.id }} · {{ footerTagText }}</span>
        <span v-if="relatedCount" class="wf-pt-footer-att">{{ t('print.related_attached', { count: relatedCount }) }}</span>
        <span v-if="attachmentCount" class="wf-pt-footer-att">{{ t('print.attachments_attached', { count: attachmentCount }) }}</span>
        <span class="wf-pt-footer-right">
          <span>{{ t('print.printed_at') }}：{{ formatPrintDateTime(meta.printedAt) }}</span>
          <span v-if="meta.printerName" class="wf-pt-footer-printer">{{ t('print.printed_by') }}：{{ meta.printerName }}</span>
        </span>
      </div>
      <div class="wf-pt-footer-note">{{ t('print.footer_note') }}</div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { FormSchema } from '@/types/form'
import {
  buildPrintSections,
  pairPrintRows,
  type PrintSectionBlock,
} from '@/composables/usePrintFormData'
import {
  formatPrintDateTime,
  instanceStatusLabel,
  resolveWorkflowNodeTitle,
  signatureImageSrc,
  timelineActionLabel,
  timelineOperationText,
} from '@/utils/printFormat'
import type { ProcessGraph } from '@/utils/workflowFlowGraph'

export interface PrintSheetMeta {
  id: number
  displayNo?: string
  status: string
  definitionName?: string
  initiatorName?: string
  departmentName?: string
  departmentPath?: string
  companyName?: string
  startedAt?: string | null
  printedAt?: string
  printerName?: string
}

export interface PrintTimelineItem {
  id: number
  action: string
  comment?: string
  created_at?: string | null
  actor_name?: string
  node_id?: string
  node_name?: string
  signature_path?: string
  signature_data?: string
}

const props = withDefaults(
  defineProps<{
    schema: FormSchema
    modelValue: Record<string, unknown>
    meta: PrintSheetMeta
    timeline?: PrintTimelineItem[]
    sections?: PrintSectionBlock[]
    processGraph?: ProcessGraph | null
    userOpts?: { label: string; value: number }[]
    deptOpts?: { label: string; value: number }[]
    attachmentCount?: number
    /** 页脚流程类型标记，如「主流程」「关联申请单」 */
    footerTag?: string
    /** 关联申请单在正文前的说明标签 */
    linkLabel?: string
    /** 另附的关联申请单份数（仅主流程页脚展示） */
    relatedCount?: number
  }>(),
  {
    timeline: () => [],
    userOpts: () => [],
    deptOpts: () => [],
    attachmentCount: 0,
    footerTag: '',
    relatedCount: 0,
  },
)

const { t } = useI18n()

const title = computed(() => props.schema.title || props.meta.definitionName || t('print.default_title'))
const footerTagText = computed(() => props.footerTag || t('print.main_flow'))
const showDescription = computed(() => props.schema.print?.showDescription === true)
const showHistory = computed(() => props.schema.print?.showApprovalHistory !== false)
const pageSize = computed(() => (props.schema.print?.pageSize || 'A4').toLowerCase())
const orientation = computed(() => props.schema.print?.orientation || 'portrait')
const marginMm = computed(() => props.schema.print?.marginMm ?? 12)

// 页边距写在打印稿自身作用域；纸张尺寸/方向/页面宽高由打印容器（.wf-print-mount）统一提供
const pageStyle = computed(() => ({
  '--wf-print-margin': `${marginMm.value}mm`,
}))

const sections = computed(() => props.sections || [])

function timelineNodeLabel(item: PrintTimelineItem) {
  if (item.action === 'submit') return t('print.submit_action')
  if (item.action === 'cc') return t('print.cc')
  const configured = (item.node_name || '').trim()
  if (configured) return configured
  if (item.node_id) return resolveWorkflowNodeTitle(item.node_id, props.processGraph)
  return timelineActionLabel(item.action)
}

function signatureSrc(item: PrintTimelineItem) {
  return signatureImageSrc(item)
}

defineExpose({
  async prepare() {
    return buildPrintSections(
      props.schema,
      props.modelValue,
      props.userOpts,
      props.deptOpts,
    )
  },
})
</script>

<style scoped>
.wf-print-sheet {
  font-family: 'Noto Sans SC', 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #000;
  background: #fff;
  box-sizing: border-box;
  padding: var(--wf-print-margin, 12mm);
  max-width: var(--wf-print-page-width, 210mm);
  margin: 0 auto;
}

.wf-pt {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  margin: 0 0 var(--app-space-10);
}

.wf-pt col.wf-pt-col-label {
  width: 12%;
}

.wf-pt col.wf-pt-col-value {
  width: 38%;
}

.wf-pt th,
.wf-pt td {
  border: 1px solid #000;
  padding: 5px var(--app-space-8);
  vertical-align: top;
  word-break: break-word;
}

.wf-pt-related-banner {
  text-align: center;
  font-size: 10pt;
  font-weight: 600;
  color: #333;
  padding: var(--app-space-6) var(--app-space-8) !important;
  border: 1px solid #000 !important;
  border-bottom: none !important;
  background: #f7f7f7 !important;
}

.wf-pt-doc-title {
  text-align: center;
  font-size: 16pt;
  font-weight: 700;
  letter-spacing: 0.12em;
  padding: var(--app-space-10) var(--app-space-8) var(--app-space-12) !important;
  border: 1px solid #000 !important;
}

.wf-pt-section-head {
  text-align: center;
  font-weight: 700;
  font-size: 11pt;
  background: #fff !important;
  padding: var(--app-space-6) var(--app-space-8) !important;
}

.wf-pt-col-head .wf-pt-th {
  text-align: center;
  font-weight: 700;
  background: #fff !important;
}

.wf-pt-th {
  font-weight: 600;
  text-align: left;
  background: #fff !important;
  color: #000 !important;
}

.wf-pt-td {
  background: #fff !important;
  color: #000 !important;
}

.wf-pt-row-full .wf-pt-td {
  width: auto;
}

.wf-pt-empty {
  border-color: #000 !important;
}

.wf-pt-mono {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}

.wf-pt-pre {
  white-space: pre-wrap;
}

.wf-pt-td-money {
  text-align: right !important;
  font-variant-numeric: tabular-nums;
}

.wf-pt-strong {
  font-weight: 700;
}

.wf-pt-muted {
  color: #333;
  text-align: center;
}

.wf-pt-detail {
  margin-bottom: var(--app-space-12);
}

.wf-pt-detail-caption {
  caption-side: top;
  text-align: left;
  font-weight: 700;
  font-size: 10.5pt;
  padding: var(--app-space-4) 0 var(--app-space-6);
}

.wf-pt-detail .wf-pt-th {
  width: auto;
  text-align: center;
  font-size: 9.5pt;
}

.wf-pt-detail .wf-pt-td {
  width: auto;
  font-size: 9.5pt;
}

.wf-pt-summary-row .wf-pt-th {
  text-align: right;
}

.wf-pt-text-block {
  border: 1px solid #000;
  margin: 0 0 var(--app-space-10);
  padding: var(--app-space-6) var(--app-space-8);
  page-break-inside: avoid;
}

.wf-pt-text-label {
  font-weight: 600;
  margin-bottom: var(--app-space-4);
}

.wf-pt-text-body {
  white-space: pre-wrap;
}

.wf-pt-actor {
  margin-bottom: var(--app-space-4);
}

.wf-pt-sign {
  display: block;
  max-height: 42px;
  max-width: 120px;
  object-fit: contain;
  filter: grayscale(100%);
}

.wf-pt-time {
  margin-top: var(--app-space-4);
  font-size: 9pt;
  color: #222;
}

.wf-pt-approval col.wf-pt-col-node {
  width: 14%;
}

.wf-pt-approval col.wf-pt-col-actor {
  width: 10%;
}

.wf-pt-approval col.wf-pt-col-record {
  width: 76%;
}

.wf-pt-approval .wf-pt-th-node,
.wf-pt-approval .wf-pt-td-node {
  width: 14%;
  font-size: 9pt;
  padding: var(--app-space-3) var(--app-space-6);
  word-break: keep-all;
  white-space: nowrap;
}

.wf-pt-approval .wf-pt-th-actor,
.wf-pt-approval .wf-pt-td-actor {
  width: 10%;
  font-size: 9pt;
  padding: var(--app-space-3) var(--app-space-4);
}

.wf-pt-approval .wf-pt-th-record,
.wf-pt-approval .wf-pt-td-record {
  width: 76%;
  padding: var(--app-space-3) var(--app-space-6);
}

.wf-pt-approval .wf-pt-td-record {
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.wf-pt-record-text {
  margin-right: 0.75em;
}

.wf-pt-time-inline {
  font-size: 9pt;
  color: #222;
  white-space: nowrap;
}

.wf-pt-approval .wf-pt-actor {
  margin-bottom: var(--app-space-2);
}

.wf-pt-footer {
  margin-top: var(--app-space-14);
  padding-top: var(--app-space-8);
  border-top: 1px solid #000;
  font-size: 9pt;
  page-break-inside: avoid;
}

.wf-pt-footer-line {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--app-space-12);
  flex-wrap: wrap;
}

.wf-pt-footer-tag {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.wf-pt-footer-att {
  color: #333;
}

.wf-pt-footer-right {
  margin-left: auto;
  display: flex;
  flex-wrap: wrap;
  gap: var(--app-space-12);
}

.wf-pt-footer-printer {
  white-space: nowrap;
}

.wf-pt-footer-note {
  margin-top: var(--app-space-6);
  color: #333;
}

@media print {
  .wf-print-sheet {
    padding: 0;
    max-width: none;
    margin: 0;
  }

  .wf-pt-title {
    page-break-after: avoid;
  }

  .wf-pt-section {
    page-break-inside: avoid;
  }

  /* 审批记录表允许跨页，<thead> 会在每页自动重复表头 */
  .wf-pt-approval {
    page-break-inside: auto;
  }

  .wf-pt-approval tr {
    page-break-inside: avoid;
  }

  .wf-pt-detail {
    page-break-inside: auto;
  }
}

.page-a4.orient-landscape {
  max-width: 297mm;
}

@media print {
  .page-a4.orient-landscape {
    max-width: none;
  }
}
</style>
