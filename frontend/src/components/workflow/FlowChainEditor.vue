<template>
  <div class="flow-chain">
    <template v-for="(row, ri) in layoutRows" :key="row.key">
      <div
        class="flow-row-wrap"
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
import FlowConditionLanes from '@/components/workflow/FlowConditionLanes.vue'
import FlowConnector from '@/components/workflow/FlowConnector.vue'
import FlowNodeCard from '@/components/workflow/FlowNodeCard.vue'
import { useFlowSnakeLayout } from '@/composables/useFlowSnakeLayout'
import type { FlowChain, FlowSegment } from '@/utils/workflowFlowGraph'

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
  width: 100%;
  max-width: 100%;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.flow-row-wrap {
  width: 100%;
  position: relative;
}

.flow-row {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: flex-start;
  min-height: 140px;
}

.condition-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  gap: 8px;
}

.flow-row-break {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  height: 28px;
  margin-left: 75px;
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
</style>
