<template>
  <span
    class="status-pill"
    :class="[`status-pill--${tone}`, { 'status-pill--dot': dot }]"
    :title="label"
  >
    <span v-if="dot" class="status-pill-dot" aria-hidden="true" />
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

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

/** 内部状态枚举 → 中文词条；调用方未传 label 时不能把英文枚举直接渲染到界面上 */
const STATUS_LABEL_KEY: Record<string, string> = {
  approved: 'workflow.status_approved',
  completed: 'workflow.status_completed',
  running: 'workflow.status_running',
  pending: 'workflow.status_pending',
  rejected: 'workflow.status_rejected',
  reject: 'workflow.status_rejected',
  cancelled: 'workflow.status_cancelled',
  draft: 'workflow.status_draft',
  withdraw: 'workflow.status_withdraw',
  withdrawn: 'workflow.status_withdraw',
  transfer: 'workflow.status_transfer',
}

const { t } = useI18n()

const label = computed(() => {
  if (props.label) return props.label
  const key = props.status ? STATUS_LABEL_KEY[props.status] : ''
  return key ? t(key) : props.status || ''
})
</script>

<style scoped>
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--app-space-4);
  max-width: 100%;
  padding: var(--app-space-2) 9px;
  border-radius: var(--radius-pill);
  font-size: var(--app-font-2xs);
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
