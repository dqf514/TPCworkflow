<template>

  <a-input
    v-if="column.type === 'formula'"
    :model-value="strVal"
    readonly
    :placeholder="column.placeholder || '自动计算'"
    :size="controlSize"
  />

  <a-input
    v-else-if="column.type === 'input' || column.type === 'serial_no'"
    :model-value="strVal"
    :readonly="readonly"
    :placeholder="inline ? column.label : column.placeholder"
    :size="controlSize"
    allow-clear
    @update:model-value="emitVal"
  />

  <a-textarea

    v-else-if="column.type === 'textarea' && !inline"

    :model-value="strVal"

    :readonly="readonly"

    :placeholder="column.placeholder"

    :auto-size="{ minRows: 2 }"

    @update:model-value="emitVal"

  />

  <a-input

    v-else-if="column.type === 'textarea' && inline"

    :model-value="strVal"

    :readonly="readonly"

    :placeholder="column.label"

    :size="controlSize"

    allow-clear

    @update:model-value="emitVal"

  />

  <PlainAmountField
    v-else-if="column.type === 'plain_amount'"
    :model-value="modelValue"
    :readonly="readonly"
    :precision="Number(column.props?.precision ?? 2)"
    :size="controlSize"
    @update:model-value="emitVal"
  />

  <MoneyField

    v-else-if="column.type === 'money'"

    :model-value="modelValue"

    :readonly="readonly"

    :compact="!inline"

    :inline="inline"

    @update:model-value="emitVal"

  />

  <a-input-number

    v-else-if="column.type === 'number'"

    :model-value="numVal"

    :readonly="readonly"

    :size="controlSize"

    class="w-full"

    @update:model-value="emitVal"

  />

  <span

    v-else-if="readonly && (column.type === 'date' || column.type === 'datetime' || column.type === 'time')"

    class="detail-readonly-time"

  >{{ formatTemporalValue(column.type, modelValue) }}</span>

  <a-date-picker

    v-else-if="column.type === 'date'"

    :model-value="strVal"

    :disabled="readonly"

    :size="controlSize"

    class="w-full"

    @update:model-value="emitVal"

  />

  <a-range-picker

    v-else-if="column.type === 'date_range'"

    :model-value="rangeVal"

    :disabled="readonly"

    :size="controlSize"

    class="w-full"

    @update:model-value="emitVal"

  />

  <span

    v-else-if="readonly && column.type === 'select'"

    class="detail-readonly-time"

  >{{ selectDisplayLabel }}</span>



  <a-select

    v-else-if="column.type === 'select'"

    :model-value="modelValue"

    :disabled="readonly"

    :options="selectOpts.map((o) => ({ label: o.label, value: o.value }))"

    :size="controlSize"

    allow-clear

    class="w-full"

    @update:model-value="emitVal"

  />

  <a-select

    v-else-if="column.type === 'user_picker'"

    :model-value="modelValue"

    :disabled="readonly"

    :options="pickerCtx?.userOpts?.value || []"

    :multiple="!!column.props?.multiple"

    :size="controlSize"

    allow-search

    allow-clear

    class="w-full"

    @update:model-value="emitVal"

  />

  <a-select

    v-else-if="column.type === 'dept_picker'"

    :model-value="modelValue"

    :disabled="readonly"

    :options="pickerCtx?.deptOpts?.value || []"

    :multiple="!!column.props?.multiple"

    :size="controlSize"

    allow-search

    allow-clear

    class="w-full"

    @update:model-value="emitVal"

  />

  <DetailInlineAttachment

    v-else-if="column.type === 'attachment' || column.type === 'image'"

    :column="column"

    :columns="columns"

    :detail-key="detailKey"

    :row-index="rowIndex"

    :model-value="modelValue"

    :readonly="readonly"

    :compact="inline"

    @update:model-value="emitVal"

    @fill-row="(patch) => emit('fill-row', patch)"

  />

  <a-input

    v-else-if="column.type === 'phone' || column.type === 'email' || column.type === 'location'"

    :model-value="strVal"

    :readonly="readonly"

    :size="controlSize"

    :type="column.type === 'email' ? 'email' : 'text'"

    :placeholder="column.type === 'email' ? '请输入有效邮箱地址' : undefined"

    @update:model-value="emitVal"

  />

  <a-input

    v-else

    :model-value="strVal"

    :readonly="readonly"

    :size="controlSize"

    @update:model-value="emitVal"

  />

</template>



<script setup lang="ts">

import { computed, inject, onMounted, ref } from 'vue'

import type { FormFieldDef } from '@/types/form'

import { formatDate, formatDateTime } from '@/utils/dateTime'

import MoneyField from '@/components/form/MoneyField.vue'
import PlainAmountField from '@/components/form/PlainAmountField.vue'

import DetailInlineAttachment from '@/components/form/DetailInlineAttachment.vue'

import { resolveFieldOptions, resolveOptionLabel, type FieldOptionItem } from '@/composables/useFieldOptions'



const props = defineProps<{

  column: FormFieldDef

  columns?: FormFieldDef[]

  detailKey?: string

  rowIndex?: number

  modelValue?: unknown

  readonly?: boolean

  inline?: boolean

}>()



const emit = defineEmits<{

  'update:modelValue': [unknown]

  'fill-row': [Record<string, unknown>]

}>()



const pickerCtx = inject<{

  userOpts: { value: { label: string; value: number }[] }

  deptOpts: { value: { label: string; value: number }[] }

} | null>('formPickerContext', null)



const controlSize = computed(() => (props.inline ? 'small' : 'medium'))

const columns = computed(() => props.columns || [])

const detailKey = computed(() => props.detailKey || '')

const rowIndex = computed(() => props.rowIndex ?? 0)



const strVal = computed(() => (props.modelValue == null ? '' : String(props.modelValue)))



const rangeVal = computed(() => {

  if (Array.isArray(props.modelValue)) return props.modelValue as string[]

  return undefined

})



const numVal = computed(() => {

  const n = Number(props.modelValue)

  return Number.isNaN(n) ? undefined : n

})



const selectOpts = ref<FieldOptionItem[]>([])



const selectDisplayLabel = computed(() => resolveOptionLabel(props.modelValue, selectOpts.value))



onMounted(async () => {

  if (props.column.type === 'select') {

    selectOpts.value = await resolveFieldOptions(props.column)

  }

})



function formatTemporalValue(type: string, raw: unknown): string {

  if (raw == null || raw === '') return '—'

  if (type === 'date') return formatDate(String(raw))

  return formatDateTime(String(raw))

}



function emitVal(v: unknown) {

  emit('update:modelValue', v)

}

</script>



<style scoped>

.detail-readonly-time {

  font-size: 0.8125rem;

  color: var(--color-text-2, #4e5969);

}

</style>


