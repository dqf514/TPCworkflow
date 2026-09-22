<template>
  <div class="field-options-panel">
    <a-form-item :label="t('designer.option_source')">
      <a-radio-group v-model="optionSource" type="button" size="small">
        <a-radio value="manual">{{ t('designer.option_manual') }}</a-radio>
        <a-radio value="option_set">{{ t('designer.option_set') }}</a-radio>
      </a-radio-group>
    </a-form-item>

    <template v-if="optionSource === 'option_set'">
      <a-form-item :label="t('designer.pick_option_set')">
        <a-select
          v-model="optionSetCode"
          :options="setOpts"
          :placeholder="t('designer.option_set_ph')"
          allow-search
          allow-clear
        />
      </a-form-item>
      <p class="hint-text">{{ t('designer.option_set_hint_option') }}</p>
      <a-button size="mini" type="text" @click="previewSet">{{ t('designer.preview_options') }}</a-button>
      <div v-if="previewList.length" class="preview-list">
        <a-tag v-for="o in previewList" :key="o.value" size="small">{{ o.label }}</a-tag>
      </div>
    </template>

    <template v-else>
      <div class="manual-toolbar">
        <a-button type="text" size="mini" @click="batchVisible = true">{{ t('designer.batch') }}</a-button>
      </div>
      <div v-for="(opt, oi) in manualRows" :key="oi" class="manual-row">
        <a-input
          v-model="opt.name"
          :placeholder="t('designer.opt_name')"
          class="manual-name"
          @input="onManualInput"
        />
        <a-input
          v-model="opt.code"
          :placeholder="t('designer.opt_code')"
          class="manual-code"
          @input="onManualInput"
        />
        <a-button size="mini" status="danger" @click="removeRow(oi)">−</a-button>
        <a-button size="mini" @click="addRowAfter(oi)">+</a-button>
      </div>
      <a-button size="mini" long class="mt-1" @click="addRow">{{ t('designer.add_option') }}</a-button>
      <p class="hint-text">{{ t('designer.manual_hint') }}</p>
    </template>

    <a-modal v-model:visible="batchVisible" :title="t('designer.batch_title')" @ok="applyBatch">
      <p class="text-sm text-gray-500 mb-2">{{ t('designer.batch_hint') }}</p>
      <a-textarea v-model="batchText" :auto-size="{ minRows: 8 }" placeholder="Name,code" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { FormFieldDef } from '@/types/form'
import {
  loadOptionSetList,
  loadOptionsBySetCode,
  normalizeManualOption,
  type FieldOptionItem,
} from '@/composables/useFieldOptions'

const { t } = useI18n()
const props = defineProps<{ field: FormFieldDef }>()

const batchVisible = ref(false)
const batchText = ref('')
const setOpts = ref<{ label: string; value: string }[]>([])
const previewList = ref<FieldOptionItem[]>([])

function ensureProps() {
  if (!props.field.props) props.field.props = {}
}

const optionSource = computed({
  get: () => (props.field.props?.optionSource === 'option_set' ? 'option_set' : 'manual'),
  set: (v: 'manual' | 'option_set') => {
    ensureProps()
    props.field.props!.optionSource = v
  },
})

const optionSetCode = computed({
  get: () => String(props.field.props?.optionSetCode || ''),
  set: (v: string) => {
    ensureProps()
    props.field.props!.optionSetCode = v
  },
})

const manualRows = ref<{ name: string; code: string }[]>([{ name: '', code: '' }])

function syncManualToProps() {
  ensureProps()
  props.field.props!.options = manualRows.value
    .filter((r) => r.name.trim() || r.code.trim())
    .map((r) =>
      normalizeManualOption({
        name: r.name.trim(),
        code: r.code.trim() || r.name.trim(),
      }),
    )
}

function loadManualFromField() {
  const raw = (props.field.props?.options as FieldOptionItem[]) || []
  manualRows.value = raw.length
    ? raw.map((o) => ({
        name: o.name || o.label || '',
        code: o.code || o.value || '',
      }))
    : [{ name: '', code: '' }]
}

function addRow() {
  manualRows.value.push({ name: '', code: '' })
  syncManualToProps()
}

function addRowAfter(oi: number) {
  manualRows.value.splice(oi + 1, 0, { name: '', code: '' })
  syncManualToProps()
}

function removeRow(oi: number) {
  manualRows.value.splice(oi, 1)
  if (!manualRows.value.length) manualRows.value.push({ name: '', code: '' })
  syncManualToProps()
}

function onManualInput() {
  syncManualToProps()
}

function applyBatch() {
  const lines = batchText.value
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
  manualRows.value = lines.map((line) => {
    const parts = line.split(/[,，\t]/).map((p) => p.trim())
    const name = parts[0] || ''
    const code = parts[1] || name
    return { name, code }
  })
  syncManualToProps()
  batchVisible.value = false
  batchText.value = ''
}

async function previewSet() {
  if (!optionSetCode.value) {
    previewList.value = []
    return
  }
  previewList.value = await loadOptionsBySetCode(optionSetCode.value, true)
}

watch(optionSetCode, () => {
  if (optionSource.value === 'option_set') previewSet()
})

watch(
  () => props.field.id,
  () => {
    loadManualFromField()
    if (optionSource.value === 'option_set' && optionSetCode.value) previewSet()
  },
  { immediate: true },
)

onMounted(async () => {
  const list = await loadOptionSetList()
  setOpts.value = list.map((s) => ({
    label: `${s.name}（${s.code}）`,
    value: s.code,
  }))
})
</script>

<style scoped>
.field-options-panel {
  width: 100%;
}

.manual-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 6px;
}

.manual-row {
  display: flex;
  gap: 4px;
  align-items: center;
  margin-bottom: 6px;
}

.manual-name {
  flex: 1;
  min-width: 0;
}

.manual-code {
  width: 88px;
  flex-shrink: 0;
}

.preview-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.hint-text {
  font-size: 12px;
  color: #86909c;
  margin: 4px 0 0;
  line-height: 1.5;
}
</style>
