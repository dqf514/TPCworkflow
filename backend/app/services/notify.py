# -*- coding: utf-8 -*-
import json
import re
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr

from flask import has_app_context

from app.extensions import db
from app.models import NotificationLog, SystemSetting, TaskInstance, User, WorkflowInstance
from app.services.email_content import (
    build_applicant_handler_prep_email,
    build_approval_email,
    build_instance_result_email,
    build_login_code_email,
    build_admin_confirm_code_email,
    build_node_extra_email,
    build_test_email,
)
from app.services.graph_utils import find_node, parse_graph, parse_variables

MAIL_CONFIG_KEYS = (
    'MAIL_SERVER',
    'MAIL_PORT',
    'MAIL_USE_TLS',
    'MAIL_USE_SSL',
    'MAIL_USERNAME',
    'MAIL_PASSWORD',
    'MAIL_DEFAULT_SENDER',
    'SMS_GATEWAY_URL',
    'SMS_API_KEY',
)


def get_mail_config(app, override: dict | None = None) -> dict:
    cfg = dict(app.config)
    for key in MAIL_CONFIG_KEYS:
        row = SystemSetting.query.get(key)
        if row and row.value is not None and str(row.value).strip() != '':
            raw = str(row.value).strip()
            if key == 'MAIL_PORT':
                try:
                    cfg[key] = int(raw)
                except ValueError:
                    pass
            elif key in ('MAIL_USE_TLS', 'MAIL_USE_SSL'):
                cfg[key] = raw.lower() not in ('0', 'false', 'no', 'off')
            else:
                cfg[key] = raw
    if override:
        for key, val in override.items():
            if key not in MAIL_CONFIG_KEYS or val is None:
                continue
            if key == 'MAIL_PORT':
                try:
                    cfg[key] = int(val)
                except (TypeError, ValueError):
                    cfg[key] = val
            elif key in ('MAIL_USE_TLS', 'MAIL_USE_SSL'):
                cfg[key] = str(val).lower() not in ('0', 'false', 'no', 'off')
            else:
                cfg[key] = str(val).strip() if val is not None else ''
    return cfg


def _resolve_sender(ec: dict) -> tuple[str, str]:
    """
    解析发件人：信封地址（纯邮箱）与 From 头（可含显示名）。
    阿里云等要求 MAIL FROM 为有效邮箱；仅填显示名（如 IMC Workflow）时自动拼接登录邮箱。
    """
    login_user = (ec.get('MAIL_USERNAME') or '').strip()
    raw = (ec.get('MAIL_DEFAULT_SENDER') or '').strip() or login_user
    if not raw:
        return '', ''

    name, addr = parseaddr(raw)
    if not addr or '@' not in str(addr):
        if '@' in raw:
            addr = raw.strip()
            name = ''
        elif login_user and '@' in login_user:
            addr = login_user
            name = raw.strip() if '@' not in raw else (name or '').strip()
        else:
            return '', ''

    display_name = (name or '').strip()
    if not display_name and '@' not in raw:
        display_name = raw.strip()
    header_from = formataddr((display_name, addr)) if display_name else addr
    return addr, header_from


def _log_notify(
    user_id,
    channel,
    subject,
    body,
    status,
    error=None,
    *,
    mail_type: str | None = None,
    recipient: str | None = None,
    task_id: int | None = None,
    instance_id: int | None = None,
    commit: bool = True,
):
    db.session.add(
        NotificationLog(
            user_id=user_id,
            channel=channel,
            mail_type=mail_type,
            recipient=(recipient or '')[:256] if recipient else None,
            task_id=task_id,
            instance_id=instance_id,
            subject=(subject or '')[:256],
            body=body,
            status=status,
            error_message=(error or '')[:512] if error else None,
        ),
    )
    if commit:
        db.session.commit()


def send_email(
    app,
    to_addr: str,
    subject: str,
    body: str,
    *,
    html_body: str | None = None,
    config_override: dict | None = None,
) -> tuple[bool, str]:
    ec = get_mail_config(app, config_override)
    server = ec.get('MAIL_SERVER')
    if not server:
        return False, '未配置 SMTP 服务器'
    if not to_addr:
        return False, '收件人为空'

    port = int(ec.get('MAIL_PORT') or 587)
    use_ssl = bool(ec.get('MAIL_USE_SSL'))
    use_tls = bool(ec.get('MAIL_USE_TLS'))
    user = ec.get('MAIL_USERNAME')
    password = ec.get('MAIL_PASSWORD')
    envelope_from, header_from = _resolve_sender(ec)
    if not envelope_from:
        return False, '未配置有效发件邮箱（发件人请填写邮箱或「显示名 <邮箱>」）'

    if html_body:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    else:
        msg = MIMEText(body, 'plain', 'utf-8')

    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = header_from
    msg['To'] = to_addr

    try:
        if use_ssl:
            smtp = smtplib.SMTP_SSL(server, port, timeout=30)
        else:
            smtp = smtplib.SMTP(server, port, timeout=30)
            smtp.ehlo()
            if use_tls:
                smtp.starttls()
                smtp.ehlo()
        if user and password:
            smtp.login(user, password)
        smtp.sendmail(envelope_from, [to_addr], msg.as_string())
        smtp.quit()
        return True, ''
    except Exception as exc:
        return False, str(exc)


def send_login_email_code(app, email: str, code: str, user_id: int | None = None) -> tuple[bool, str]:
    subject, text_body, html_body = build_login_code_email(code)
    ok, err = send_email(app, email, subject, text_body, html_body=html_body)
    _log_notify(
        user_id,
        'email',
        subject,
        text_body[:2000],
        'sent' if ok else 'failed',
        err,
        mail_type='login_code',
        recipient=email,
        commit=True,
    )
    return ok, err


def send_admin_confirm_email_code(
    app,
    email: str,
    purpose: str,
    code: str,
    *,
    user_id: int | None = None,
    operator_name: str = '',
) -> tuple[bool, str]:
    subject, text_body, html_body = build_admin_confirm_code_email(
        purpose=purpose,
        code=code,
        operator_name=operator_name,
    )
    ok, err = send_email(app, email, subject, text_body, html_body=html_body)
    _log_notify(
        user_id,
        'email',
        subject,
        text_body[:2000],
        'sent' if ok else 'failed',
        err,
        mail_type='admin_confirm_code',
        recipient=email,
        commit=True,
    )
    return ok, err


def send_test_email(
    app,
    to_addr: str,
    config_override: dict | None = None,
    *,
    operator_id: int | None = None,
) -> tuple[bool, str]:
    subject, text_body, html_body = build_test_email()
    ok, err = send_email(
        app,
        to_addr,
        subject,
        text_body,
        html_body=html_body,
        config_override=config_override,
    )
    _log_notify(
        operator_id,
        'email',
        subject,
        text_body[:2000],
        'sent' if ok else 'failed',
        err,
        mail_type='test',
        recipient=to_addr,
        commit=True,
    )
    return ok, err


def notify_approval_task_email(app, task_id: int) -> tuple[bool, str]:
    """待办创建后通知审批人（失败不阻断流程）。"""
    task = TaskInstance.query.get(task_id)
    if not task or task.status != 'pending':
        return False, '任务不存在或已处理'
    assignee = User.query.get(task.assignee_id)
    if not assignee or not assignee.email:
        return False, '审批人未配置邮箱'

    row = SystemSetting.query.get('PUBLIC_BASE_URL')
    if row and row.value and str(row.value).strip():
        public_base = str(row.value).strip().rstrip('/')
    else:
        public_base = (app.config.get('PUBLIC_BASE_URL') or '').strip().rstrip('/')
    subject, text_body, html_body = build_approval_email(
        task,
        public_base_url=public_base,
    )
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    ok, err = send_email(app, assignee.email, subject, text_body, html_body=html_body)
    _log_notify(
        assignee.id,
        'email',
        subject,
        text_body[:2000],
        'sent' if ok else 'failed',
        err,
        mail_type='approval_notify',
        recipient=assignee.email,
        task_id=task.id,
        instance_id=task.instance_id,
        commit=True,
    )
    return ok, err


def notify_pending_tasks(app, task_ids: list[int]) -> None:
    seen_extra_nodes: set[tuple[int, str]] = set()
    for tid in task_ids:
        try:
            notify_approval_task_email(app, tid)
        except Exception:
            pass
        try:
            task = TaskInstance.query.get(tid)
            if not task:
                continue
            node_key = (task.instance_id, task.node_id)
            if node_key in seen_extra_nodes:
                continue
            seen_extra_nodes.add(node_key)
            notify_node_extra_emails(app, tid)
        except Exception:
            pass
    try:
        notify_applicant_handler_prep_for_tasks(app, task_ids)
    except Exception:
        pass


def notify_applicant_handler_prep_for_tasks(app, task_ids: list[int]) -> None:
    """办理人节点生成待办时，按节点配置通知申请人准备材料（每节点每单仅一次）。"""
    seen: set[tuple[int, str]] = set()
    for tid in task_ids:
        task = TaskInstance.query.get(tid)
        if not task or task.node_type != 'handler':
            continue
        key = (task.instance_id, task.node_id)
        if key in seen:
            continue
        seen.add(key)
        notify_applicant_handler_prep(app, task.instance_id, task.node_id)


def notify_applicant_handler_prep(app, instance_id: int, node_id: str) -> tuple[bool, str]:
    """进入办理人节点时通知申请人（失败不阻断流程）。"""
    inst = WorkflowInstance.query.get(instance_id)
    if not inst or not inst.definition:
        return False, '实例不存在'
    graph = parse_graph(inst.definition.process_graph)
    node = find_node(graph, node_id) or {}
    if node.get('type') != 'handler':
        return False, '非办理节点'
    cfg = (node.get('config') or {}).get('notify_applicant_on_enter') or {}
    if not cfg.get('enabled'):
        return False, '未启用'

    variables = parse_variables(inst.variables)
    notified = list(variables.get('_sys_handler_prep') or [])
    if node_id in notified:
        return False, '已通知'

    initiator = User.query.get(inst.initiator_id)
    if not initiator or not initiator.email:
        return False, '申请人未配置邮箱'

    subject, text_body, html_body = build_applicant_handler_prep_email(
        inst,
        node,
        public_base_url=_public_base_url(app),
        subject_tpl=cfg.get('subject'),
        body_tpl=cfg.get('body'),
    )

    notified.append(node_id)
    variables['_sys_handler_prep'] = notified
    inst.variables = json.dumps(variables, ensure_ascii=False)
    try:
        db.session.flush()
    except Exception:
        db.session.rollback()
        return False, '状态更新失败'

    ok, err = send_email(app, initiator.email, subject, text_body, html_body=html_body)
    _log_notify(
        initiator.id,
        'email',
        subject,
        text_body[:2000],
        'sent' if ok else 'failed',
        err,
        mail_type='applicant_handler_prep',
        recipient=initiator.email,
        instance_id=inst.id,
        commit=True,
    )
    return ok, err


_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _resolve_extra_email_recipients(
    inst: WorkflowInstance,
    send_email: dict,
    *,
    exclude_assignee_id: int | None = None,
) -> list[tuple[str, str, int | None]]:
    """解析节点额外发邮件收件人，返回 [(email, display_name, user_id)]。"""
    recipients: list[tuple[str, str, int | None]] = []
    recipient_type = send_email.get('recipient_type') or 'org_user'
    assignee_email = ''
    if exclude_assignee_id:
        assignee = User.query.get(exclude_assignee_id)
        if assignee and assignee.email:
            assignee_email = assignee.email.strip().lower()

    if recipient_type == 'org_user':
        for raw_uid in send_email.get('user_ids') or []:
            try:
                uid = int(raw_uid)
            except (TypeError, ValueError):
                continue
            user = User.query.get(uid)
            if not user or not user.email:
                continue
            email = user.email.strip()
            if not email or email.lower() == assignee_email:
                continue
            recipients.append((email, user.display_label(), user.id))
    elif recipient_type == 'form_field':
        field_key = (send_email.get('field_key') or '').strip()
        if not field_key:
            return []
        variables = parse_variables(inst.variables)
        form_data = variables.get('form') or {}
        raw = form_data.get(field_key)
        if raw is None or raw == '':
            return []
        email = str(raw).strip()
        if not _EMAIL_RE.match(email):
            return []
        if assignee_email and email.lower() == assignee_email:
            return []
        recipients.append((email, email, None))

    deduped: list[tuple[str, str, int | None]] = []
    seen: set[str] = set()
    for email, name, uid in recipients:
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append((email, name, uid))
    return deduped


def _resolve_node_extra_email_recipients(
    task: TaskInstance,
    send_email: dict,
) -> list[tuple[str, str, int | None]]:
    inst = task.instance
    if not inst:
        return []
    return _resolve_extra_email_recipients(
        inst,
        send_email,
        exclude_assignee_id=task.assignee_id,
    )


def _extra_email_use_custom_template(send_email: dict) -> bool:
    return bool((send_email.get('subject') or '').strip() or (send_email.get('body') or '').strip())


def _send_node_extra_emails(
    app,
    *,
    inst: WorkflowInstance,
    node: dict,
    email_cfg: dict,
    trigger: str,
    task: TaskInstance | None,
    mail_type: str,
) -> None:
    if not email_cfg.get('enabled'):
        return
    if (email_cfg.get('trigger') or 'on_enter') != trigger:
        return

    recipients = _resolve_extra_email_recipients(
        inst,
        email_cfg,
        exclude_assignee_id=task.assignee_id if task else None,
    )
    if not recipients:
        return

    public_base = _public_base_url(app)
    subject_tpl = email_cfg.get('subject')
    body_tpl = email_cfg.get('body')
    use_custom = _extra_email_use_custom_template(email_cfg) or trigger == 'on_complete'

    for email, name, user_id in recipients:
        if use_custom or trigger == 'on_complete':
            subject, text_body, html_body = build_node_extra_email(
                inst,
                node,
                public_base_url=public_base,
                recipient_name=name,
                trigger=trigger,
                subject_tpl=subject_tpl,
                body_tpl=body_tpl,
            )
        elif task:
            subject, text_body, html_body = build_approval_email(
                task,
                public_base_url=public_base,
                recipient_name=name,
                include_quick_actions=False,
            )
        else:
            continue

        ok, err = send_email(app, email, subject, text_body, html_body=html_body)
        _log_notify(
            user_id,
            'email',
            subject,
            text_body[:2000],
            'sent' if ok else 'failed',
            err,
            mail_type=mail_type,
            recipient=email,
            task_id=task.id if task else None,
            instance_id=inst.id,
            commit=True,
        )


def _mark_node_extra_email_sent(inst: WorkflowInstance, node_id: str, trigger: str) -> bool:
    """标记该节点该时机的额外邮件已发送；若已发送返回 False。"""
    key = f'{node_id}:{trigger}'
    variables = parse_variables(inst.variables)
    sent = list(variables.get('_sys_node_extra_email') or [])
    if key in sent:
        return False
    sent.append(key)
    variables['_sys_node_extra_email'] = sent
    inst.variables = json.dumps(variables, ensure_ascii=False)
    try:
        db.session.flush()
    except Exception:
        db.session.rollback()
        return False
    return True


def notify_node_extra_emails(app, task_id: int) -> None:
    """节点到达时：额外发邮件（与待办通知并行）。"""
    task = TaskInstance.query.get(task_id)
    if not task or task.status != 'pending':
        return
    inst = task.instance
    definition = inst.definition if inst else None
    if not definition or not inst:
        return
    graph = parse_graph(definition.process_graph)
    node = find_node(graph, task.node_id) or {}
    config = node.get('config') or {}
    send_email = config.get('send_email') or {}
    if not send_email.get('enabled'):
        return
    if (send_email.get('trigger') or 'on_enter') != 'on_enter':
        return

    _send_node_extra_emails(
        app,
        inst=inst,
        node=node,
        email_cfg=send_email,
        trigger='on_enter',
        task=task,
        mail_type='node_extra_email',
    )


def notify_node_extra_emails_on_complete(
    app,
    instance_id: int,
    node_id: str,
    completed_task_id: int | None = None,
) -> None:
    """节点全部审批/办理完成后：按配置向额外收件人发邮件。"""
    inst = WorkflowInstance.query.get(instance_id)
    if not inst or not inst.definition:
        return
    graph = parse_graph(inst.definition.process_graph)
    node = find_node(graph, node_id) or {}
    config = node.get('config') or {}
    send_email = config.get('send_email') or {}
    if not send_email.get('enabled'):
        return
    if send_email.get('trigger') != 'on_complete':
        return
    if not _mark_node_extra_email_sent(inst, node_id, 'on_complete'):
        return

    task = TaskInstance.query.get(completed_task_id) if completed_task_id else None
    _send_node_extra_emails(
        app,
        inst=inst,
        node=node,
        email_cfg=send_email,
        trigger='on_complete',
        task=task,
        mail_type='node_extra_email_complete',
    )


def _public_base_url(app) -> str:
    row = SystemSetting.query.get('PUBLIC_BASE_URL')
    if row and row.value and str(row.value).strip():
        return str(row.value).strip().rstrip('/')
    return (app.config.get('PUBLIC_BASE_URL') or '').strip().rstrip('/')


def notify_instance_result_email(app, instance_id: int) -> tuple[bool, str]:
    """流程结束（通过/驳回）后通知申请人（失败不阻断流程）。"""
    inst = WorkflowInstance.query.get(instance_id)
    if not inst or inst.status not in ('approved', 'rejected'):
        return False, '实例未结束或状态无需通知'
    initiator = User.query.get(inst.initiator_id)
    if not initiator or not initiator.email:
        return False, '申请人未配置邮箱'

    subject, text_body, html_body = build_instance_result_email(
        inst,
        public_base_url=_public_base_url(app),
    )
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    ok, err = send_email(app, initiator.email, subject, text_body, html_body=html_body)
    _log_notify(
        initiator.id,
        'email',
        subject,
        text_body[:2000],
        'sent' if ok else 'failed',
        err,
        mail_type='instance_result',
        recipient=initiator.email,
        instance_id=inst.id,
        commit=True,
    )
    return ok, err


def notify_instance_result_if_finished(app, inst: WorkflowInstance) -> None:
    if inst.status not in ('approved', 'rejected') or not inst.finished_at:
        return
    if inst.status == 'approved':
        try:
            from app.services.receipt_duplicate_service import sync_receipt_usage_for_instance

            sync_receipt_usage_for_instance(inst)
            db.session.commit()
        except Exception:
            db.session.rollback()
    try:
        notify_instance_result_email(app, inst.id)
    except Exception:
        pass
    if inst.status == 'approved':
        try:
            from app.services.document_delivery import maybe_deliver_document

            maybe_deliver_document(app, inst)
        except Exception:
            pass


def send_login_sms_code(
    app,
    phone: str,
    code: str,
    user_id: int | None = None,
) -> tuple[bool, str]:
    """短信网关未配置时写入日志供开发调试。"""
    ec = get_mail_config(app)
    gateway = ec.get('SMS_GATEWAY_URL')
    if not gateway:
        _log_notify(
            user_id,
            'sms',
            '登录验证码',
            f'手机号 {phone} 验证码 {code}（未配置网关，仅记录）',
            'dev_log',
            mail_type='sms_login',
            recipient=phone,
        )
        return True, ''
    try:
        import urllib.parse
        import urllib.request

        data = urllib.parse.urlencode({
            'phone': phone,
            'code': code,
            'key': ec.get('SMS_API_KEY') or '',
        }).encode()
        urllib.request.urlopen(gateway, data=data, timeout=15)
        _log_notify(
            user_id,
            'sms',
            '登录验证码',
            f'已发送至 {phone}',
            'sent',
            mail_type='sms_login',
            recipient=phone,
        )
        return True, ''
    except Exception as exc:
        _log_notify(
            user_id,
            'sms',
            '登录验证码',
            f'发送至 {phone}',
            'failed',
            str(exc),
            mail_type='sms_login',
            recipient=phone,
        )
        return False, str(exc)
