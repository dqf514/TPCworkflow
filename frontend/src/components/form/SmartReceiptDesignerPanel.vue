<template>
  <div class="smart-receipt-designer">
    <div class="props-section-title">{{ t('designer.smart_receipt_props') }}</div>
    <p class="hint-text">{{ t('designer.smart_receipt_hint') }}</p>

    <div class="props-grid cols-2">
      <a-form-item :label="t('designer.smart_receipt_scene')" class="props-item">
        <a-select v-model="scene" :options="sceneOpts" />
      </a-form-item>
      <a-form-item :label="t('designer.smart_receipt_fill_mode')" class="props-item">
        <a-select v-model="fillMode" :options="fillModeOpts" />
      </a-form-item>
    </div>

    <a-form-item
      v-if="fillMode !== 'main_fields'"
      :label="t('designer.smart_receipt_target_detail')"
      class="props-item"
    >
      <a-select
        v-model="targetDetailKey"
        :options="detailOpts"
        allow-clear
        :placeholder="t('designer.smart_receipt_target_detail_ph')"
      />
    </a-form-item>

    <a-form-item :label="t('designer.smart_receipt_attach')" class="props-item">
      <a-select
        v-model="attachToFieldKey"
        :options="attachFieldOpts"
        allow-clear
        :placeholder="t('designer.smart_receipt_attach_ph')"
      />
    </a-form-item>

    <div class="props-switches mb-2">
      <label class="props-switch-cell">
        <span>{{ t('designer.smart_receipt_auto_fill') }}</span>
        <a-switch v-model="autoFill" size="small" />
      </label>
    </div>

    <div class="props-section-title">{{ t('designer.smart_receipt_mappings') }}</div>
    <div v-for="(row, idx) in mappings" :key="idx" class="mapping-row">
      <a-select
        v-model="row.extractKey"
        :options="extractKeyOpts"
        :placeholder="t('designer.smart_receipt_extract_ph')"
        allow-search
        class="mapping-col"
      />
      <a-select
        v-model="row.targetScope"
        :options="scopeOpts"
        class="mapping-scope"
      />
      <a-select
        v-model="row.targetKey"
        :options="targetOptsForRow(row)"
        :placeholder="t('designer.smart_receipt_target_ph')"
        allow-search
        class="mapping-col"
      />
      <a-button size="mini" status="danger" @click="removeMapping(idx)">×</a-button>
    </div>
    <a-button size="mini" long class="mt-1" @click="addMapping">{{ t('designer.smart_receipt_add_mapping') }}</a-button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RECEIPT_EXTRACT_KEYS, type SmartReceiptMapping } from '@/constants/receiptExtractKeys'
import { listDetailTargets, listMainMappableFields } from '@/composables/useSmartReceiptFill'
import type { FormFieldDef, FormSchema } from '@/types/form'

const props = defineProps<{
  field: FormFieldDef
  schema: FormSchema
}>()

const { t } = useI18n()

function ensureRecognition() {
  if (!props.field.props) props.field.props = {}
  if (!props.field.props.recognition || typeof props.field.props.recognition !== 'object') {
    props.field.props.recognition = {
      enabled: true,
      scene: 'expense',
      fillMode: 'detail_row',
      mappings: [],
      autoFill: true,
      attachToScope: 'detail',
    }
  }
  if (!Array.isArray((props.field.props.recognition as { mappings?: unknown }).mappings)) {
    ;(props.field.props.recognition as { mappings: SmartReceiptMapping[] }).mappings = []
  }
}

const rec = computed(() => {
  ensureRecognition()
  return props.field.props!.recognition as Record<string, unknown>
})

const sceneOpts = [
  { label: '费用报销', value: 'expense' },
  { label: '付款申请', value: 'payment' },
  { label: '通用凭证', value: 'general' },
]

const fillModeOpts = [
  { label: '填入明细行', value: 'detail_row' },
  { label: '填入主表', value: 'main_fields' },
  { label: '主表 + 明细', value: 'both' },
]

const scopeOpts = [
  { label: '主表', value: 'main' },
  { label: '明细', value: 'detail' },
]

const extractKeyOpts = RECEIPT_EXTRACT_KEYS.map((k) => ({
  label: `${k.label}（${k.key}）`,
  value: k.key,
}))

const detailTargets = computed(() => listDetailTargets(props.schema))

const detailOpts = computed(() =>
  detailTargets.value.map((d) => ({ label: d.detailLabel, value: d.detailKey })),
)

const mainFields = computed(() => listMainMappableFields(props.schema))

const attachFieldOpts = computed(() => {
  const opts: { label: string; value: string }[] = []
  for (const f of mainFields.value) {
    if (f.type === 'attachment' || f.type === 'image') {
      opts.push({ label: `[主表] ${f.label}`, value: f.key })
    }
  }
  for (const d of detailTargets.value) {
    for (const c of d.columns) {
      if (c.type === 'attachment' || c.type === 'image') {
        opts.push({ label: `[${d.detailLabel}] ${c.label}`, value: c.key })
      }
    }
  }
  return opts
})

const scene = computed({
  get: () => String(rec.value.scene || 'expense'),
  set: (v: string) => {
    rec.value.scene = v
  },
})

const fillMode = computed({
  get: () => String(rec.value.fillMode || 'detail_row'),
  set: (v: string) => {
    rec.value.fillMode = v
  },
})

const targetDetailKey = computed({
  get: () => String(rec.value.targetDetailKey || ''),
  set: (v: string) => {
    rec.value.targetDetailKey = v
  },
})

const attachToFieldKey = computed({
  get: () => String(rec.value.attachToFieldKey || ''),
  set: (v: string) => {
    rec.value.attachToFieldKey = v
    rec.value.attachToScope = mainFields.value.some((f) => f.key === v) ? 'main' : 'detail'
  },
})

const autoFill = computed({
  get: () => rec.value.autoFill === true,
  set: (v: boolean) => {
    rec.value.autoFill = v
  },
})

const mappings = computed({
  get: () => (rec.value.mappings as SmartReceiptMapping[]) || [],
  set: (v: SmartReceiptMapping[]) => {
    rec.value.mappings = v
  },
})

function targetOptsForRow(row: SmartReceiptMapping) {
  if (row.targetScope === 'main') {
    return mainFields.value.map((f) => ({
      label: `${f.label}（${f.type}）`,
      value: f.key,
    }))
  }
  const detailKey = targetDetailKey.value
  const detail = detailTargets.value.find((d) => d.detailKey === detailKey)
  if (!detail) return []
  return detail.columns.map((c) => ({
    label: `${c.label}（${c.type}）`,
    value: c.key,
  }))
}

function addMapping() {
  const scope = fillMode.value === 'main_fields' ? 'main' : 'detail'
  mappings.value = [
    ...mappings.value,
    { extractKey: 'total_amount', targetKey: '', targetScope: scope as 'main' | 'detail' },
  ]
}

function removeMapping(idx: number) {
  mappings.value = mappings.value.filter((_, i) => i !== idx)
}
</script>

<style scoped>
.smart-receipt-designer .hint-text {
  margin: 0 0 8px;
  font-size: 12px;
  color: #86909c;
  line-height: 1.4;
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.mapping-col {
  flex: 1;
  min-width: 0;
}

.mapping-scope {
  width: 88px;
  flex-shrink: 0;
}

.mb-2 {
  margin-bottom: 8px;
}
</style>
