<template>
  <div class="wf-flow" :class="{ 'is-runtime': mode === 'runtime' }">
    <div v-if="title || durationText" class="wf-flow-head">
      <span v-if="title" class="wf-flow-title">{{ title }}</span>
      <span v-if="durationText" class="wf-flow-duration">{{ durationText }}</span>
    </div>

    <ol v-if="steps.length" class="wf-flow-steps">
      <li
        v-for="(step, index) in steps"
        :key="step.id"
        class="wf-step"
        :class="[`is-${stepState(step)}`, { 'is-first': index === 0 }]"
      >
        <span class="wf-step-marker">
          <icon-check v-if="stepState(step) === 'done'" />
          <span v-else class="wf-step-num">{{ index + 1 }}</span>
        </span>
        <span class="wf-step-label">{{ step.label }}</span>
        <span v-if="stepState(step) === 'current'" class="wf-step-tag">
          {{ t('workflow.flow_current_node') }}
        </span>
      </li>
    </ol>

    <p v-else class="wf-flow-empty">{{ t('workflow.flow_preview_empty') }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { IconCheck } from '@arco-design/web-vue/es/icon'
import { useFormPreviewVariables } from '@/composables/useFormPreviewVariables'
import { formatStepDuration } from '@/utils/formatStepDuration'
import {
  buildFlowNodeStates,
  type FlowNodePreviewState,
} from '@/utils/workflowFlowProgress'
import {
  flattenFlowChainToTextSteps,
  graphToFlowChain,
  resolvePreviewFlowChain,
  type FlowChain,
  type FlowTextStep,
  type ProcessGraph,
} from '@/utils/workflowFlowGraph'

const props = withDefaults(
  defineProps<{
    processGraph?: ProcessGraph
    mode?: 'apply' | 'runtime'
    title?: string
    status?: string
    currentNodeIds?: string[]
    completedNodeIds?: string[]
    stepStartedAt?: string | null
    /** 填表/详情预览：根据表单值解析条件分支 */
    formData?: Record<string, unknown>
  }>(),
  {
    mode: 'apply',
  },
)

const { t } = useI18n()

const nowTick = ref(Date.now())
let tickTimer: ReturnType<typeof setInterval> | null = null

const previewVariables = useFormPreviewVariables(() => props.formData)

const chain = ref<FlowChain>([])

function recomputeChain() {
  const full = graphToFlowChain(props.processGraph)
  if (props.mode === 'apply' || props.formData) {
    chain.value = resolvePreviewFlowChain(full, previewVariables.value)
    return
  }
  chain.value = full
}

watch(
  () => [props.processGraph, props.mode, previewVariables.value] as const,
  () => recomputeChain(),
  { deep: true, immediate: true },
)

const steps = computed(() => flattenFlowChainToTextSteps(chain.value))

const nodeStates = computed<Record<string, FlowNodePreviewState>>(() =>
  buildFlowNodeStates(chain.value, {
    mode: props.mode,
    status: props.status,
    currentNodeIds: props.currentNodeIds,
    completedNodeIds: props.completedNodeIds,
  }),
)

const currentStepId = computed(() => {
  if (props.mode === 'apply') {
    return steps.value.find((s) => s.type === 'start')?.id || null
  }
  const ids = props.currentNodeIds || []
  if (ids.length) return ids[0]
  const running = steps.value.find((s) => nodeStates.value[s.id] === 'current')
  return running?.id || null
})

function isCurrentStep(step: FlowTextStep) {
  if (currentStepId.value && step.id === currentStepId.value) return true
  if (props.mode === 'runtime' && nodeStates.value[step.id] === 'current') return true
  return false
}

function stepState(step: FlowTextStep): FlowNodePreviewState {
  if (isCurrentStep(step)) return 'current'
  return nodeStates.value[step.id] === 'done' ? 'done' : 'pending'
}

const durationText = computed(() => {
  if (props.mode !== 'runtime' || !props.stepStartedAt) return ''
  if (props.status && !['running', 'pending'].includes(props.status)) return ''
  nowTick.value
  return formatStepDuration(props.stepStartedAt)
})

onMounted(() => {
  if (props.mode === 'runtime' && props.stepStartedAt) {
    tickTimer = setInterval(() => {
      nowTick.value = Date.now()
    }, 30000)
  }
})

onBeforeUnmount(() => {
  if (tickTimer) clearInterval(tickTimer)
})
</script>

<style scoped>
.wf-flow {
  width: 100%;
  min-width: 0;
}

.wf-flow-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.wf-flow-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text);
}

.wf-flow-duration {
  font-size: 0.6875rem;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.wf-flow-steps {
  display: flex;
  align-items: flex-start;
  margin: 0;
  padding: 2px 0 4px;
  overflow-x: auto;
  list-style: none;
  scrollbar-width: thin;
}

.wf-step {
  position: relative;
  display: flex;
  flex: 1 1 0;
  min-width: 84px;
  max-width: 180px;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 0 6px;
  text-align: center;
}

.wf-step::before {
  content: '';
  position: absolute;
  top: 11px;
  right: 50%;
  width: 100%;
  height: 2px;
  border-radius: 1px;
  background: var(--divider);
}

.wf-step.is-first::before {
  display: none;
}

.wf-step.is-done::before,
.wf-step.is-current::before {
  background: color-mix(in srgb, var(--success) 42%, var(--surface));
}

.wf-step-marker {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 1.5px solid var(--border-input);
  border-radius: 50%;
  background: var(--surface);
  color: var(--text-tertiary);
  font-size: 10.5px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  transition:
    border-color var(--dur-base) var(--ease-out),
    background-color var(--dur-base) var(--ease-out),
    box-shadow var(--dur-base) var(--ease-out);
}

.wf-step.is-done .wf-step-marker {
  border-color: var(--success);
  background: var(--success);
  color: var(--brand-contrast);
  font-size: 12px;
}

.wf-step.is-current .wf-step-marker {
  border-color: var(--brand);
  background: var(--brand);
  color: var(--brand-contrast);
  box-shadow: 0 0 0 4px var(--brand-soft);
}

.wf-step-label {
  display: -webkit-box;
  overflow: hidden;
  font-size: 0.71875rem;
  line-height: 1.4;
  color: var(--text-tertiary);
  word-break: break-word;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.wf-step.is-done .wf-step-label {
  color: var(--text-secondary);
}

.wf-step.is-current .wf-step-label {
  font-weight: 600;
  color: var(--brand);
}

.wf-step-tag {
  padding: 0 5px;
  border-radius: var(--radius-pill);
  background: var(--brand-soft);
  color: var(--brand);
  font-size: 9.5px;
  font-weight: 600;
  line-height: 1.6;
  white-space: nowrap;
}

.wf-flow-empty {
  margin: 0;
  padding: 4px 0;
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

@media (max-width: 640px) {
  .wf-step {
    flex-basis: 96px;
  }
}
</style>
