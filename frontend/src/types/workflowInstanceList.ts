export interface WorkflowInstanceListRow {
  id: number
  public_uuid: string
  display_no?: string
  definition_id?: number
  definition_name?: string
  business_sector_name?: string
  status: string
  /** 运行中时，当前审批节点在设计器中的自定义名称 */
  current_node_label?: string | null
  initiator_name?: string
  department_name?: string
  started_at?: string
  updated_at?: string
  finished_at?: string
  total_amount?: number | null
  amount_currency?: string | null
  can_withdraw?: boolean
  has_unread_update?: boolean
  is_latest_update?: boolean
  my_task_status?: string
  my_completed_at?: string
}

export type InstanceListSortField =
  | 'display_no'
  | 'definition_name'
  | 'business_sector_name'
  | 'total_amount'
  | 'status'
  | 'initiator_name'
  | 'department_name'
  | 'started_at'
  | 'updated_at'
  | 'finished_at'
  | 'task_created_at'
  | 'completed_at'
  | 'task_status'
  | 'node_name'

export type InstanceListSortDirection = 'ascend' | 'descend' | ''

export interface InstanceListColumnConfig {
  displayNo?: boolean
  flow?: boolean
  sector?: boolean
  amount?: boolean
  status?: boolean
  applicant?: boolean
  department?: boolean
  submittedAt?: boolean
  updatedAt?: boolean
  finishedAt?: boolean
  actions?: boolean
}
