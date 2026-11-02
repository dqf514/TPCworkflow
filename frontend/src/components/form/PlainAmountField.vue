<template>
  <a-input-number
    :model-value="numVal"
    :disabled="readonly"
    :precision="precision"
    :min="minValue"
    class="w-full plain-amount-field"
    :size="size"
    placeholder="0.00"
    @update:model-value="onInput"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue?: unknown
    readonly?: boolean
    precision?: number
    min?: number
    size?: 'mini' | 'small' | 'medium' | 'large'
  }>(),
  { readonly: false, precision: 2, min: 0, size: 'small' },
)

const emit = defineEmits<{ 'update:modelValue': [number | null] }>()

const minValue = computed(() => props.min)

const numVal = computed(() => {
  const v = props.modelValue
  if (v == null || v === '') return undefined
  const n = Number(v)
  return Number.isNaN(n) ? undefined : n
})

function onInput(val: number | undefined) {
  emit('update:modelValue', val == null ? null : Number(val))
}
</script>

<style scoped>
/* Arco 各版本 InputNumber 内层 input 的类名不一致（部分版本是 .arco-input-number-input，
   2.57 直接用 .arco-input），两种都命中，避免右对齐与等宽数字失效。 */
.plain-amount-field :deep(.arco-input-number-input),
.plain-amount-field :deep(input.arco-input) {
  text-align: right;
  /* 金额列需要等宽数字才能对齐小数点 */
  font-variant-numeric: tabular-nums;
}
</style>
