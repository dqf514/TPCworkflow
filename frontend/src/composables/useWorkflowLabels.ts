import type { ComposerTranslation } from 'vue-i18n'

const STATUS_KEYS: Record<string, string> = {
  running: 'workflow.status_running',
  approved: 'workflow.status_approved',
  rejected: 'workflow.status_rejected',
  cancelled: 'workflow.status_cancelled',
  draft: 'workflow.status_draft',
  pending: 'workflow.status_pending',
}

const TASK_STATUS_KEYS: Record<string, string> = {
  approved: 'workflow.my_task_approved',
  rejected: 'workflow.my_task_rejected',
  reject: 'workflow.my_task_rejected',
  transfer: 'workflow.my_task_transfer',
  completed: 'workflow.my_task_completed',
  pending: 'workflow.status_pending',
  cancelled: 'workflow.my_task_superseded',
}

/** 流程实例状态显示文案（随当前语言） */
export function formatInstanceStatus(
  status: string | undefined,
  t: ComposerTranslation,
  currentNodeLabel?: string | null,
): string {
  if (status === 'running' && currentNodeLabel) {
    return currentNodeLabel
  }
  if (!status) return ''
  const key = STATUS_KEYS[status]
  if (!key) return status
  const label = t(key)
  return label === key ? status : label
}

/** 列表行状态：运行中优先展示当前节点名称 */
export function formatInstanceListStatus(
  record: { status?: string; current_node_label?: string | null },
  t: ComposerTranslation,
): string {
  return formatInstanceStatus(record.status, t, record.current_node_label)
}

/** 我在该单上的处理结果 */
export function formatMyTaskStatus(status: string | undefined, t: ComposerTranslation): string {
  if (!status) return '—'
  const key = TASK_STATUS_KEYS[status]
  if (!key) return status
  const label = t(key)
  return label === key ? status : label
}
