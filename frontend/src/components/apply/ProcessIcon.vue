<template>
  <img
    :src="src"
    :alt="label"
    class="process-icon-img"
    :style="{ width: `${size}px`, height: `${size}px` }"
    draggable="false"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getProcessIconDataUrl, PROCESS_ICON_CATALOG } from '@/utils/processIcons'

const props = withDefaults(
  defineProps<{
    icon?: string
    size?: number
  }>(),
  {
    icon: 'general',
    size: 56,
  },
)

const label = computed(
  () => PROCESS_ICON_CATALOG.find((m) => m.key === props.icon)?.label || '流程',
)
const src = computed(() => getProcessIconDataUrl(props.icon || 'general', props.size))
</script>

<style scoped>
.process-icon-img {
  display: block;
  border-radius: 25%;
  flex-shrink: 0;
  object-fit: contain;
}
</style>
