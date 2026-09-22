<template>
  <div class="flow-connector" :class="[`dir-${direction}`, { 'is-readonly': readonly }]">
    <div v-if="direction === 'vertical'" class="flow-line-v" />
    <template v-else>
      <div class="flow-line" />
      <FlowAddMenu v-if="!readonly" @select="(type) => emit('add', type)" />
      <div v-else class="flow-line-dot" />
      <div class="flow-line" />
    </template>
  </div>
</template>

<script setup lang="ts">
import FlowAddMenu from '@/components/workflow/FlowAddMenu.vue'

withDefaults(
  defineProps<{
    readonly?: boolean
    direction?: 'horizontal' | 'vertical'
  }>(),
  { direction: 'horizontal' },
)
const emit = defineEmits<{ add: [type: string] }>()
</script>

<style scoped>
.flow-connector {
  display: flex;
  flex-direction: row;
  align-items: center;
  flex-shrink: 0;
  width: auto;
  padding: 0 2px;
}

.flow-connector.dir-vertical {
  flex-direction: column;
  width: auto;
  padding: 2px 0;
  height: auto;
}

.flow-line {
  width: 32px;
  height: 2px;
  background: #c9cdd4;
}

.flow-line-v {
  width: 2px;
  height: 28px;
  background: #c9cdd4;
}

.flow-connector.is-readonly .flow-line {
  width: 24px;
}

.flow-line-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c9cdd4;
  flex-shrink: 0;
}
</style>
