<template>
  <span class="status-pill" :class="[`status-pill--${tone}`, { 'status-pill--dot': dot }]">
    <span v-if="dot" class="status-pill-dot" aria-hidden="true" />
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    status?: string
    label?: string
    tone?: 'success' | 'danger' | 'info' | 'warning' | 'neutral'
    dot?: boolean
  }>(),
  {
    dot: true,
  },
)

const toneByStatus: Record<string, 'success' | 'danger' | 'info' | 'warning' | 'neutral'> = {
  approved: 'success',
  completed: 'success',
  running: 'info',
  pending: 'info',
  rejected: 'danger',
  reject: 'danger',
  cancelled: 'neutral',
  draft: 'neutral',
  withdraw: 'warning',
  transfer: 'warning',
}

const tone = computed(() => props.tone || toneByStatus[props.status || ''] || 'neutral')
const label = computed(() => props.label || props.status || '')
</script>

<style scoped>
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  padding: 2px 9px;
  border-radius: var(--radius-pill);
  font-size: 11.5px;
  font-weight: 500;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-pill-dot {
  flex-shrink: 0;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.8;
}

.status-pill--success {
  background: var(--success-soft);
  color: var(--success);
}

.status-pill--danger {
  background: var(--danger-soft);
  color: var(--danger);
}

.status-pill--info {
  background: var(--info-soft);
  color: var(--info);
}

.status-pill--warning {
  background: var(--warning-soft);
  color: var(--warning);
}

.status-pill--neutral {
  background: var(--surface-muted);
  color: var(--text-secondary);
}
</style>
