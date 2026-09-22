<template>
  <div ref="rootRef" class="wf-vertical-designer" :class="{ 'is-fullscreen': fullscreen }">
    <div class="designer-toolbar">
      <span class="toolbar-label">{{ t('flowDesign.auto_save_hint') }}</span>
      <a-button size="small" type="outline" class="ml-auto" @click="toggleFullscreen">
        {{ fullscreen ? t('flowDesign.exit_fullscreen') : t('flowDesign.fullscreen') }}
      </a-button>
    </div>

    <div class="designer-scroll">
      <div class="flow-canvas-outer">
        <div class="flow-canvas">
        <FlowChainEditor
          :chain="flowChain"
          :field-label-map="fieldLabelMap"
          :role-name-map="roleNameMap"
          @insert="onInsert"
          @edit="openEditor"
          @remove="onRemove"
          @add-branch="onAddBranch"
          @remove-branch="onRemoveBranch"
        />
        </div>
      </div>
    </div>

    <WorkflowNodeConfigDrawer
      :visible="panelOpen"
      :node-type="editorNodeType"
      :node-id="editorNodeId"
      :config="editorConfig"
      :branches="editorBranches"
      :form-schema="formSchema"
      :target-node-ids="allNodeIds"
      :visual-mode="true"
      :embed-container="fullscreen ? rootRef : null"
      @close="panelOpen = false"
      @save="onDrawerSave"
      @delete="onDrawerDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, provide, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FlowChainEditor from '@/components/workflow/FlowChainEditor.vue'
import WorkflowNodeConfigDrawer from '@/components/workflow/WorkflowNodeConfigDrawer.vue'
import { provideFlowDesignerPopup } from '@/composables/useFlowDesignerPopup'
import {
  defaultNodeConfig,
  type ConditionBranch,
  type WorkflowNodeConfig,
} from '@/composables/useWorkflowAssignee'
import type { FormSchema } from '@/types/form'
import { flattenFormFieldsForPermissions } from '@/utils/formFieldTree'
import {
  collectNodeIds,
  createConditionBlock,
  createStepNode,
  flowChainToGraph,
  graphToFlowChain,
  type FlowChain,
  type FlowConditionBlock,
  type FlowSegment,
  type WfNodeType,
} from '@/utils/workflowFlowGraph'

const { t } = useI18n()

const props = withDefaults(
  defineProps<{
    modelValue?: { nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] }
    formSchema?: FormSchema
    minHeight?: string
  }>(),
  { minHeight: 'min(72vh, 720px)' },
)

const emit = defineEmits<{ 'update:modelValue': [typeof props.modelValue] }>()

const rootRef = ref<HTMLElement | null>(null)
const fullscreen = ref(false)

provideFlowDesignerPopup(
  computed(() => (fullscreen.value && rootRef.value ? rootRef.value : null)),
)
const flowChain = ref<FlowChain>([])
const roleNameMap = ref<Record<string, string>>({})
const panelOpen = ref(false)
const editorPath = ref<number[]>([])
const editorNodeType = ref('')
const editorNodeId = ref('')
const editorConfig = ref<WorkflowNodeConfig>({})
const editorBranches = ref<ConditionBranch[]>([])

const fieldLabelMap = computed(() => {
  const map: Record<string, string> = {}
  for (const f of flattenFormFieldsForPermissions(props.formSchema)) {
    map[`form.${f.key}`] = f.label
  }
  return map
})

const allNodeIds = computed(() => collectNodeIds(flowChain.value))

let syncing = false
let emitTimer: ReturnType<typeof setTimeout> | null = null
let lastExportJson = ''

function scheduleExport() {
  if (emitTimer) clearTimeout(emitTimer)
  emitTimer = setTimeout(() => {
    const graph = flowChainToGraph(flowChain.value)
    const json = JSON.stringify(graph)
    if (json === lastExportJson) {
      emitTimer = null
      return
    }
    lastExportJson = json
    syncing = true
    emit('update:modelValue', graph)
    queueMicrotask(() => {
      syncing = false
    })
    emitTimer = null
  }, 200)
}

function loadFromGraph(g: typeof props.modelValue) {
  syncing = true
  flowChain.value = graphToFlowChain(g)
  lastExportJson = JSON.stringify(g || {})
  syncing = false
}

function toggleFullscreen() {
  fullscreen.value = !fullscreen.value
}

function resolveChainRef(path: number[]): FlowChain {
  if (path.length <= 1) return flowChain.value
  const main = flowChain.value[path[0]]
  if (main?.kind === 'condition') {
    return main.branches[path[1]]?.chain || []
  }
  return flowChain.value
}

function resolveSegment(path: number[]): FlowSegment | null {
  if (!path.length) return null
  if (path.length === 1) return flowChain.value[path[0]] || null
  if (path.length === 3) {
    const main = flowChain.value[path[0]]
    if (main?.kind === 'condition') {
      return main.branches[path[1]]?.chain[path[2]] || null
    }
  }
  return flowChain.value[path[0]] || null
}

function openEditor(path: number[]) {
  const seg = resolveSegment(path)
  if (!seg) return
  editorPath.value = path
  if (seg.kind === 'node') {
    editorNodeType.value = seg.type
    editorNodeId.value = seg.id
    editorConfig.value = JSON.parse(JSON.stringify(seg.config))
    editorBranches.value = []
  } else {
    editorNodeType.value = 'condition'
    editorNodeId.value = seg.id
    editorConfig.value = JSON.parse(JSON.stringify(seg.config))
    editorBranches.value = seg.branches.map((br) => ({
      expr: br.expr,
      target: '',
      label: br.label,
      priority: br.priority,
    }))
  }
  panelOpen.value = true
}

function onInsert(payload: { path: number[]; index: number; type: WfNodeType | 'condition' }) {
  const chain = resolveChainRef(payload.path)
  const insertIdx = payload.index + 1
  if (payload.type === 'condition') {
    const firstField = flattenFormFieldsForPermissions(props.formSchema)[0]?.key || ''
    chain.splice(insertIdx, 0, createConditionBlock(firstField))
  } else {
    chain.splice(insertIdx, 0, createStepNode(payload.type))
  }
  scheduleExport()
}

function onRemove(path: number[]) {
  const idx = path[path.length - 1]
  const chain = resolveChainRef(path.slice(0, -1))
  const seg = chain[idx]
  if (!seg) return
  if (seg.kind === 'node' && (seg.type === 'start' || seg.type === 'end')) return
  chain.splice(idx, 1)
  scheduleExport()
}

function onAddBranch(path: number[]) {
  const seg = resolveSegment(path) as FlowConditionBlock | null
  if (!seg || seg.kind !== 'condition') return
  const pri = seg.branches.filter((b) => b.expr !== 'default').length + 1
  const firstField = flattenFormFieldsForPermissions(props.formSchema)[0]?.key || ''
  const defIdx = seg.branches.findIndex((b) => b.expr === 'default')
  const item = {
    id: `branch_${Date.now()}`,
    label: `条件 ${pri}`,
    priority: pri,
    expr: { field: firstField ? `form.${firstField}` : 'form.', op: 'lt', value: '' } as const,
    chain: [] as FlowSegment[],
  }
  if (defIdx >= 0) seg.branches.splice(defIdx, 0, item)
  else seg.branches.push(item)
  scheduleExport()
}

function onRemoveBranch(payload: { path: number[]; branchIndex: number }) {
  const seg = resolveSegment(payload.path) as FlowConditionBlock | null
  if (!seg || seg.kind !== 'condition') return
  const br = seg.branches[payload.branchIndex]
  if (!br || br.expr === 'default') return
  seg.branches.splice(payload.branchIndex, 1)
  scheduleExport()
}

function applyEditorToSegment(
  seg: FlowSegment,
  config: WorkflowNodeConfig,
  branches?: ConditionBranch[],
) {
  if (seg.kind === 'node') {
    seg.config = config
    return
  }
  seg.config = config
  if (branches) {
    for (let i = 0; i < seg.branches.length; i++) {
      const br = seg.branches[i]
      const src = branches[i]
      if (!src) continue
      br.label = src.label || br.label
      br.priority = src.priority ?? br.priority
      if (src.expr !== undefined) br.expr = src.expr
    }
  }
}

function onDrawerSave(payload: { config: WorkflowNodeConfig; branches?: ConditionBranch[] }) {
  const seg = resolveSegment(editorPath.value)
  if (!seg) return
  applyEditorToSegment(seg, payload.config, payload.branches)
  scheduleExport()
}

function onDrawerDelete() {
  onRemove(editorPath.value)
  panelOpen.value = false
}

async function loadRoleNames() {
  try {
    const { api } = await import('@/api/client')
    const res = await api.get<{ ok: boolean; data: { code: string; name: string }[] }>(
      '/admin/flow-roles',
    )
    if (res.data.ok) {
      const map: Record<string, string> = {}
      for (const r of res.data.data) map[r.code] = r.name
      roleNameMap.value = map
    }
  } catch {
    /* ignore */
  }
}

function exportGraph() {
  scheduleExport()
}

function resize() {
  /* 横向链式布局无需 canvas resize */
}

onMounted(() => {
  loadFromGraph(props.modelValue)
  loadRoleNames()
})

watch(
  () => props.modelValue,
  (g) => {
    if (syncing) return
    const json = JSON.stringify(g || {})
    if (json === lastExportJson) return
    loadFromGraph(g)
  },
  { deep: true },
)

defineExpose({ resize, exportGraph })
</script>

<style scoped>
.wf-vertical-designer {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: v-bind(minHeight);
  gap: 8px;
}

.wf-vertical-designer.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 1100;
  background: #f7f8fa;
  padding: 12px;
  min-height: 100vh !important;
  overflow: hidden;
}

.wf-vertical-designer.is-fullscreen :deep(.arco-drawer-container) {
  position: absolute !important;
  inset: 0 !important;
  z-index: 200 !important;
}

.wf-vertical-designer.is-fullscreen :deep(.arco-trigger-popup) {
  z-index: 300 !important;
}

.designer-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.toolbar-label {
  font-size: 12px;
  color: #86909c;
}

.designer-scroll {
  flex: 1;
  min-height: 480px;
  overflow: auto;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  background: #f2f3f5;
}

.designer-scroll::-webkit-scrollbar {
  height: 8px;
}

.flow-canvas-outer {
  box-sizing: border-box;
  min-height: 100%;
  width: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  padding: 16px 20px;
}

.flow-canvas {
  width: 100%;
  max-width: 100%;
}
</style>
