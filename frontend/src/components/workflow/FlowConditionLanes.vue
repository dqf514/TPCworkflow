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

            @ok="emit('remove-branch', bi)"

          >

            <a-button size="mini" type="text" status="danger" class="branch-del">删</a-button>

          </a-popconfirm>

        </div>



        <div class="branch-flow">

          <FlowConnector

            v-if="!readonly"

            direction="horizontal"

            @add="(type) => emit('insert', { path: branchPath(bi), index: -1, type })"

          />

          <FlowChainEditor

            :chain="br.chain"

            :base-path="branchPath(bi)"

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



function branchPath(bi: number) {

  return [...props.path, bi]

}

</script>



<style scoped>

.condition-fork {

  width: 100%;

  margin: 4px 0 8px;

  padding: 12px 16px 16px;

  background: linear-gradient(180deg, #fafbfc 0%, #fff 100%);

  border: 1px solid #e5e6eb;

  border-radius: 12px;

  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);

}



.fork-entry {

  display: flex;

  align-items: center;

  justify-content: center;

  gap: 8px;

  margin-bottom: 12px;

}



.fork-line-h {

  flex: 1;

  max-width: 120px;

  height: 2px;

  background: linear-gradient(90deg, transparent, #c9cdd4 20%, #c9cdd4 80%, transparent);

}



.fork-hub {

  width: 28px;

  height: 28px;

  display: flex;

  align-items: center;

  justify-content: center;

  font-size: 16px;

  color: #86909c;

  background: #f2f3f5;

  border: 2px solid #c9cdd4;

  border-radius: 4px;

  transform: rotate(45deg);

  flex-shrink: 0;

}



.fork-toolbar {

  display: flex;

  justify-content: center;

  margin-bottom: 12px;

}



.branch-stack {

  display: flex;

  flex-direction: column;

  gap: 12px;

  width: 100%;

}



.branch-row {

  display: flex;

  flex-direction: row;

  align-items: stretch;

  gap: 12px;

  width: 100%;

  min-height: 132px;

  padding: 10px 12px;

  background: #f7f8fa;

  border: 1px solid #e5e6eb;

  border-radius: 10px;

  border-left: 4px solid #86909c;

}



.branch-row:has(.branch-badge.is-default) {

  border-left-color: #165dff;

}



.branch-meta {

  flex: 0 0 168px;

  display: flex;

  flex-direction: column;

  gap: 4px;

  position: relative;

  padding-right: 8px;

  border-right: 1px dashed #e5e6eb;

}



.branch-badge {

  display: inline-block;

  font-size: 11px;

  font-weight: 700;

  color: #fff;

  background: #86909c;

  padding: 2px 8px;

  border-radius: 4px;

  width: fit-content;

}



.branch-badge.is-default {

  background: #165dff;

}



.branch-title {

  font-size: 13px;

  font-weight: 600;

  color: #1d2129;

  line-height: 1.4;

}



.branch-expr {

  font-size: 12px;

  color: #4e5969;

  line-height: 1.45;

}



.branch-del {

  align-self: flex-start;

  margin-top: 4px;

}



.branch-flow {

  flex: 1;

  min-width: 0;

  display: flex;

  flex-direction: row;

  align-items: center;

  overflow-x: auto;

  overflow-y: hidden;

  padding: 4px 0;

}



.branch-flow :deep(.flow-chain) {

  flex: 1;

  min-width: min-content;

}



.fork-merge {

  display: flex;

  align-items: center;

  justify-content: center;

  gap: 12px;

  margin-top: 12px;

  padding-top: 8px;

}



.merge-line {

  flex: 1;

  max-width: 160px;

  height: 2px;

  background: linear-gradient(90deg, transparent, #c9cdd4 30%, #c9cdd4 70%, transparent);

}



.merge-label {

  font-size: 11px;

  color: #86909c;

  white-space: nowrap;

}

</style>

