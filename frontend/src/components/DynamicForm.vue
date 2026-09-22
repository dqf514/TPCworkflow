<template>
  <a-form :model="model" layout="vertical">
    <a-form-item
      v-for="field in schema"
      :key="field.key"
      :label="field.label"
      :required="field.required"
    >
      <a-input v-if="field.type === 'text'" v-model="model[field.key]" />
      <a-input-number
        v-else-if="field.type === 'number'"
        v-model="model[field.key]"
        class="w-full"
      />
      <a-textarea v-else-if="field.type === 'textarea'" v-model="model[field.key]" />
      <a-select
        v-else-if="field.type === 'select'"
        v-model="model[field.key]"
        :options="field.options || []"
        allow-clear
      />
      <a-date-picker
        v-else-if="field.type === 'date'"
        v-model="model[field.key]"
        class="w-full"
      />
      <a-input v-else v-model="model[field.key]" />
    </a-form-item>
  </a-form>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'

export interface FormField {
  key: string
  label: string
  type: string
  required?: boolean
  options?: { label: string; value: string }[]
}

const props = defineProps<{ schema: FormField[]; modelValue?: Record<string, unknown> }>()
const emit = defineEmits<{ 'update:modelValue': [Record<string, unknown>] }>()

const model = reactive<Record<string, unknown>>({ ...(props.modelValue || {}) })

watch(
  model,
  () => emit('update:modelValue', { ...model }),
  { deep: true },
)

watch(
  () => props.schema,
  (s) => {
    for (const f of s) {
      if (model[f.key] === undefined) model[f.key] = f.type === 'number' ? undefined : ''
    }
  },
  { immediate: true },
)
</script>
