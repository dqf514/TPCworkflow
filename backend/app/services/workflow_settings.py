# -*- coding: utf-8 -*-
"""流程模板级高级设置（参考企业微信审批）。"""
import json

DEFAULT_WORKFLOW_SETTINGS = {
    'require_comment': True,
    'require_comment_on_reject': True,
    'require_handwritten_sign': False,
    'require_handler_comment': False,
    'allow_transfer': True,
    'allow_revoke_after_approved': False,
    'allow_add_sign': False,
    'approver_empty_action': 'auto_approve',
    'approver_empty_transfer_user_id': None,
    'approver_resigned_action': 'auto_transfer',
    'approver_resigned_transfer_user_id': None,
    'handler_empty_action': 'auto_approve',
    'handler_empty_transfer_user_id': None,
    'handler_resigned_action': 'auto_transfer',
    'handler_resigned_transfer_user_id': None,
    'duplicate_approver_mode': 'every_node',
    'apply_visibility_mode': 'all',
    'visible_department_ids': [],
    'visible_user_ids': [],
    'document_delivery': {
        'enabled': False,
        'template_code': '',
        'recipient_email_field': 'recipient_email',
        'recipient_name_field': 'recipient_name',
        'email_language_field': 'email_language',
        'cc_email_field': 'recipient_email_cc',
    },
}


def merge_settings(raw: str | None) -> dict:
    base = json.loads(json.dumps(DEFAULT_WORKFLOW_SETTINGS))
    if not raw:
        return base
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            base.update(data)
    except (json.JSONDecodeError, TypeError):
        pass
    return base
