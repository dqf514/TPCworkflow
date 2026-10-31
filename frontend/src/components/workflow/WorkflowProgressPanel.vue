<template>
  <div class="wf-progress-panel">
    <div class="wf-progress-panel__head">
      <h3 class="wf-progress-panel__title">{{ title || t('workflow.flow_progress_title') }}</h3>
      <span v-if="statusLabel" class="wf-progress-panel__status" :class="statusToneClass">
        {{ statusLabel }}
      </span>
    </div>

    <div v-if="hasFlow" class="wf-progress-panel__flow">
      <WorkflowFlowPreview
        :process-graph="processGraph"
        :form-data="formData"
        mode="runtime"
        :status="status"
        :current-node-ids="currentNodeIds"
        :completed-node-ids="completedNodeIds"
        :step-started-at="stepStartedAt"
      />
    </div>

    <div v-if="hasFlow && hasTimeline" class="wf-progress-panel__divider">
      <span>{{ t('workflow.progress_records') }}</span>
    </div>

    <div v-if="hasTimeline" class="wf-progress-panel__timeline">
      <ApprovalTimeline :items="timeline" :show-actor="showActor" compact />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import WorkflowFlowPreview from '@/components/workflow/WorkflowFlowPreview.vue'
import ApprovalTimeline, { type ApprovalTimelineItem } from '@/components/workflow/ApprovalTimeline.vue'
import type { ProcessGraph } from '@/utils/workflowFlowGraph'

const props = withDefaults(
  defineProps<{
    title?: string
    status?: string
    statusLabel?: string
    processGraph?: ProcessGraph
    formData?: Record<string, unknown>
    currentNodeIds?: string[]
    completedNodeIds?: string[]
    stepStartedAt?: string | null
    timeline?: ApprovalTimelineItem[]
    showActor?: boolean
  }>(),
  {
    timeline: () => [],
    showActor: true,
  },
)

const { t } = useI18n()

const hasFlow = computed(() => !!(props.processGraph?.nodes?.length))
const hasTimeline = computed(() => (props.timeline?.length || 0) > 0)

const statusToneClass = computed(() => {
  const s = props.status || ''
  if (s === 'approved') return 'is-approved'
  if (s === 'rejected') return 'is-rejected'
  if (s === 'cancelled') return 'is-cancelled'
  if (s === 'running') return 'is-running'
  return ''
})
</script>

<style scoped>
.wf-progress-panel {
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  background: var(--surface);
  overflow: hidden;
}

.wf-progress-panel__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 13px 16px;
  border-bottom: 1px solid var(--divider);
}

.wf-progress-panel__title {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text);
}

.wf-progress-panel__status {
  display: inline-flex;
  align-items: center;
  padding: 2px 9px;
  border-radius: var(--radius-pill);
  font-size: 11.5px;
  font-weight: 500;
  background: var(--surface-muted);
  color: var(--text-secondary);
}

.wf-progress-panel__status.is-running {
  background: var(--info-soft);
  color: var(--info);
}

.wf-progress-panel__status.is-approved {
  background: var(--success-soft);
  color: var(--success);
}

.wf-progress-panel__status.is-rejected {
  background: var(--danger-soft);
  color: var(--danger);
}

.wf-progress-panel__status.is-cancelled {
  background: var(--surface-muted);
  color: var(--text-tertiary);
}

.wf-progress-panel__flow {
  padding: 12px 14px;
  margin: 12px 14px 4px;
  border-radius: var(--radius-md);
  background: var(--surface-muted);
}

.wf-progress-panel__divider {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px 0;
  color: var(--text-tertiary);
  font-size: 0.6875rem;
}

.wf-progress-panel__divider::before,
.wf-progress-panel__divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border) 20%, var(--border) 80%, transparent);
}

.wf-progress-panel__timeline {
  padding: 8px 16px 14px;
}

@media (max-width: 767px) {
  .wf-progress-panel__head {
    padding: 12px 14px;
  }

  .wf-progress-panel__flow {
    margin: 10px 10px 2px;
    padding: 10px 10px;
  }

  .wf-progress-panel__timeline {
    padding-left: 12px;
    padding-right: 12px;
  }
}
</style>
