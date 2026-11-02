<template>
  <div class="instance-context-header">
    <div class="ctx-head">
      <div class="ctx-main">
        <h2 v-if="title" class="ctx-title">{{ title }}</h2>
        <div class="ctx-meta">
          <span v-if="meta.displayNo || meta.id" class="ctx-no">
            {{ meta.displayNo || `#${meta.id}` }}
          </span>
          <span v-if="meta.companyName" class="ctx-meta-item">{{ meta.companyName }}</span>
          <span v-if="meta.departmentPath || meta.departmentName" class="ctx-meta-item">
            {{ meta.departmentPath || meta.departmentName }}
          </span>
          <span v-if="meta.initiatorName" class="ctx-meta-item">{{ meta.initiatorName }}</span>
          <span v-if="meta.startedAt" class="ctx-meta-item">
            {{ formatPrintDateTime(meta.startedAt) }}
          </span>
        </div>
      </div>
      <StatusPill
        v-if="meta.status"
        :status="meta.status"
        :label="statusLabel || instanceStatusLabel(meta.status)"
        class="ctx-status"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import StatusPill from '@/components/workflow/StatusPill.vue'
import { formatPrintDateTime, instanceStatusLabel } from '@/utils/printFormat'

export interface InstanceContextMeta {
  id?: number
  displayNo?: string
  status?: string
  definitionName?: string
  initiatorName?: string
  companyName?: string
  departmentName?: string
  departmentPath?: string
  startedAt?: string | null
}

withDefaults(
  defineProps<{
    title?: string
    meta: InstanceContextMeta
    statusLabel?: string
  }>(),
  { statusLabel: '' },
)
</script>

<style scoped>
.instance-context-header {
  margin-bottom: var(--app-space-16);
}

.ctx-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--app-space-10) var(--app-space-16);
}

.ctx-main {
  min-width: 0;
}

.ctx-title {
  margin: 0 0 var(--app-space-6);
  font-size: var(--app-font-xl);
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text);
  line-height: 1.35;
}

.ctx-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--app-space-6) var(--app-space-14);
  font-size: var(--app-font-sm);
  color: var(--text-secondary);
}

.ctx-meta-item {
  position: relative;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ctx-no {
  padding: 1px var(--app-space-8);
  border-radius: var(--radius-sm);
  background: var(--surface-muted);
  font-family: ui-monospace, 'Cascadia Code', 'Segoe UI Mono', monospace;
  font-size: var(--app-font-xs);
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.ctx-status {
  flex-shrink: 0;
  margin-top: var(--app-space-2);
}

@media (max-width: 640px) {
  .ctx-title {
    font-size: 1.0625rem;
  }

  .ctx-meta {
    gap: var(--app-space-4) var(--app-space-10);
  }
}
</style>
