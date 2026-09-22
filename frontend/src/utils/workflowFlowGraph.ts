/**
 * 垂直流程树 ↔ process_graph 双向转换，保证画布路径与引擎一致。
 */
import {
  defaultNodeConfig,
  type ConditionBranch,
  type WorkflowNodeConfig,
} from '@/composables/useWorkflowAssignee'
import {
  conditionValuesEqual,
  fieldKeyFromConditionPath,
  formatConditionValueLabel,
  normalizeConditionScalar,
} from '@/utils/conditionFieldMeta'

export type WfNodeType = 'start' | 'approver' | 'handler' | 'cc' | 'condition' | 'end'

export interface ProcessGraph {
  nodes: Record<string, unknown>[]
  edges: Record<string, unknown>[]
}

export interface FlowStepNode {
  kind: 'node'
  id: string
  type: WfNodeType
  config: WorkflowNodeConfig
}

export interface FlowConditionBlock {
  kind: 'condition'
  id: string
  config: WorkflowNodeConfig
  branches: FlowConditionBranch[]
}

export interface FlowConditionBranch {
  id: string
  label: string
  priority: number
  expr: ConditionBranch['expr']
  chain: FlowSegment[]
}

export type FlowSegment = FlowStepNode | FlowConditionBlock

export type FlowChain = FlowSegment[]

let seq = 1

export function resetFlowIdSeq(n = 1) {
  seq = n
}

export function nextFlowId(prefix: string) {
  return `${prefix}_${seq++}`
}

export function defaultFlowChain(): FlowChain {
  return [
    { kind: 'node', id: 'start', type: 'start', config: defaultNodeConfig('start') },
    {
      kind: 'node',
      id: 'approve1',
      type: 'approver',
      config: defaultNodeConfig('approver'),
    },
    { kind: 'node', id: 'end', type: 'end', config: defaultNodeConfig('end') },
  ]
}

export function createStepNode(type: WfNodeType): FlowSegment {
  const id = nextFlowId(type)
  return { kind: 'node', id, type, config: defaultNodeConfig(type) }
}

export function createConditionBlock(fieldKey = ''): FlowConditionBlock {
  const id = nextFlowId('condition')
  const field = fieldKey ? `form.${fieldKey}` : 'form.'
  return {
    kind: 'condition',
    id,
    config: { title: '条件分支' },
    branches: [
      {
        id: nextFlowId('branch'),
        label: '条件 1',
        priority: 1,
        expr: { field, op: 'eq', value: '' },
        chain: [],
      },
      {
        id: nextFlowId('branch'),
        label: '默认条件',
        priority: 99,
        expr: 'default',
        chain: [],
      },
    ],
  }
}

function isConditionBlock(seg: FlowSegment): seg is FlowConditionBlock {
  return seg.kind === 'condition'
}

function isStepNode(seg: FlowSegment): seg is FlowStepNode {
  return seg.kind === 'node'
}

/** 收集链上所有节点 id（含嵌套条件内） */
export function collectNodeIds(chain: FlowChain): string[] {
  const ids: string[] = []
  function walk(segments: FlowSegment[]) {
    for (const seg of segments) {
      if (isStepNode(seg)) ids.push(seg.id)
      else {
        ids.push(seg.id)
        for (const br of seg.branches) walk(br.chain)
      }
    }
  }
  walk(chain)
  return ids
}

function buildAdjacency(graph: ProcessGraph) {
  const out = new Map<string, string[]>()
  const inc = new Map<string, string[]>()
  for (const e of graph.edges || []) {
    const s = String(e.source || '')
    const t = String(e.target || '')
    if (!s || !t) continue
    if (!out.has(s)) out.set(s, [])
    out.get(s)!.push(t)
    if (!inc.has(t)) inc.set(t, [])
    inc.get(t)!.push(s)
  }
  return { out, inc }
}

function nodeById(graph: ProcessGraph, id: string) {
  return (graph.nodes || []).find((n) => String(n.id) === id)
}

function pickSingleNext(out: Map<string, string[]>, id: string): string | null {
  const list = out.get(id) || []
  return list.length === 1 ? list[0] : list[0] || null
}

function isEndNodeId(graph: ProcessGraph, id: string): boolean {
  const n = nodeById(graph, id)
  return !!n && String(n.type) === 'end'
}

/** 从 branch 起点沿单链走到 merge 前（不含 merge/end 节点） */
function walkBranchChain(
  graph: ProcessGraph,
  startId: string,
  mergeId: string,
  out: Map<string, string[]>,
): string[] {
  const chain: string[] = []
  let cur: string | null = startId
  const guard = new Set<string>()
  while (cur && cur !== mergeId && !guard.has(cur)) {
    guard.add(cur)
    const n = nodeById(graph, cur)
    if (!n) break
    if (String(n.type) === 'end') break
    if (String(n.type) === 'condition') break
    chain.push(cur)
    const nx = pickSingleNext(out, cur)
    if (!nx || nx === mergeId || isEndNodeId(graph, nx)) break
    cur = nx
  }
  return chain
}

function findMergeAfterCondition(
  graph: ProcessGraph,
  condId: string,
  branchTargets: string[],
  out: Map<string, string[]>,
): string | null {
  const tails: string[] = []
  for (const tid of branchTargets) {
    if (!tid) continue
    const walked = walkBranchChain(graph, tid, '', out)
    const last = walked[walked.length - 1] || tid
    const nxt = pickSingleNext(out, last)
    if (nxt) tails.push(nxt)
  }
  if (!tails.length) return null
  const first = tails[0]
  return tails.every((t) => t === first) ? first : first
}

/** 分支链内不应包含结束节点（结束为汇合点，属于主链） */
function sanitizeBranchChain(chain: FlowChain): FlowChain {
  return chain.filter((seg) => !(isStepNode(seg) && seg.type === 'end'))
}

function sanitizeFlowChain(chain: FlowChain): FlowChain {
  return chain.map((seg) => {
    if (!isConditionBlock(seg)) return seg
    return {
      ...seg,
      branches: seg.branches.map((br) => ({
        ...br,
        chain: sanitizeBranchChain(sanitizeFlowChain(br.chain)),
      })),
    }
  })
}

function nodeToStep(n: Record<string, unknown>): FlowStepNode {
  return {
    kind: 'node',
    id: String(n.id),
    type: (n.type as WfNodeType) || 'approver',
    config: (n.config as WorkflowNodeConfig) || defaultNodeConfig(String(n.type)),
  }
}

function segmentFromNodeId(graph: ProcessGraph, id: string, visited: Set<string>): FlowSegment | null {
  const n = nodeById(graph, id)
  if (!n || visited.has(id)) return null
  visited.add(id)
  const type = String(n.type) as WfNodeType
  if (type === 'condition') {
    const branchesRaw = (n.branches as ConditionBranch[]) || []
    const { out } = buildAdjacency(graph)
    const targets = branchesRaw.map((b) => String(b.target || ''))
    const mergeId = findMergeAfterCondition(graph, id, targets, out)
    const branches: FlowConditionBranch[] = branchesRaw.map((br, i) => {
      const tid = String(br.target || '')
      const walked = tid ? walkBranchChain(graph, tid, mergeId || '', out) : []
      const subChain: FlowChain = []
      for (const nid of walked) {
        const sub = segmentFromNodeId(graph, nid, visited)
        if (sub) subChain.push(sub)
      }
      return {
        id: `branch_${id}_${i}`,
        label: br.label || (br.expr === 'default' ? '默认条件' : `条件 ${i + 1}`),
        priority: br.priority ?? i + 1,
        expr: br.expr,
        chain: subChain,
      }
    })
    return {
      kind: 'condition',
      id,
      config: (n.config as WorkflowNodeConfig) || defaultNodeConfig('condition'),
      branches,
    }
  }
  return nodeToStep(n)
}

/** process_graph → 垂直流程树 */
export function graphToFlowChain(graph: ProcessGraph | undefined): FlowChain {
  if (!graph?.nodes?.length) {
    resetFlowIdSeq(2)
    return defaultFlowChain()
  }
  const { out } = buildAdjacency(graph)
  const start = graph.nodes.find((n) => n.type === 'start')
  if (!start) {
    resetFlowIdSeq(2)
    return defaultFlowChain()
  }
  const visited = new Set<string>()
  const chain: FlowChain = []
  let cur: string | null = String(start.id)
  while (cur && !visited.has(`main_${cur}`)) {
    visited.add(`main_${cur}`)
    const n = nodeById(graph, cur)
    if (!n) break
    if (String(n.type) === 'condition') {
      const seg = segmentFromNodeId(graph, cur, new Set()) as FlowConditionBlock
      chain.push(seg)
      const branchesRaw = (n.branches as ConditionBranch[]) || []
      const targets = branchesRaw.map((b) => String(b.target || ''))
      const mergeId = findMergeAfterCondition(graph, cur, targets, out)
      cur = mergeId
      continue
    }
    chain.push(nodeToStep(n))
    if (String(n.type) === 'end') break
    cur = pickSingleNext(out, cur)
  }
  if (!chain.some((s) => isStepNode(s) && s.type === 'start')) {
    chain.unshift({
      kind: 'node',
      id: 'start',
      type: 'start',
      config: defaultNodeConfig('start'),
    })
  }
  if (!chain.some((s) => isStepNode(s) && s.type === 'end')) {
    chain.push({ kind: 'node', id: 'end', type: 'end', config: defaultNodeConfig('end') })
  }
  const maxNum = Math.max(
    1,
    ...collectNodeIds(chain).map((id) => {
      const m = /_(\d+)$/.exec(id)
      return m ? Number(m[1]) : 0
    }),
  )
  resetFlowIdSeq(maxNum + 1)
  return sanitizeFlowChain(chain)
}

interface ExportCtx {
  nodes: Record<string, unknown>[]
  edges: Record<string, unknown>[]
  y: number
}

function addEdge(ctx: ExportCtx, source: string, target: string) {
  if (!source || !target) return
  const exists = ctx.edges.some(
    (e) => String(e.source) === source && String(e.target) === target,
  )
  if (!exists) ctx.edges.push({ source, target })
}

function exportSegmentChain(ctx: ExportCtx, segments: FlowSegment[]): string | null {
  let prev: string | null = null
  for (const seg of segments) {
    if (isStepNode(seg)) {
      ctx.nodes.push({
        id: seg.id,
        type: seg.type,
        x: 400,
        y: ctx.y,
        config: seg.config,
      })
      ctx.y += 120
      if (prev) addEdge(ctx, prev, seg.id)
      prev = seg.id
      continue
    }
    ctx.nodes.push({
      id: seg.id,
      type: 'condition',
      x: 400,
      y: ctx.y,
      config: seg.config,
      branches: [],
    })
    ctx.y += 80
    if (prev) addEdge(ctx, prev, seg.id)
    const branchTargets: string[] = []
    const branchesOut: ConditionBranch[] = []
    const sorted = [...seg.branches].sort((a, b) => a.priority - b.priority)
    for (const br of sorted) {
      const firstId = exportSegmentChain(ctx, br.chain)
      branchTargets.push(firstId || '')
      branchesOut.push({
        expr: br.expr,
        target: firstId || '',
        label: br.label,
        priority: br.priority,
      })
    }
    const condNode = ctx.nodes.find((n) => n.id === seg.id)
    if (condNode) condNode.branches = branchesOut
    prev = seg.id
    ;(seg as FlowConditionBlock & { _branchTails?: string[] })._branchTails = branchTargets.map(
      (tid) => {
        if (!tid) return ''
        let tail = tid
        let guard = 0
        while (guard++ < 50) {
          const outs = ctx.edges.filter((e) => e.source === tail)
          if (outs.length !== 1) break
          tail = String(outs[0].target)
        }
        return tail
      },
    )
  }
  return prev
}

/** 垂直流程树 → process_graph，并同步 condition.branches[].target */
export function flowChainToGraph(chain: FlowChain): ProcessGraph {
  const ctx: ExportCtx = { nodes: [], edges: [], y: 80 }
  const mainIds: string[] = []
  let prevMain: string | null = null

  for (let i = 0; i < chain.length; i++) {
    const seg = chain[i]
    const nextSeg = chain[i + 1]
    const mergeTargetId =
      nextSeg && isStepNode(nextSeg)
        ? nextSeg.id
        : nextSeg && isConditionBlock(nextSeg)
          ? nextSeg.id
          : null

    if (isStepNode(seg)) {
      ctx.nodes.push({ id: seg.id, type: seg.type, x: 400, y: ctx.y, config: seg.config })
      ctx.y += 120
      mainIds.push(seg.id)
      if (prevMain) addEdge(ctx, prevMain, seg.id)
      prevMain = seg.id
      continue
    }

    ctx.nodes.push({
      id: seg.id,
      type: 'condition',
      x: 400,
      y: ctx.y,
      config: seg.config,
      branches: [],
    })
    ctx.y += 80
    if (prevMain) addEdge(ctx, prevMain, seg.id)
    mainIds.push(seg.id)

    const branchesOut: ConditionBranch[] = []
    const sorted = [...seg.branches].sort((a, b) => a.priority - b.priority)
    for (const br of sorted) {
      let subPrev: string | null = null
      let firstId = ''
      for (const sub of br.chain) {
        if (isStepNode(sub)) {
          if (sub.type === 'end') {
            continue
          }
          if (!ctx.nodes.find((n) => n.id === sub.id)) {
            ctx.nodes.push({
              id: sub.id,
              type: sub.type,
              x: 400,
              y: ctx.y,
              config: sub.config,
            })
            ctx.y += 120
          }
          if (!firstId) firstId = sub.id
          if (subPrev) addEdge(ctx, subPrev, sub.id)
          subPrev = sub.id
        } else {
          const nested = flowChainToGraph([sub])
          for (const n of nested.nodes) {
            if (!ctx.nodes.find((x) => x.id === n.id)) ctx.nodes.push(n)
          }
          for (const e of nested.edges) addEdge(ctx, String(e.source), String(e.target))
          const nestedStart = nested.nodes.find((n) => n.type === 'start')?.id
          const nestedEnd = [...nested.nodes].reverse().find((n) => n.type !== 'start')?.id
          if (nestedStart && !firstId) firstId = String(nestedStart)
          if (subPrev && nestedStart) addEdge(ctx, subPrev, String(nestedStart))
          if (nestedEnd) subPrev = String(nestedEnd)
        }
      }
      branchesOut.push({
        expr: br.expr,
        target: firstId,
        label: br.label,
        priority: br.priority,
      })
      const tail = subPrev || firstId
      if (tail && mergeTargetId) addEdge(ctx, tail, mergeTargetId)
    }
    const condNode = ctx.nodes.find((n) => n.id === seg.id)
    if (condNode) condNode.branches = branchesOut
    prevMain = seg.id
    if (mergeTargetId && !sorted.length) addEdge(ctx, seg.id, mergeTargetId)
  }

  return { nodes: ctx.nodes, edges: ctx.edges }
}

export function formatConditionExpr(
  expr: ConditionBranch['expr'],
  fieldLabelMap?: Record<string, string>,
): string {
  if (expr === 'default' || expr === null || expr === undefined) return '其他情况走此分支'
  if (typeof expr === 'string') return expr === 'default' ? '默认条件' : expr
  if (typeof expr !== 'object') return String(expr)
  const field = String(expr.field || '')
  const label = fieldLabelMap?.[field] || field.replace(/^form\./, '')
  const opMap: Record<string, string> = {
    eq: '等于',
    ne: '不等于',
    gt: '大于',
    gte: '大于等于',
    lt: '小于',
    lte: '小于等于',
  }
  const op = opMap[String(expr.op || 'eq')] || String(expr.op)
  const fieldKey = fieldKeyFromConditionPath(field)
  const valueLabel = formatConditionValueLabel(
    fieldLabelMap?.[`__type__:${fieldKey}`],
    expr.value,
  )
  return `${label} ${op} ${valueLabel}`
}

function isDefaultBranchExpr(expr: ConditionBranch['expr']): boolean {
  if (expr === 'default' || expr === null || expr === undefined || expr === true) return true
  if (typeof expr === 'string' && expr.trim() === 'default') return true
  if (typeof expr === 'object' && (expr as { default?: boolean }).default) return true
  return false
}

function normalizeCompareValue(val: unknown): unknown {
  return normalizeConditionScalar(val)
}

function getVariableValue(variables: Record<string, unknown>, field: string): unknown {
  if (field in variables) return variables[field]
  if (field.startsWith('form.')) {
    const form = (variables.form as Record<string, unknown>) || {}
    return form[field.slice(5)]
  }
  if (field.startsWith('org.')) {
    const org = (variables.org as Record<string, unknown>) || {}
    return org[field.slice(4)]
  }
  const parts = field.split('.')
  let cur: unknown = variables
  for (const p of parts) {
    if (!cur || typeof cur !== 'object') return undefined
    cur = (cur as Record<string, unknown>)[p]
  }
  return cur
}

/** 与后端 graph_utils.eval_condition 对齐 */
export function evalCondition(
  expr: ConditionBranch['expr'],
  variables: Record<string, unknown>,
): boolean {
  if (expr === null || expr === undefined || expr === '' || expr === true) return true
  if (expr === 'default') return true
  if (typeof expr === 'boolean') return expr
  if (typeof expr === 'string') {
    const s = expr.trim()
    if (s === 'default') return true
    if (s === 'true') return true
    if (s === 'false') return false
    return Boolean(s)
  }
  if (typeof expr === 'object') {
    if ((expr as { default?: boolean }).default) return true
    const field = String((expr as { field?: string; key?: string }).field || (expr as { key?: string }).key || '')
    const op = String((expr as { op?: string }).op || 'eq')
    const expected = (expr as { value?: unknown }).value
    if (!field) return false
    const actual = normalizeCompareValue(getVariableValue(variables, field))
    const expectedNorm = normalizeCompareValue(expected)
    if (['gt', 'gte', 'lt', 'lte'].includes(op)) {
      const a = Number(actual)
      const b = Number(expectedNorm)
      if (Number.isNaN(a) || Number.isNaN(b)) return false
      if (op === 'gt') return a > b
      if (op === 'gte') return a >= b
      if (op === 'lt') return a < b
      if (op === 'lte') return a <= b
    }
    if (op === 'ne') return !conditionValuesEqual(actual, expectedNorm)
    if (op === 'eq') return conditionValuesEqual(actual, expectedNorm)
    return conditionValuesEqual(actual, expectedNorm)
  }
  return Boolean(expr)
}

export function pickMatchingBranch(
  branches: FlowConditionBranch[],
  variables: Record<string, unknown>,
): FlowConditionBranch | null {
  if (!branches.length) return null
  const sorted = [...branches].sort((a, b) => a.priority - b.priority)
  const nonDefault = sorted.filter((b) => !isDefaultBranchExpr(b.expr))
  const defaultBranch = sorted.find((b) => isDefaultBranchExpr(b.expr)) || sorted[sorted.length - 1]
  for (const br of nonDefault) {
    if (evalCondition(br.expr, variables)) return br
  }
  return defaultBranch || null
}

/** 发起/填表预览：仅保留当前表单值命中的条件分支路径 */
export function resolvePreviewFlowChain(
  chain: FlowChain,
  variables: Record<string, unknown>,
): FlowChain {
  const out: FlowChain = []

  for (const seg of chain) {
    if (isStepNode(seg)) {
      out.push(seg)
      continue
    }

    const matched = pickMatchingBranch(seg.branches, variables)
    const previewBranch: FlowConditionBranch = matched
      ? {
          ...matched,
          chain: resolvePreviewFlowChain(matched.chain, variables),
        }
      : {
          id: 'preview_empty',
          label: '未匹配',
          priority: 99,
          expr: 'default',
          chain: [],
        }

    out.push({
      ...seg,
      branches: [previewBranch],
    })
  }

  return sanitizeFlowChain(out)
}

export interface FlowTextStep {
  id: string
  type: string
  label: string
}

const FALLBACK_STEP_LABELS: Record<string, string> = {
  start: '申请人',
  end: '结束',
  approver: '审批',
  handler: '办理',
  cc: '抄送',
  condition: '条件分支',
}

/** 将流程链压平为文字步骤（条件分支展开为命中路径上的节点） */
export function flattenFlowChainToTextSteps(chain: FlowChain): FlowTextStep[] {
  const steps: FlowTextStep[] = []

  function walk(segments: FlowChain) {
    for (const seg of segments) {
      if (isStepNode(seg)) {
        const title = seg.config?.title?.trim()
        steps.push({
          id: seg.id,
          type: seg.type,
          label: title || FALLBACK_STEP_LABELS[seg.type] || seg.type,
        })
        continue
      }
      for (const br of seg.branches) {
        if (br.chain?.length) walk(br.chain)
      }
    }
  }

  walk(chain)
  return steps
}
