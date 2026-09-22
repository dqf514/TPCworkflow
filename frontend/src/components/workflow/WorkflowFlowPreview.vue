<template>
  <div class="wf-flow-textline" :class="{ 'is-runtime': mode === 'runtime' }">
    <div v-if="title || durationText" class="wf-flow-textline__head">
      <span v-if="title" class="wf-flow-textline__title">{{ title }}</span>
      <span v-if="durationText" class="wf-flow-textline__duration">{{ durationText }}</span>
    </div>
    <p v-if="steps.length" class="wf-flow-textline__track">
      <template v-for="(step, index) in steps" :key="step.id">
        <span v-if="index > 0" class="wf-flow-textline__sep">&gt;&gt;</span>
        <span class="wf-flow-textline__step" :class="{ 'is-current': isCurrentStep(step) }">
          <span class="wf-flow-textline__num">{{ index + 1 }}.</span>
          {{ step.label }}
          <span v-if="isCurrentStep(step)" class="wf-flow-textline__current-tag">
            （{{ t('workflow.flow_current_node') }}）
          </span>
        </span>
      </template>
    </p>
    <p v-else class="wf-flow-textline__empty">{{ t('workflow.flow_preview_empty') }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
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
.wf-flow-textline {
  margin-top: 16px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  background: #f7f8fa;
}

.wf-flow-textline.is-runtime {
  background: linear-gradient(180deg, #f7f8fa 0%, #f2f6ff 100%);
}

.wf-flow-textline__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.wf-flow-textline__title {
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
}

.wf-flow-textline__duration {
  font-size: 11px;
  color: #86909c;
}

.wf-flow-textline__track {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: #4e5969;
  word-break: break-word;
}

.wf-flow-textline__step {
  display: inline;
}

.wf-flow-textline__step.is-current {
  font-weight: 600;
  color: #1d2129;
}

.wf-flow-textline__num {
  margin-right: 2px;
}

.wf-flow-textline__current-tag {
  font-weight: 600;
}

.wf-flow-textline__sep {
  margin: 0 6px;
  color: #c9cdd4;
  font-weight: 400;
}

.wf-flow-textline__empty {
  margin: 0;
  font-size: 13px;
  color: #86909c;
}
</style>
