<template>
  <div
    class="flow-node-card"
    :class="[
      `type-${displayType}`,
      { clickable: canEdit, [`state-${previewState}`]: !!previewState },
    ]"
    @click="canEdit && emit('edit')"
  >
    <div class="card-header" :style="{ background: meta.header }">
      <span class="card-type">{{ headerTitle }}</span>
      <a-popconfirm
        v-if="canDelete"
        :content="t('flowDesign.delete_node_confirm')"
        position="top"
        :popup-container="popupContainer"
        @ok="emit('remove')"
      >
        <a-button size="mini" type="text" class="card-del" @click.stop>
          ×
        </a-button>
      </a-popconfirm>
    </div>
    <div class="card-body">
      <div class="card-title">{{ title }}</div>
      <div v-if="subtitle" class="card-sub">{{ subtitle }}</div>
      <div v-if="conditionLines.length" class="cond-lines">
        <div v-for="(line, i) in conditionLines" :key="i" class="cond-line">{{ line }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFlowDesignerPopup } from '@/composables/useFlowDesignerPopup'
import {
  NODE_TYPE_META,
  useWorkflowAssignee,
  type WorkflowNodeConfig,
} from '@/composables/useWorkflowAssignee'
import {
  formatConditionExpr,
  type FlowConditionBlock,
  type FlowSegment,
} from '@/utils/workflowFlowGraph'

const props = defineProps<{
  segment: FlowSegment
  fieldLabelMap: Record<string, string>
  roleNameMap: Record<string, string>
  /** 只读预览：done | current | pending */
  previewState?: 'done' | 'current' | 'pending'
}>()

const emit = defineEmits<{ edit: []; remove: [] }>()

const { t } = useI18n()
const popupContainer = useFlowDesignerPopup()
const { nodeDisplayTitle, summarizeConfig } = useWorkflowAssignee()

const displayType = computed(() =>
  props.segment.kind === 'node' ? props.segment.type : 'condition',
)

const meta = computed(() => NODE_TYPE_META[displayType.value] || NODE_TYPE_META.approver)

const config = computed(() =>
  props.segment.kind === 'node'
    ? props.segment.config
    : (props.segment as FlowConditionBlock).config,
)

const title = computed(() =>
  nodeDisplayTitle(displayType.value, config.value as WorkflowNodeConfig),
)

const subtitle = computed(() => {
  if (props.segment.kind === 'condition') return ''
  return summarizeConfig(
    props.segment.type,
    props.segment.config,
    props.roleNameMap,
  )
})

const headerTitle = computed(() => t(meta.value.labelKey))

const conditionLines = computed(() => {
  if (props.segment.kind !== 'condition') return []
  // 设计态由 FlowConditionLanes 展示分支，卡片内不再重复
  if (!props.previewState) return []
  const sorted = [...props.segment.branches].sort((a, b) => a.priority - b.priority)
  return sorted.map(
    (br, i) =>
      `${br.expr === 'default' ? '默认' : `优先级${br.priority || i + 1}`}：${br.label || formatConditionExpr(br.expr, props.fieldLabelMap)}`,
  )
})

const canEdit = computed(
  () =>
    !props.previewState &&
    (displayType.value !== 'end' || props.segment.kind === 'condition'),
)

const canDelete = computed(() => {
  if (props.segment.kind !== 'node') return false
  return props.segment.type !== 'start' && props.segment.type !== 'end'
})
</script>

<style scoped>
.flow-node-card {
  --flow-node-height: 120px;
  height: var(--flow-node-height);
  width: calc(var(--flow-node-height) * 1.25);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e5e6eb;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition:
    box-shadow 0.25s,
    border-color 0.25s,
    opacity 0.25s;
}

.flow-node-card.type-condition {
  height: auto;
  min-height: var(--flow-node-height);
  max-height: 168px;
  width: calc(var(--flow-node-height) * 1.25);
}

.flow-node-card.state-done {
  border-color: #00b42a;
  opacity: 0.92;
}

.flow-node-card.state-current {
  border-color: #165dff;
  box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.2);
  animation: flow-node-pulse 2.2s ease-in-out infinite;
}

.flow-node-card.state-pending {
  opacity: 0.58;
}

@keyframes flow-node-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.18);
  }
  50% {
    box-shadow: 0 0 0 5px rgba(22, 93, 255, 0.32);
  }
}

.flow-node-card.clickable {
  cursor: pointer;
}

.flow-node-card.clickable:hover {
  box-shadow: 0 4px 14px rgba(22, 93, 255, 0.12);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 6px 10px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.card-del {
  color: rgba(255, 255, 255, 0.85) !important;
}

.card-body {
  flex: 1;
  min-height: 0;
  padding: 8px 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.flow-node-card.type-condition .card-body {
  justify-content: flex-start;
  overflow: auto;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: #1d2129;
  margin-bottom: 2px;
  line-height: 1.35;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-sub {
  font-size: 11px;
  color: #86909c;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.cond-lines {
  margin-top: 6px;
}

.cond-line {
  font-size: 12px;
  color: #4e5969;
  line-height: 1.6;
  padding: 4px 0;
  border-top: 1px dashed #e5e6eb;
}

.cond-line:first-child {
  border-top: none;
}
</style>
