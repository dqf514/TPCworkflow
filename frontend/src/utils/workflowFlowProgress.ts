import { collectNodeIds, type FlowChain } from '@/utils/workflowFlowGraph'

export type FlowNodePreviewState = 'done' | 'current' | 'pending'

export function buildFlowNodeStates(
  chain: FlowChain,
  opts: {
    mode: 'apply' | 'runtime'
    status?: string
    currentNodeIds?: string[]
    completedNodeIds?: string[]
  },
): Record<string, FlowNodePreviewState> {
  const ids = collectNodeIds(chain)
  const states: Record<string, FlowNodePreviewState> = {}
  const current = new Set(opts.currentNodeIds || [])
  const done = new Set(opts.completedNodeIds || [])
  done.add('start')

  if (opts.mode === 'apply') {
    for (const id of ids) {
      states[id] = id === 'start' ? 'done' : 'pending'
    }
    return states
  }

  const terminalStatuses = new Set(['approved', 'rejected', 'cancelled', 'completed', 'withdrawn'])
  const terminal = terminalStatuses.has(opts.status || '')

  if (terminal) {
    for (const id of ids) {
      states[id] = 'done'
    }
    return states
  }

  for (const id of ids) {
    if (current.has(id)) {
      states[id] = 'current'
    } else if (done.has(id)) {
      states[id] = 'done'
    } else {
      states[id] = 'pending'
    }
  }
  return states
}
