export type EmptyAction = 'auto_approve' | 'transfer' | 'admin_handover'
export type ResignedAction = 'auto_transfer' | 'admin_handover'
export type DuplicateApproverMode = 'first_only' | 'consecutive_only' | 'every_node'
export type ApplyVisibilityMode = 'all' | 'restricted'

export interface DocumentDeliverySettings {
  enabled: boolean
  template_code: string
  recipient_email_field: string
  recipient_name_field: string
  email_language_field: string
  cc_email_field: string
}

export interface WorkflowSettings {
  require_comment: boolean
  require_comment_on_reject: boolean
  require_handwritten_sign: boolean
  require_handler_comment: boolean
  allow_transfer: boolean
  allow_revoke_after_approved: boolean
  allow_add_sign: boolean
  approver_empty_action: EmptyAction
  approver_empty_transfer_user_id?: number | null
  approver_resigned_action: ResignedAction
  approver_resigned_transfer_user_id?: number | null
  handler_empty_action: EmptyAction
  handler_empty_transfer_user_id?: number | null
  handler_resigned_action: ResignedAction
  handler_resigned_transfer_user_id?: number | null
  duplicate_approver_mode: DuplicateApproverMode
  apply_visibility_mode: ApplyVisibilityMode
  visible_department_ids: number[]
  visible_user_ids: number[]
  document_delivery: DocumentDeliverySettings
}

export const DEFAULT_DOCUMENT_DELIVERY = (): DocumentDeliverySettings => ({
  enabled: false,
  template_code: '',
  recipient_email_field: 'recipient_email',
  recipient_name_field: 'recipient_name',
  email_language_field: 'email_language',
  cc_email_field: 'recipient_email_cc',
})

export const DEFAULT_WORKFLOW_SETTINGS = (): WorkflowSettings => ({
  require_comment: true,
  require_comment_on_reject: true,
  require_handwritten_sign: false,
  require_handler_comment: false,
  allow_transfer: true,
  allow_revoke_after_approved: false,
  allow_add_sign: false,
  approver_empty_action: 'auto_approve',
  approver_empty_transfer_user_id: null,
  approver_resigned_action: 'auto_transfer',
  approver_resigned_transfer_user_id: null,
  handler_empty_action: 'auto_approve',
  handler_empty_transfer_user_id: null,
  handler_resigned_action: 'auto_transfer',
  handler_resigned_transfer_user_id: null,
  duplicate_approver_mode: 'every_node',
  apply_visibility_mode: 'all',
  visible_department_ids: [],
  visible_user_ids: [],
  document_delivery: DEFAULT_DOCUMENT_DELIVERY(),
})

export function mergeWorkflowSettings(raw?: Partial<WorkflowSettings>): WorkflowSettings {
  const base = DEFAULT_WORKFLOW_SETTINGS()
  const merged = { ...base, ...(raw || {}) }
  merged.document_delivery = {
    ...DEFAULT_DOCUMENT_DELIVERY(),
    ...(raw?.document_delivery || {}),
  }
  return merged
}
