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
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
}

.icon-picker-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 4px;
  border: 1px solid var(--border, #e5e6eb);
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.icon-picker-item:hover {
  border-color: var(--brand, #5034ff);
}

.icon-picker-item.active {
  border-color: var(--brand, #5034ff);
  box-shadow: 0 0 0 2px rgba(80, 52, 255, 0.15);
}

.icon-picker-label {
  font-size: 0.6875rem;
  color: var(--text-secondary, #676879);
  text-align: center;
  line-height: 1.2;
}
</style>
