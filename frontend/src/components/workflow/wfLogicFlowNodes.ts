import { RectNode, RectNodeModel, type GraphModel } from '@logicflow/core'
import { NODE_TYPE_META } from '@/composables/useWorkflowAssignee'

export const WF_NODE_TYPE = 'wf-node'

class WfNodeModel extends RectNodeModel {
  initNodeData(data: Record<string, unknown>) {
    super.initNodeData(data)
    this.width = 196
    this.height = 76
    this.radius = 8
  }

  getNodeStyle() {
    const style = super.getNodeStyle()
    const wfType = (this.properties?.type as string) || 'approver'
    const meta = NODE_TYPE_META[wfType] || NODE_TYPE_META.approver
    style.fill = meta.fill
    style.stroke = meta.stroke
    style.strokeWidth = 2
    return style
  }

  getTextStyle() {
    const style = super.getTextStyle()
    style.fontSize = 12
    style.color = '#1d2129'
    return style
  }
}

class WfNodeView extends RectNode {}

export function registerWfNodes(lf: { register: (arg: { type: string; view: typeof WfNodeView; model: typeof WfNodeModel }) => void }) {
  lf.register({ type: WF_NODE_TYPE, view: WfNodeView, model: WfNodeModel })
}

export function patchNodeText(
  lf: { getNodeModelById: (id: string) => GraphModel['nodes'][0] | undefined },
  nodeId: string,
  text: string,
) {
  try {
    const model = lf.getNodeModelById(nodeId)
    if (model && 'updateText' in model) {
      ;(model as { updateText: (t: string) => void }).updateText(text)
    }
  } catch {
    /* ignore */
  }
}
