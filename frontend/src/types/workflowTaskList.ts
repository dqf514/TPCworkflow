import type { WorkflowInstanceListRow } from '@/types/workflowInstanceList'

export interface WorkflowTaskListRow extends WorkflowInstanceListRow {
  task_id: number
  node_id: string
  node_name?: string
  node_type?: string
  task_status: string
  task_created_at?: string
  task_completed_at?: string
  is_handler?: boolean
  can_quick_approve?: boolean
  can_reject?: boolean
  field_requirement_errors?: string[]
}

export type TaskListSortField =
  | 'display_no'
  | 'definition_name'
  | 'business_sector_name'
  | 'total_amount'
  | 'initiator_name'
  | 'department_name'
  | 'started_at'
  | 'task_created_at'
  | 'completed_at'
  | 'task_status'
  | 'node_name'

export interface TaskListPageResult {
  items: WorkflowTaskListRow[]
  total: number
  page: number
  page_size: number
}

export interface TaskBatchCompleteResult {
  succeeded: number[]
  failed: { task_id: number | string; reason: string }[]
}
