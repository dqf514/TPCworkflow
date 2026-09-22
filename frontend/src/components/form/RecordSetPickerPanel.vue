<template>
  <div class="record-set-picker-panel">
    <a-form-item :label="t('designer.pick_record_set')">
      <a-select
        v-model="recordSetCode"
        :options="setOpts"
        :placeholder="t('designer.record_set_ph')"
        allow-search
        allow-clear
      />
    </a-form-item>
    <a-form-item v-if="columnOpts.length" :label="t('designer.record_set_label_field')">
      <a-select
        v-model="labelField"
        :options="columnOpts"
        :placeholder="t('designer.record_set_label_field_ph')"
        allow-clear
      />
      <template #extra>
        <span class="hint-text">{{ t('designer.record_set_label_field_hint') }}</span>
      </template>
    </a-form-item>
    <a-form-item :label="t('designer.record_set_scope')">
      <a-checkbox v-model="showCompanyRecords" :disabled="companyScopeLocked">
        {{ t('designer.record_set_show_company') }}
      </a-checkbox>
      <a-checkbox v-model="showPersonalRecords" class="ml-3" :disabled="personalScopeLocked">
        {{ t('designer.record_set_show_personal') }}
      </a-checkbox>
      <template #extra>
        <span class="hint-text">{{ scopeHint }}</span>
      </template>
    </a-form-item>
    <p class="hint-text">{{ t('designer.record_set_hint') }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { FormFieldDef } from '@/types/form'
import { loadRecordSetList, loadRecordSetPayload, type RecordSetDataScope } from '@/composables/useRecordSets'

const props = defineProps<{ field: FormFieldDef }>()

const { t } = useI18n()
const setList = ref<{ code: string; name: string }[]>([])
const previewColumns = ref<{ field_key: string; label: string }[]>([])
const linkedDataScope = ref<RecordSetDataScope>('mixed')

const personalScopeLocked = computed(() => linkedDataScope.value === 'company')
const companyScopeLocked = computed(() => linkedDataScope.value === 'personal')

const setOpts = computed(() =>
  setList.value.map((s) => ({ label: `${s.name}（${s.code}）`, value: s.code })),
)

const recordSetCode = computed({
  get: () => String(props.field.props?.recordSetCode || ''),
  set: (v: string) => {
    if (!props.field.props) props.field.props = {}
    props.field.props.recordSetCode = v
  },
})

const labelField = computed({
  get: () => String(props.field.props?.labelField || ''),
  set: (v: string) => {
    if (!props.field.props) props.field.props = {}
    props.field.props.labelField = v
  },
})

const showCompanyRecords = computed({
  get: () => props.field.props?.showCompanyRecords !== false,
  set: (v: boolean) => {
    if (!props.field.props) props.field.props = {}
    props.field.props.showCompanyRecords = v
  },
})

const showPersonalRecords = computed({
  get: () => props.field.props?.showPersonalRecords !== false,
  set: (v: boolean) => {
    if (!props.field.props) props.field.props = {}
    props.field.props.showPersonalRecords = v
  },
})

const columnOpts = computed(() =>
  previewColumns.value.map((c) => ({ label: c.label, value: c.field_key })),
)

const scopeHint = computed(() => {
  if (linkedDataScope.value === 'company') {
    return '该配置表为公司级，填报时仅可选择公司数据，不支持保存到个人配置'
  }
  if (linkedDataScope.value === 'personal') {
    return '该配置表为个人级，仅显示与保存本人数据'
  }
  return t('designer.record_set_scope_hint')
})

function applyScopeDefaults() {
  if (linkedDataScope.value === 'company') {
    showPersonalRecords.value = false
    showCompanyRecords.value = true
  } else if (linkedDataScope.value === 'personal') {
    showCompanyRecords.value = false
    showPersonalRecords.value = true
  }
}

async function refreshColumns() {
  const code = recordSetCode.value.trim()
  if (!code) {
    previewColumns.value = []
    linkedDataScope.value = 'mixed'
    return
  }
  const payload = await loadRecordSetPayload(code)
  previewColumns.value = payload?.columns || []
  linkedDataScope.value = payload?.data_scope || 'mixed'
  applyScopeDefaults()
  if (previewColumns.value.length && !labelField.value) {
    labelField.value = previewColumns.value[0].field_key
  }
}

watch(recordSetCode, () => {
  void refreshColumns()
})

onMounted(async () => {
  setList.value = await loadRecordSetList()
  await refreshColumns()
})
</script>

<style scoped>
.hint-text {
  font-size: 12px;
  color: #86909c;
  margin: 0;
}
</style>
