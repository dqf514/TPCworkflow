<template>
  <div class="flow-chain" role="list" aria-label="流程节点链">
    <!-- 空数据时给出明确提示，避免只渲染一片空白画布 -->
    <div v-if="!chain.length" class="flow-chain-empty" role="status">
      {{ t('workflow.flow_chain_empty') }}
    </div>
    <template v-for="(row, ri) in layoutRows" :key="row.key">
      <div
        class="flow-row-wrap"
        role="listitem"
        :class="{ 'is-condition': row.units[0]?.kind === 'condition-block' }"
      >
        <div class="flow-row">
          <template v-for="unit in row.units" :key="unit.key">
            <template v-if="unit.kind === 'segment'">
              <FlowNodeCard
                :segment="chain[unit.index]"
                :field-label-map="fieldLabelMap"
                :role-name-map="roleNameMap"
                :preview-state="nodeStateFor(chain[unit.index])"
                @edit="emit('edit', pathFor(unit.index))"
                @remove="emit('remove', pathFor(unit.index))"
              />
              <FlowConnector
                v-if="showConnectorAfter(chain[unit.index], unit.index)"
                :readonly="readonly"
                direction="horizontal"
                @add="(type) => emit('insert', { path: props.basePath || [], index: unit.index, type })"
              />
            </template>

            <template v-else-if="unit.kind === 'condition-block'">
              <div class="condition-block">
                <FlowNodeCard
                  :segment="chain[unit.index]"
                  :field-label-map="fieldLabelMap"
                  :role-name-map="roleNameMap"
                  :preview-state="nodeStateFor(chain[unit.index])"
                  @edit="emit('edit', pathFor(unit.index))"
                  @remove="emit('remove', pathFor(unit.index))"
                />
                <FlowConditionLanes
                  v-if="chain[unit.index].kind === 'condition'"
                  :block="chain[unit.index]"
                  :path="pathFor(unit.index)"
                  :field-label-map="fieldLabelMap"
                  :role-name-map="roleNameMap"
                  @insert="(p) => emit('insert', p)"
                  @edit="(p) => emit('edit', p)"
                  :readonly="readonly"
                  :node-states="nodeStates"
                  @remove="(p) => emit('remove', p)"
                  @add-branch="emit('add-branch', pathFor(unit.index))"
                  @remove-branch="(bi) => emit('remove-branch', { path: pathFor(unit.index), branchIndex: bi })"
                />
                <FlowConnector
                  :readonly="readonly"
                  direction="horizontal"
                  @add="(type) => emit('insert', { path: props.basePath || [], index: unit.index, type })"
                />
              </div>
            </template>
          </template>
        </div>

        <div
          v-if="ri < layoutRows.length - 1 && row.units[0]?.kind !== 'condition-block'"
          class="flow-row-break"
        >
          <div class="break-vert" />
          <div class="break-hor" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import FlowConditionLanes from '@/components/workflow/FlowConditionLanes.vue'
import FlowConnector from '@/components/workflow/FlowConnector.vue'
import FlowNodeCard from '@/components/workflow/FlowNodeCard.vue'
import { useFlowSnakeLayout } from '@/composables/useFlowSnakeLayout'
import type { FlowChain, FlowSegment } from '@/utils/workflowFlowGraph'

const { t } = useI18n()

const props = defineProps<{
  chain: FlowChain
  basePath?: number[]
  fieldLabelMap: Record<string, string>
  roleNameMap: Record<string, string>
  readonly?: boolean
  nodeStates?: Record<string, 'done' | 'current' | 'pending'>
}>()

const { layoutRows } = useFlowSnakeLayout(toRef(props, 'chain'))

function nodeStateFor(seg: FlowSegment): 'done' | 'current' | 'pending' | undefined {
  if (!props.nodeStates) return undefined
  return props.nodeStates[seg.id]
}

const emit = defineEmits<{
  insert: [payload: { path: number[]; index: number; type: string }]
  edit: [path: number[]]
  remove: [path: number[]]
  'add-branch': [path: number[]]
  'remove-branch': [payload: { path: number[]; branchIndex: number }]
}>()

function pathFor(idx: number) {
  return [...(props.basePath || []), idx]
}

function showConnectorAfter(seg: FlowSegment, idx: number) {
  if (seg.kind === 'node' && seg.type === 'end') return false
  if (seg.kind === 'condition') return false
  return idx < props.chain.length - 1
}
</script>

<style scoped>
.flow-chain {
  /* 节点卡高度令牌：窄屏统一收敛，避免 375px 视口横向溢出 */
  --flow-node-height: 120px;
  width: 100%;
  max-width: 100%;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.flow-chain-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 96px;
  padding: 1.5rem;
  border: 1px dashed var(--border);
  border-radius: var(--radius-md);
  color: var(--text-tertiary);
  font-size: var(--app-font-md);
}

.flow-row-wrap {
  width: 100%;
  position: relative;
}

.flow-row {
  display: flex;
  flex-direction: row;
  /* 窄屏允许换行，避免一行 5 个节点（≈750px）在手机上溢出 */
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-start;
  min-height: 140px;
  row-gap: var(--app-space-8);
}

.condition-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  gap: var(--app-space-8);
}

.flow-row-break {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  height: 28px;
  /* 折返连接线的横向偏移跟随节点高度令牌，窄屏不再错位 */
  margin-left: calc(var(--flow-node-height) * 0.5);
}

.break-vert {
  width: 2px;
  height: 14px;
  background: #c9cdd4;
}

.break-hor {
  width: 48px;
  height: 2px;
  background: #c9cdd4;
}

@media (max-width: 767px) {
  .flow-chain {
    --flow-node-height: 88px;
  }

  .flow-row {
    min-height: 112px;
  }
}
</style>
