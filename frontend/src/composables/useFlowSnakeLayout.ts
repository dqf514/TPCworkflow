import { computed, type Ref } from 'vue'
import type { FlowChain } from '@/utils/workflowFlowGraph'

/** 每行最多节点数（固定，不随宽度变化） */
export const FLOW_NODES_PER_ROW = 5

export interface FlowLayoutUnit {
  key: string
  kind: 'segment' | 'condition-block'
  index: number
}

export interface FlowLayoutRow {
  key: string
  units: FlowLayoutUnit[]
}

export function useFlowSnakeLayout(chain: Ref<FlowChain>) {
  const layoutRows = computed((): FlowLayoutRow[] => {
    const chainVal = chain.value
    const rows: FlowLayoutRow[] = []
    let buffer: FlowLayoutUnit[] = []
    let count = 0
    let rowSeq = 0

    function flush() {
      if (!buffer.length) return
      rows.push({
        key: `row-${rowSeq++}`,
        units: [...buffer],
      })
      buffer = []
      count = 0
    }

    chainVal.forEach((seg, idx) => {
      if (seg.kind === 'condition') {
        flush()
        rows.push({
          key: `cond-${seg.id}`,
          units: [{ key: `cb-${idx}`, kind: 'condition-block', index: idx }],
        })
        rowSeq++
        return
      }

      if (count >= FLOW_NODES_PER_ROW) {
        flush()
      }

      buffer.push({ key: `seg-${idx}`, kind: 'segment', index: idx })
      count++
    })

    flush()
    return rows
  })

  return { layoutRows }
}
