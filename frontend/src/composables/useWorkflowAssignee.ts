import { useI18n } from 'vue-i18n'

export type AssigneeType =
  | 'fixed_users'
  | 'initiator'
  | 'flow_role'
  | 'initiator_dept_manager'
  | 'parent_dept_manager'
  | 'dept_chain'
  | 'dept_manager'

export type FieldPermMode = 'hidden' | 'read' | 'edit'

/** 节点额外发送邮件（与待办通知并行，内容相同） */
export type NodeSendEmailTrigger = 'on_enter' | 'on_complete'

export interface NodeSendEmailConfig {
  enabled?: boolean
  /** 到达节点时 | 节点全部完成后 */
  trigger?: NodeSendEmailTrigger
  /** 组织成员 | 表单邮箱字段 */
  recipient_type?: 'org_user' | 'form_field'
  user_ids?: number[]
  field_key?: string
  subject?: string
  body?: string
}

/** 进入办理人节点时通知申请人准备材料 */
export interface NodeNotifyApplicantConfig {
  enabled?: boolean
  subject?: string
  body?: string
}

export interface WorkflowNodeConfig {
  title?: string
  apv_rel?: 'or' | 'and' | 'sequential'
  assignee_type?: AssigneeType
  flow_role_code?: string
  user_ids?: number[]
  department_id?: number
  field_permissions?: Record<string, FieldPermMode>
  /** 本节点可编辑字段须填写 */
  field_node_required?: Record<string, boolean>
  /** 本节点可编辑字段须相对进入节点时修改 */
  field_must_modify?: Record<string, boolean>
  send_email?: NodeSendEmailConfig
  notify_applicant_on_enter?: NodeNotifyApplicantConfig
}

export interface ConditionBranch {
  expr: { field: string; op: string; value: unknown } | 'default' | string
  target: string
  label?: string
  priority?: number
}

export const CONDITION_OPS = [
  { value: 'eq', labelKey: 'flowDesign.op_eq' },
  { value: 'ne', labelKey: 'flowDesign.op_ne' },
  { value: 'gt', labelKey: 'flowDesign.op_gt' },
  { value: 'gte', labelKey: 'flowDesign.op_gte' },
  { value: 'lt', labelKey: 'flowDesign.op_lt' },
  { value: 'lte', labelKey: 'flowDesign.op_lte' },
] as const

export const NODE_TYPE_META: Record<
  string,
  { fill: string; stroke: string; header: string; labelKey: string }
> = {
  start: { fill: '#e8f3ff', stroke: '#165dff', header: '#165dff', labelKey: 'flowDesign.node_start' },
  approver: { fill: '#fff7e8', stroke: '#ff7d00', header: '#ff7d00', labelKey: 'flowDesign.node_approver' },
  handler: { fill: '#e8fffb', stroke: '#0fc6c2', header: '#0fc6c2', labelKey: 'flowDesign.node_handler' },
  cc: { fill: '#e8ffea', stroke: '#00b42a', header: '#00b42a', labelKey: 'flowDesign.node_cc' },
  condition: { fill: '#f2f3f5', stroke: '#86909c', header: '#86909c', labelKey: 'flowDesign.node_condition' },
  end: { fill: '#f7f8fa', stroke: '#c9cdd4', header: '#4e5969', labelKey: 'flowDesign.node_end' },
}

export function defaultNodeConfig(type: string): WorkflowNodeConfig & { branches?: ConditionBranch[] } {
  if (type === 'approver' || type === 'handler') {
    return {
      title: '',
      apv_rel: 'or',
      assignee_type: 'initiator_dept_manager',
      field_permissions: {},
      field_node_required: {},
      field_must_modify: {},
    }
  }
  if (type === 'cc') {
    return { title: '', assignee_type: 'flow_role', flow_role_code: 'dept_leader' }
  }
  if (type === 'condition') {
    return { title: '' }
  }
  if (type === 'start') {
    return { title: '申请人' }
  }
  return { title: '' }
}

export function useWorkflowAssignee() {
  const { t } = useI18n()

  function assigneeTypeLabel(type: string) {
    const map: Record<string, string> = {
      fixed_users: t('flowDesign.assignee_fixed'),
      initiator: t('flowDesign.assignee_initiator'),
      flow_role: t('flowDesign.assignee_flow_role'),
      initiator_dept_manager: t('flowDesign.assignee_dept_mgr'),
      parent_dept_manager: t('flowDesign.assignee_parent_mgr'),
      dept_chain: t('flowDesign.assignee_dept_chain'),
      dept_manager: t('flowDesign.assignee_dept_pick'),
    }
    return map[type] || type
  }

  function approveModeLabel(mode: string) {
    if (mode === 'and') return t('flowDesign.mode_and')
    if (mode === 'sequential') return t('flowDesign.mode_seq')
    return t('flowDesign.mode_or')
  }

  function summarizeConfig(type: string, config: WorkflowNodeConfig, roleNameMap?: Record<string, string>) {
    if (type === 'start') return t('flowDesign.start_summary')
    if (type === 'end') return t('flowDesign.end_summary')
    if (type === 'condition') return t('flowDesign.condition_summary')
    const cfg = config || {}
    const parts: string[] = []
    if (cfg.assignee_type) parts.push(assigneeTypeLabel(cfg.assignee_type))
    if (cfg.assignee_type === 'flow_role' && cfg.flow_role_code) {
      parts.push(roleNameMap?.[cfg.flow_role_code] || cfg.flow_role_code)
    }
    if (cfg.assignee_type === 'fixed_users' && cfg.user_ids?.length) {
      parts.push(t('flowDesign.n_users', { n: cfg.user_ids.length }))
    }
    if (cfg.assignee_type === 'dept_manager' && cfg.department_id) {
      parts.push(`#${cfg.department_id}`)
    }
    if ((type === 'approver' || type === 'handler') && cfg.apv_rel) {
      parts.push(approveModeLabel(cfg.apv_rel))
    }
    if (cfg.send_email?.enabled) {
      const trig = cfg.send_email.trigger || 'on_enter'
      if (trig === 'on_complete') {
        parts.push(t('flowDesign.send_email_on_complete_badge'))
      } else {
        parts.push(t('flowDesign.send_email_on_enter_badge'))
      }
      if (cfg.send_email.recipient_type === 'form_field' && cfg.send_email.field_key) {
        parts.push(t('flowDesign.send_email_field_summary'))
      } else if (cfg.send_email.user_ids?.length) {
        parts.push(t('flowDesign.send_email_users_summary', { n: cfg.send_email.user_ids.length }))
      }
    }
    if (type === 'handler' && cfg.notify_applicant_on_enter?.enabled) {
      parts.push(t('flowDesign.notify_applicant_enabled'))
    }
    return parts.filter(Boolean).join(' · ') || t('flowDesign.config_pending')
  }

  function nodeDisplayTitle(type: string, config: WorkflowNodeConfig) {
    if (config?.title?.trim()) return config.title.trim()
    return t(NODE_TYPE_META[type]?.labelKey || 'flowDesign.node_props')
  }

  function buildNodeText(type: string, config: WorkflowNodeConfig, roleNameMap?: Record<string, string>) {
    const title = nodeDisplayTitle(type, config)
    const sub = summarizeConfig(type, config, roleNameMap)
    return sub && type !== 'end' ? `${title}\n${sub}` : title
  }

  return {
    assigneeTypeLabel,
    approveModeLabel,
    summarizeConfig,
    nodeDisplayTitle,
    buildNodeText,
  }
}
