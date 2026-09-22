<template>
  <div class="field-linkage-panel">
    <p class="hint-text">{{ t('designer.linkage_hint') }}</p>
    <a-table :data="rules" :pagination="false" size="small" row-key="_uid">
      <template #columns>
        <a-table-column :title="t('designer.linkage_option')" :width="140">
          <template #cell="{ record }">
            <a-select
              v-if="field.type !== 'switch'"
              v-model="record.optionValue"
              :options="optionOpts"
              :loading="optionOptsLoading"
              allow-search
              :placeholder="optionOptsPlaceholder"
            />
            <a-select v-else v-model="record.optionValue" :options="switchOpts" />
          </template>
        </a-table-column>
        <a-table-column :title="t('designer.linkage_show_fields')">
          <template #cell="{ record }">
            <a-select
              v-model="record.showFieldIds"
              :options="fieldOpts"
              multiple
              allow-search
              :max-tag-count="2"
              :placeholder="t('designer.linkage_show_fields_ph')"
            />
          </template>
        </a-table-column>
        <a-table-column :title="t('designer.linkage_show_sections')" :width="200">
          <template #cell="{ record }">
            <a-select
              v-model="record.showSectionIds"
              :options="sectionOpts"
              multiple
              allow-search
              :max-tag-count="1"
              :placeholder="t('designer.linkage_show_sections_ph')"
            />
          </template>
        </a-table-column>
        <a-table-column :width="56">
          <template #cell="{ record }">
            <a-button type="text" status="danger" size="mini" @click="removeRule(record._uid)">
              {{ t('designer.delete_short') }}
            </a-button>
          </template>
        </a-table-column>
      </template>
    </a-table>
    <a-button long size="small" class="mt-2" @click="addRule">{{ t('designer.linkage_add_rule') }}</a-button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { FieldLinkageRule, FormFieldDef, FormSchema } from '@/types/form'
import { listAllFields } from '@/composables/useFieldLinkage'
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

type RuleRow = FieldLinkageRule & { _uid: string; showSectionIds: string[] }

let uidSeq = 1
function nextUid() {
  uidSeq += 1
  return `lr-${uidSeq}`
}

function ensureLinkage(): { rules: FieldLinkageRule[] } {
  if (!props.field.props) props.field.props = {}
  if (!props.field.props.linkage) {
    props.field.props.linkage = { rules: [] }
  }
  return props.field.props.linkage as { rules: FieldLinkageRule[] }
}

function toRow(r: FieldLinkageRule, uid?: string): RuleRow {
  return {
    _uid: uid || nextUid(),
    optionValue: r.optionValue || '',
    showFieldIds: [...(r.showFieldIds || [])],
    showSectionIds: [...(r.showSectionIds || [])],
  }
}

const rules = ref<RuleRow[]>([])
const linkageOptionItems = ref<FieldOptionItem[]>([])
const optionOptsLoading = ref(false)

function loadRules() {
  const linkage = ensureLinkage()
  rules.value = (linkage.rules || []).map((r) => toRow(r))
}

function persistRules() {
  const linkage = ensureLinkage()
  linkage.rules = rules.value.map(({ _uid, ...rest }) => rest)
}

async function refreshLinkageOptions() {
  if (props.field.type === 'switch') {
    linkageOptionItems.value = []
    return
  }
  optionOptsLoading.value = true
  try {
    linkageOptionItems.value = await resolveFieldOptions(props.field)
  } finally {
    optionOptsLoading.value = false
  }
}

watch(
  () => props.field.id,
  () => loadRules(),
  { immediate: true },
)

watch(rules, () => persistRules(), { deep: true })

watch(
  () => [
    props.field.id,
    props.field.type,
    props.field.props?.optionSource,
    props.field.props?.optionSetCode,
    props.field.props?.options,
  ],
  () => refreshLinkageOptions(),
  { immediate: true, deep: true },
)

const optionOpts = computed(() => fieldOptionsToSelectOpts(linkageOptionItems.value))

const optionOptsPlaceholder = computed(() => {
  if (optionOptsLoading.value) return t('designer.linkage_option_loading')
  if (!optionOpts.value.length) return t('designer.linkage_option_empty')
  return t('designer.linkage_option_ph')
})

const switchOpts = [
  { label: '开启', value: '1' },
  { label: '关闭', value: '0' },
]

const fieldOpts = computed(() =>
  listAllFields(props.schema)
    .filter((f) => f.id !== props.field.id && f.type !== 'divider')
    .map((f) => ({
      label: `${f.sectionTitle ? `[${f.sectionTitle}] ` : ''}${f.label || f.key}（${f.key || f.type}）`,
      value: f.id,
    })),
)

const sectionOpts = computed(() =>
  (props.schema.sections || []).map((s) => ({
    label: s.title || s.id,
    value: s.id,
  })),
)

function addRule() {
  rules.value.push(
    toRow({
      optionValue: optionOpts.value[0]?.value || (props.field.type === 'switch' ? '1' : ''),
      showFieldIds: [],
      showSectionIds: [],
    }),
  )
}

function removeRule(uid: string) {
  rules.value = rules.value.filter((r) => r._uid !== uid)
}
</script>

<style scoped>
.field-linkage-panel {
  margin-top: 4px;
}

.hint-text {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.5;
}

.mt-2 {
  margin-top: 8px;
}
</style>
