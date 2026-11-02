<template>
  <div class="icon-picker">
    <div class="icon-picker-grid">
      <button
        v-for="item in PROCESS_ICON_CATALOG"
        :key="item.key"
        type="button"
        class="icon-picker-item"
        :class="{ active: modelValue === item.key }"
        :title="item.label"
        @click="emit('update:modelValue', item.key)"
      >
        <ProcessIcon :icon="item.key" :size="48" />
        <span class="icon-picker-label">{{ item.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import ProcessIcon from './ProcessIcon.vue'
import { PROCESS_ICON_CATALOG } from '@/utils/processIcons'

defineProps<{ modelValue?: string }>()
const emit = defineEmits<{ 'update:modelValue': [string] }>()
</script>

<style scoped>
.icon-picker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
  gap: var(--app-space-8);
  max-height: 280px;
  overflow-y: auto;
}

.icon-picker-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--app-space-xs);
  padding: var(--app-space-sm) var(--app-space-xs);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.icon-picker-item:hover {
  border-color: var(--brand);
}

.icon-picker-item.active {
  border-color: var(--brand);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand) 15%, transparent);
}

.icon-picker-label {
  font-size: var(--app-font-2xs);
  color: var(--text-secondary);
  text-align: center;
  line-height: 1.2;
}
</style>
