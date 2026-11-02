<template>

  <div class="condition-fork">

    <div class="fork-entry">

      <div class="fork-line-h" />

      <div class="fork-hub" title="条件分支">◇</div>

      <div class="fork-line-h" />

    </div>



    <div v-if="!readonly" class="fork-toolbar">

      <a-button size="mini" type="outline" @click="emit('add-branch')">

        {{ t('flowDesign.add_branch') }}

      </a-button>

    </div>



    <div class="branch-stack">

      <div

        v-for="(br, bi) in sortedBranches"

        :key="br.id"

        class="branch-row"

      >

        <div class="branch-meta">

          <div class="branch-badge" :class="{ 'is-default': br.expr === 'default' }">

            {{ br.expr === 'default' ? t('flowDesign.default_branch') : `P${br.priority}` }}

          </div>

          <div class="branch-title">{{ br.label || formatConditionExpr(br.expr, fieldLabelMap) }}</div>

          <div v-if="br.expr !== 'default'" class="branch-expr">

            {{ formatConditionExpr(br.expr, fieldLabelMap) }}

          </div>

          <a-popconfirm

            v-if="!readonly && br.expr !== 'default'"

            :content="t('flowDesign.delete_branch_confirm')"

            position="top"

            :popup-container="popupContainer"

            @ok="emit('remove-branch', branchIndex(br))"

          >

            <a-button size="mini" type="text" status="danger" class="branch-del">删</a-button>

          </a-popconfirm>

        </div>



        <div class="branch-flow">

          <FlowConnector

            v-if="!readonly"

            direction="horizontal"

            @add="(type) => emit('insert', { path: branchPath(branchIndex(br)), index: -1, type })"

          />

          <FlowChainEditor

            :chain="br.chain"

            :base-path="branchPath(branchIndex(br))"

            :field-label-map="fieldLabelMap"

            :role-name-map="roleNameMap"

            :readonly="readonly"

            :node-states="nodeStates"

            @insert="(p) => emit('insert', p)"

            @edit="(p) => emit('edit', p)"

            @remove="(p) => emit('remove', p)"

            @add-branch="emit('add-branch')"

            @remove-branch="(p) => emit('remove-branch', p)"

          />

          <FlowConnector

            v-if="!readonly && br.chain.length"

            direction="horizontal"

            readonly

          />

        </div>

      </div>

    </div>



    <div class="fork-merge">

      <div class="merge-line" />

      <span class="merge-label">{{ t('flowDesign.branch_merge') }}</span>

      <div class="merge-line" />

    </div>

  </div>

</template>



<script setup lang="ts">

import { computed } from 'vue'

import { useI18n } from 'vue-i18n'

import FlowChainEditor from '@/components/workflow/FlowChainEditor.vue'

import FlowConnector from '@/components/workflow/FlowConnector.vue'
import { useFlowDesignerPopup } from '@/composables/useFlowDesignerPopup'
import {

  formatConditionExpr,

  type FlowConditionBlock,

  type FlowConditionBranch,

} from '@/utils/workflowFlowGraph'



const props = defineProps<{

  block: FlowConditionBlock

  path: number[]

  fieldLabelMap: Record<string, string>

  roleNameMap: Record<string, string>

  readonly?: boolean

  nodeStates?: Record<string, 'done' | 'current' | 'pending'>

}>()



const emit = defineEmits<{

  insert: [payload: { path: number[]; index: number; type: string }]

  edit: [path: number[]]

  remove: [path: number[]]

  'add-branch': []

  'remove-branch': [branchIndex: number]

}>()



const { t } = useI18n()
const popupContainer = useFlowDesignerPopup()



const sortedBranches = computed(() =>

  [...props.block.branches].sort((a, b) => a.priority - b.priority),

)

/**
 * 排序后的下标不能直接当数组下标使用：
 * 泳道按 priority 排序显示，而增删分支用的是原始数组下标，需按 id 回查。
 */
function branchIndex(br: FlowConditionBranch): number {

  const idx = props.block.branches.findIndex((b) => b.id === br.id)

  return idx >= 0 ? idx : 0

}



function branchPath(bi: number) {

  return [...props.path, bi]

}

</script>



<style scoped>

.condition-fork {

  width: 100%;

  margin: var(--app-space-xs) 0 var(--app-space-sm);

  padding: var(--app-space-md) var(--app-space-lg) var(--app-space-lg);

  background: linear-gradient(180deg, var(--surface-muted) 0%, var(--surface) 100%);

  border: 1px solid var(--border);

  border-radius: var(--radius-lg);

  box-shadow: var(--shadow-xs);

}



.fork-entry {

  display: flex;

  align-items: center;

  justify-content: center;

  gap: var(--app-space-8);

  margin-bottom: var(--app-space-12);

}



.fork-line-h {

  flex: 1;

  max-width: 120px;

  height: 2px;

  background: linear-gradient(90deg, transparent, var(--border-strong) 20%, var(--border-strong) 80%, transparent);

}



.fork-hub {

  width: 28px;

  height: 28px;

  display: flex;

  align-items: center;

  justify-content: center;

  font-size: var(--app-font-lg);

  color: var(--text-tertiary);

  background: var(--surface-muted);

  border: 2px solid var(--border-strong);

  border-radius: var(--radius-sm);

  transform: rotate(45deg);

  flex-shrink: 0;

}



.fork-toolbar {

  display: flex;

  justify-content: center;

  margin-bottom: var(--app-space-12);

}



.branch-stack {

  display: flex;

  flex-direction: column;

  gap: var(--app-space-12);

  width: 100%;

}



.branch-row {

  display: flex;

  flex-direction: row;

  align-items: stretch;

  gap: var(--app-space-12);

  width: 100%;

  min-height: 132px;

  padding: var(--app-space-10) var(--app-space-12);

  background: var(--surface-muted);

  border: 1px solid var(--border);

  border-radius: var(--radius-lg);

  border-left: 4px solid var(--text-tertiary);

}



.branch-row:has(.branch-badge.is-default) {

  border-left-color: var(--brand);

}



.branch-meta {

  flex: 0 0 168px;

  display: flex;

  flex-direction: column;

  gap: var(--app-space-xs);

  position: relative;

  padding-right: var(--app-space-sm);

  border-right: 1px dashed var(--border);

}



.branch-badge {

  display: inline-block;

  font-size: var(--app-font-2xs);

  font-weight: 700;

  color: var(--brand-contrast);

  background: var(--text-tertiary);

  padding: var(--app-space-2) var(--app-space-8);

  border-radius: var(--radius-sm);

  width: fit-content;

}



.branch-badge.is-default {

  background: var(--brand);

}



.branch-title {

  font-size: var(--app-font-sm);

  font-weight: 600;

  color: var(--text);

  line-height: 1.4;

}



.branch-expr {

  font-size: var(--app-font-xs);

  color: var(--text-secondary);

  line-height: 1.45;

}



.branch-del {

  align-self: flex-start;

  margin-top: var(--app-space-4);

}



.branch-flow {

  flex: 1;

  min-width: 0;

  display: flex;

  flex-direction: row;

  align-items: center;

  overflow-x: auto;

  overflow-y: hidden;

  padding: var(--app-space-4) 0;

}



.branch-flow :deep(.flow-chain) {

  flex: 1;

  min-width: min-content;

}



.fork-merge {

  display: flex;

  align-items: center;

  justify-content: center;

  gap: var(--app-space-12);

  margin-top: var(--app-space-12);

  padding-top: var(--app-space-8);

}



.merge-line {

  flex: 1;

  max-width: 160px;

  height: 2px;

  background: linear-gradient(90deg, transparent, var(--border-strong) 30%, var(--border-strong) 70%, transparent);

}



.merge-label {

  font-size: var(--app-font-2xs);

  color: var(--text-tertiary);

  white-space: nowrap;

}

</style>

