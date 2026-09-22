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
        :form-schema="formSchema"
        :form-data="formData"
        mode="runtime"
        :status="status"
        :current-node-ids="currentNodeIds"
        :completed-node-ids="completedNodeIds"
        :step-started-at="stepStartedAt"
        :show-zoom-hint="showZoomHint"
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
import type { FormSchema } from '@/types/form'

const props = withDefaults(
  defineProps<{
    title?: string
    status?: string
    statusLabel?: string
    processGraph?: ProcessGraph
    formSchema?: FormSchema
    formData?: Record<string, unknown>
    currentNodeIds?: string[]
    completedNodeIds?: string[]
    stepStartedAt?: string | null
    timeline?: ApprovalTimelineItem[]
    showActor?: boolean
    showZoomHint?: boolean
  }>(),
  {
    timeline: () => [],
    showActor: true,
    showZoomHint: true,
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
  border-radius: 12px;
  border: 1px solid #e5e6eb;
  background: #fff;
  overflow: hidden;
}

.wf-progress-panel__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 16px 10px;
  border-bottom: 1px solid #f2f3f5;
  background: linear-gradient(180deg, #fafbfc 0%, #fff 100%);
}

.wf-progress-panel__title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
}

.wf-progress-panel__status {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: #f2f3f5;
  color: #4e5969;
}

.wf-progress-panel__status.is-running {
  background: #e8f3ff;
  color: #165dff;
}

.wf-progress-panel__status.is-approved {
  background: #e8ffea;
  color: #00b42a;
}

.wf-progress-panel__status.is-rejected {
  background: #ffece8;
  color: #f53f3f;
}

.wf-progress-panel__status.is-cancelled {
  background: #f2f3f5;
  color: #86909c;
}

.wf-progress-panel__flow {
  padding: 12px 16px 4px;
}

.wf-progress-panel__flow :deep(.wf-flow-preview) {
  margin-top: 0;
}

.wf-progress-panel__flow :deep(.wf-flow-preview-viewport) {
  border: none;
  background: #f7f8fa;
  padding: 12px 10px;
}

.wf-progress-panel__divider {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 16px 0;
  color: #86909c;
  font-size: 12px;
}

.wf-progress-panel__divider::before,
.wf-progress-panel__divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, #e5e6eb 20%, #e5e6eb 80%, transparent);
}

.wf-progress-panel__timeline {
  padding: 8px 16px 12px;
}

@media (max-width: 767px) {
  .wf-progress-panel__head {
    padding: 12px 14px 8px;
  }

  .wf-progress-panel__flow,
  .wf-progress-panel__timeline {
    padding-left: 12px;
    padding-right: 12px;
  }
}
</style>
