<template>
  <WorkflowVerticalDesigner
    ref="innerRef"
    :model-value="modelValue"
    :form-schema="formSchema"
    :min-height="minHeight"
    @update:model-value="emit('update:modelValue', $event)"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import WorkflowVerticalDesigner from '@/components/WorkflowVerticalDesigner.vue'
import type { FormSchema } from '@/types/form'

const props = withDefaults(
  defineProps<{
    modelValue?: { nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] }
    formSchema?: FormSchema
    minHeight?: string
  }>(),
  { minHeight: 'min(72vh, 720px)' },
)

const emit = defineEmits<{ 'update:modelValue': [typeof props.modelValue] }>()

const innerRef = ref<{ resize?: () => void; exportGraph?: () => void } | null>(null)

function resize() {
  innerRef.value?.resize?.()
}

function exportGraph() {
  innerRef.value?.exportGraph?.()
}

defineExpose({ resize, exportGraph })
</script>
