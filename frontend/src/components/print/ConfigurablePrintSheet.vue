<template>
  <div
    class="wf-print-root cps-root"
    :class="[`page-${pageSize}`, `orient-${orientation}`, `layout-${layout}`]"
    :style="rootStyle"
  >
    <div class="cps-header">
      <div class="cps-header-left">
        <img
          v-if="logoUrl"
          class="cps-logo"
          :src="logoUrl"
          alt="Logo"
          :style="{ width: `${logoWidthMm}mm` }"
        />
        <slot v-else name="logo-fallback" />
      </div>
      <div v-if="blockMap.company_info" class="cps-header-right">
        <div class="cps-richtext" :style="{ textAlign: blockMap.company_info.align || 'right' }">
          {{ blockMap.company_info.content }}
        </div>
      </div>
    </div>

    <div class="cps-meta-row">
      <div v-if="blockMap.to_block" class="cps-meta-left">
        <div v-for="(item, i) in blockMap.to_block.items || []" :key="i" class="cps-field-line">
          <span class="cps-label">{{ item.label }}</span>
          <span class="cps-value">
            {{ resolveItem(item).value }}
            <div v-if="resolveItem(item).sub" class="cps-sub">{{ resolveItem(item).sub }}</div>
          </span>
        </div>
      </div>
      <div v-if="blockMap.doc_meta" class="cps-meta-right">
        <div v-for="(item, i) in blockMap.doc_meta.items || []" :key="i" class="cps-field-line cps-field-line-right">
          <span class="cps-label">{{ item.label }}</span>
          <span class="cps-value">{{ resolveItem(item).value }}</span>
        </div>
      </div>
    </div>

    <div v-if="blockMap.particulars_table" class="cps-table-wrap">
      <div class="cps-table-head">
        <span class="cps-table-title">{{ blockMap.particulars_table.title || 'PARTICULARS' }}</span>
        <span class="cps-table-currency">{{ currencyDisplay }}</span>
      </div>
      <table class="cps-table">
        <thead>
          <tr>
            <th
              v-for="col in blockMap.particulars_table.columns || []"
              :key="col.key"
              :style="{ width: col.width, textAlign: col.align || 'left' }"
            >
              {{ col.header }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ri) in detailRows" :key="ri">
            <td
              v-for="col in blockMap.particulars_table.columns || []"
              :key="col.key"
              :style="{ textAlign: col.align || 'left' }"
              :class="{ 'cps-money': col.format === 'money_plain' }"
            >
              {{ cellValue(row, col) }}
            </td>
          </tr>
          <tr v-if="blockMap.particulars_table.showTotal" class="cps-total-row">
            <td :colspan="totalColspan"></td>
            <td class="cps-total-label">{{ blockMap.particulars_table.totalLabel || 'Total' }}</td>
            <td class="cps-money cps-total-value">{{ formatPrintMoney(detailTotal, currency) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="blockMap.seal_sign" class="cps-signature">
      <img
        v-if="blockMap.seal_sign.showSeal && sealUrl"
        class="cps-seal"
        :src="sealUrl"
        alt="Seal"
        :style="{ width: `${sealWidthMm}mm`, opacity: sealOpacity }"
      />
      <div class="cps-sign-lines">
        <div v-for="(line, i) in blockMap.seal_sign.lines || []" :key="i">{{ line }}</div>
      </div>
    </div>

    <div v-if="blockMap.payment_advice" class="cps-footer" :class="{ 'has-divider': blockMap.payment_advice.showDivider }">
      <div class="cps-kv-col">
        <div v-for="(item, i) in blockMap.payment_advice.left || []" :key="`l-${i}`" class="cps-kv-line">
          <span class="cps-kv-label">{{ item.label }}</span>
          <span class="cps-kv-value">{{ resolveItem(item).value }}</span>
        </div>
      </div>
      <div class="cps-kv-col">
        <div v-for="(item, i) in blockMap.payment_advice.right || []" :key="`r-${i}`" class="cps-kv-line">
          <span class="cps-kv-label">{{ item.label }}</span>
          <span class="cps-kv-value">{{ resolveItem(item).value }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  computeDetailTotal,
  formatPrintFieldValue,
  formatPrintMoney,
  resolveAssetUrl,
  resolveFieldItemText,
  resolveTemplateCurrency,
} from '@/composables/usePrintTemplateFormat'
import type { PrintDetailColumn, PrintFieldItem, PrintTemplateSchema } from '@/types/printTemplate'

const props = defineProps<{
  templateSchema: PrintTemplateSchema
  modelValue: Record<string, unknown>
}>()

const pageSize = computed(() => (props.templateSchema.page?.size || 'A4').toLowerCase())
const orientation = computed(() => props.templateSchema.page?.orientation || 'portrait')
const layout = computed(() => props.templateSchema.layout || 'debit_note_v1')
const marginMm = computed(() => props.templateSchema.page?.marginMm ?? 10)

const currency = computed(() => resolveTemplateCurrency(props.templateSchema, props.modelValue))

const currencyDisplay = computed(() => {
  const b = blockMap.value.particulars_table
  if (b?.currencyLabel) return b.currencyLabel
  return `${currency.value} ($)`
})

const rootStyle = computed(() => ({
  '--cps-margin': `${marginMm.value}mm`,
  '--cps-font': props.templateSchema.styles?.fontFamily || 'Arial, Helvetica, sans-serif',
  '--cps-font-size': `${props.templateSchema.styles?.baseFontSizePt || 10}pt`,
  '--cps-border': props.templateSchema.styles?.tableBorderColor || '#333',
}))

const blockMap = computed(() => props.templateSchema.blocks || {})

const logoUrl = computed(() => resolveAssetUrl(props.templateSchema.assets?.logo?.url))
const logoWidthMm = computed(() => props.templateSchema.assets?.logo?.widthMm || 42)
const sealUrl = computed(() => resolveAssetUrl(props.templateSchema.assets?.seal?.url))
const sealWidthMm = computed(() => props.templateSchema.assets?.seal?.widthMm || 36)
const sealOpacity = computed(() => props.templateSchema.assets?.seal?.opacity ?? 0.95)

const detailRows = computed(() => {
  const key = blockMap.value.particulars_table?.fieldKey || 'particulars'
  const rows = props.modelValue[key]
  return Array.isArray(rows) ? rows : []
})

const detailTotal = computed(() => {
  const b = blockMap.value.particulars_table
  if (!b) return 0
  return computeDetailTotal(b, props.modelValue)
})

const totalColspan = computed(() => {
  const n = blockMap.value.particulars_table?.columns?.length || 1
  return Math.max(1, n - 2)
})

function resolveItem(item: PrintFieldItem) {
  return resolveFieldItemText(item, props.modelValue, currency.value)
}

function cellValue(row: unknown, col: PrintDetailColumn) {
  if (!row || typeof row !== 'object') return '—'
  const val = (row as Record<string, unknown>)[col.key]
  return formatPrintFieldValue(val, col.format, currency.value)
}
</script>

<style scoped>
.cps-root {
  box-sizing: border-box;
  width: 100%;
  padding: var(--cps-margin, 10mm);
  font-family: var(--cps-font);
  font-size: var(--cps-font-size);
  color: #111;
  background: #fff;
}

.cps-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12mm;
  margin-bottom: 8mm;
}

.cps-header-right {
  flex: 1;
  text-align: right;
}

.cps-richtext {
  white-space: pre-line;
  line-height: 1.45;
  font-size: 9.5pt;
}

.cps-logo {
  height: auto;
  max-height: 18mm;
  object-fit: contain;
}

.cps-meta-row {
  display: flex;
  justify-content: space-between;
  gap: 10mm;
  margin-bottom: 6mm;
}

.cps-meta-left,
.cps-meta-right {
  flex: 1;
}

.cps-meta-right {
  text-align: right;
}

.cps-field-line {
  display: flex;
  gap: 4mm;
  margin-bottom: 2mm;
  line-height: 1.4;
}

.cps-field-line-right {
  justify-content: flex-end;
}

.cps-label {
  font-weight: 600;
  min-width: 18mm;
}

.cps-sub {
  font-size: 9pt;
  color: #333;
}

.cps-table-wrap {
  margin-bottom: 8mm;
}

.cps-table-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 2mm;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.cps-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.cps-table th,
.cps-table td {
  border: 1px solid var(--cps-border);
  padding: 2mm 2.5mm;
  vertical-align: top;
  word-break: break-word;
}

.cps-table th {
  font-weight: 700;
  background: #fafafa;
}

.cps-money {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.cps-total-row td {
  border-top: 2px solid var(--cps-border);
  font-weight: 700;
}

.cps-total-label {
  text-align: right;
}

.cps-total-value {
  text-align: right;
}

.cps-signature {
  position: relative;
  min-height: 28mm;
  margin: 10mm 0 8mm;
}

.cps-seal {
  position: absolute;
  left: 8mm;
  top: 0;
  height: auto;
  pointer-events: none;
}

.cps-sign-lines {
  padding-top: 18mm;
  line-height: 1.5;
}

.cps-footer {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8mm;
  padding-top: 4mm;
}

.cps-footer.has-divider {
  border-top: 3px solid #111;
  margin-top: 4mm;
  padding-top: 5mm;
}

.cps-kv-line {
  display: flex;
  gap: 3mm;
  margin-bottom: 1.5mm;
  line-height: 1.4;
}

.cps-kv-label {
  min-width: 24mm;
  font-weight: 600;
}

.cps-kv-value {
  flex: 1;
}

@media print {
  .cps-root {
    page-break-inside: avoid;
  }
}
</style>
