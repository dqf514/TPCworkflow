<template>
  <div class="field-show-when-panel">
    <label class="props-switch-cell">
      <span>{{ t('designer.show_when_enable') }}</span>
      <a-switch v-model="enabled" size="small" />
    </label>
    <template v-if="enabled">
      <a-form-item :label="t('designer.show_when_source')" class="props-item">
        <a-select
          v-model="rule.fieldKey"
          :options="sourceFieldOpts"
          allow-search
          :placeholder="t('designer.show_when_source_ph')"
          @change="onSourceChange"
        />
      </a-form-item>
      <a-form-item :label="t('designer.show_when_values')" class="props-item">
        <a-select
          v-model="rule.values"
          :options="sourceValueOpts"
          :loading="sourceValueLoading"
          multiple
          allow-search
          :placeholder="sourceValuePlaceholder"
        />
      </a-form-item>
      <a-form-item
        v-if="sourceFieldType === 'multi_select' || sourceFieldType === 'checkbox_group'"
        :label="t('designer.show_when_match')"
        class="props-item"
      >
        <a-radio-group v-model="rule.match" type="button" size="small">
          <a-radio value="any">{{ t('designer.show_when_match_any') }}</a-radio>
          <a-radio value="all">{{ t('designer.show_when_match_all') }}</a-radio>
        </a-radio-group>
      </a-form-item>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { FieldShowWhenRule, FormFieldDef, FormSchema } from '@/types/form'
import { LINKAGE_SOURCE_TYPES } from '@/composables/useFieldLinkage'
import {
  fieldOptionsToSelectOpts,
  resolveFieldOptions,
  type FieldOptionItem,
} from '@/composables/useFieldOptions'

const props = defineProps<{
  field: FormFieldDef
  schema: FormSchema
}>()

const { t } = useI18n()

const enabled = computed({
  get: () => !!props.field.showWhen,
  set: (on: boolean) => {
    if (!on) {
      delete props.field.showWhen
      delete props.field.showWhenLogic
      return
    }
    if (!props.field.showWhen) {
      props.field.showWhen = { fieldKey: '', values: [], match: 'any' }
    }
  },
})

const rule = reactive({
  fieldKey: '',
  values: [] as string[],
  match: 'any' as 'any' | 'all',
})

const sourceValueItems = ref<FieldOptionItem[]>([])
const sourceValueLoading = ref(false)

function arrEq(a: string[] | undefined, b: string[]): boolean {
  if (!a) return b.length === 0
  if (a.length !== b.length) return false
  return a.every((v, i) => v === b[i])
}

function readRuleFromField(): { fieldKey: string; values: string[]; match: 'any' | 'all' } {
  const sw = props.field.showWhen
  const one = (Array.isArray(sw) ? sw[0] : sw) as FieldShowWhenRule | undefined
  return {
    fieldKey: one?.fieldKey || '',
    values: [...(one?.values || [])],
    match: one?.match || 'any',
  }
}

function ruleMatchesField(): boolean {
  const snapshot = readRuleFromField()
  return (
    rule.fieldKey === snapshot.fieldKey &&
    rule.match === snapshot.match &&
    arrEq(snapshot.values, rule.values)
  )
}

function syncFieldToRule() {
  const snapshot = readRuleFromField()
  if (
    rule.fieldKey === snapshot.fieldKey &&
    rule.match === snapshot.match &&
    arrEq(rule.values, snapshot.values)
  ) {
    return
  }
  rule.fieldKey = snapshot.fieldKey
  rule.values = snapshot.values
  rule.match = snapshot.match
}

function syncRuleToField() {
  if (!enabled.value || ruleMatchesField()) return
  props.field.showWhen = {
    fieldKey: rule.fieldKey,
    values: [...rule.values],
    match: rule.match,
  }
}

watch(
  () => props.field.showWhen,
  () => syncFieldToRule(),
  { immediate: true, deep: true },
)

watch(rule, () => syncRuleToField(), { deep: true })

const sourceFields = computed(() => {
  const out: FormFieldDef[] = []
  for (const sec of props.schema.sections || []) {
    for (const f of sec.fields || []) {
      if (f.id === props.field.id) continue
      if ((LINKAGE_SOURCE_TYPES as readonly string[]).includes(f.type) && f.key) {
        out.push(f)
      }
    }
  }
  return out
})

const sourceFieldOpts = computed(() =>
  sourceFields.value.map((f) => ({
    label: `${f.label || f.key}（${f.key}）`,
    value: f.key,
  })),
)

const sourceField = computed(() => sourceFields.value.find((f) => f.key === rule.fieldKey))

const sourceFieldType = computed(() => sourceField.value?.type || '')

async function refreshSourceValueOptions() {
  const src = sourceField.value
  if (!src || src.type === 'switch') {
    sourceValueItems.value = []
    return
  }
  sourceValueLoading.value = true
  try {
    sourceValueItems.value = await resolveFieldOptions(src)
  } finally {
    sourceValueLoading.value = false
  }
}

watch(
  () => [
    rule.fieldKey,
    sourceField.value?.props?.optionSource,
    sourceField.value?.props?.optionSetCode,
    sourceField.value?.props?.options,
  ],
  () => refreshSourceValueOptions(),
  { immediate: true, deep: true },
)

const sourceValueOpts = computed(() => {
  if (sourceFieldType.value === 'switch') {
    return [
      { label: '开启', value: '1' },
      { label: '关闭', value: '0' },
    ]
  }
  return fieldOptionsToSelectOpts(sourceValueItems.value)
})

const sourceValuePlaceholder = computed(() => {
  if (sourceValueLoading.value) return t('designer.linkage_option_loading')
  if (!sourceValueOpts.value.length) return t('designer.linkage_option_empty')
  return t('designer.show_when_values_ph')
})

function onSourceChange() {
  rule.values = []
}
</script>

<style scoped>
.field-show-when-panel {
  margin-top: 4px;
}

.props-switch-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
}
</style>
