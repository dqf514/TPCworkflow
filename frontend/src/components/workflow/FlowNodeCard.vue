<template>
  <!-- 节点卡可点击：补 role/tabindex/键盘事件，让键盘用户也能打开节点配置。
       卡片内含删除按钮，不能改成 <button>（会形成嵌套 button，HTML 无效）。 -->
  <div
    class="flow-node-card"
    :class="[
      `type-${displayType}`,
      { clickable: canEdit, [`state-${previewState}`]: !!previewState },
    ]"
    :role="canEdit ? 'button' : undefined"
    :tabindex="canEdit ? 0 : undefined"
    :aria-label="canEdit ? `${headerTitle}：${title}` : undefined"
    @click="canEdit && emit('edit')"
    @keydown.enter.prevent="canEdit && emit('edit')"
    @keydown.space.prevent="canEdit && emit('edit')"
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
        <a-button
          size="mini"
          type="text"
          class="card-del"
          :aria-label="t('flowDesign.delete_node')"
          @click.stop
        >
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
      `${br.expr === 'default' ? t('flowDesign.branch_default_label') : t('flowDesign.branch_priority', { n: br.priority || i + 1 })}：${br.label || formatConditionExpr(br.expr, props.fieldLabelMap)}`,
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
  /* 节点高度由外层 .flow-chain 提供（--flow-node-height），窄屏可统一收敛 */
  height: var(--flow-node-height, 120px);
  width: calc(var(--flow-node-height, 120px) * 1.25);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  transition:
    box-shadow 0.25s,
    border-color 0.25s,
    opacity 0.25s;
}

.flow-node-card.type-condition {
  height: auto;
  min-height: var(--flow-node-height, 120px);
  max-height: 168px;
  width: calc(var(--flow-node-height, 120px) * 1.25);
}

.flow-node-card.state-done {
  border-color: var(--success);
  opacity: 0.92;
}

.flow-node-card.state-current {
  border-color: var(--brand);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand) 20%, transparent);
  animation: flow-node-pulse 2.2s ease-in-out infinite;
}

.flow-node-card.state-pending {
  opacity: 0.58;
}

@keyframes flow-node-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand) 18%, transparent);
  }
  50% {
    box-shadow: 0 0 0 5px color-mix(in srgb, var(--brand) 32%, transparent);
  }
}

.flow-node-card.clickable {
  cursor: pointer;
}

.flow-node-card.clickable:hover {
  box-shadow: var(--shadow-md);
}

/* 键盘焦点可见（与 main.css 的焦点环保持一致） */
.flow-node-card:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand) 16%, transparent);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: var(--app-space-6) var(--app-space-10);
  color: #fff;
  font-size: var(--app-font-xs);
  font-weight: 600;
}

.card-del {
  color: rgba(255, 255, 255, 0.85) !important;
}

.card-body {
  flex: 1;
  min-height: 0;
  padding: var(--app-space-8) var(--app-space-10);
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
  font-size: var(--app-font-sm);
  font-weight: 600;
  color: var(--text);
  margin-bottom: var(--app-space-2);
  line-height: 1.35;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-sub {
  font-size: var(--app-font-2xs);
  color: var(--text-tertiary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.cond-lines {
  margin-top: var(--app-space-6);
}

.cond-line {
  font-size: var(--app-font-xs);
  color: var(--text-secondary);
  line-height: 1.6;
  padding: var(--app-space-xs) 0;
  border-top: 1px dashed var(--border);
}

.cond-line:first-child {
  border-top: none;
}
</style>
