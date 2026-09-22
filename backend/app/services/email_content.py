# -*- coding: utf-8 -*-
"""审批待办邮件：中文摘要、系统内链接、可选快速审批。"""
from __future__ import annotations

import json
import re
from datetime import datetime
from html import escape

from app.models import Department, InstanceTimeline, TaskInstance, User, WorkflowInstance
from app.services.instance_access import ensure_instance_public_uuid
from app.services.approval_token import create_task_email_token
from app.utils.branding import APP_DISPLAY_NAME, EMAIL_FOOTER_LINE
from app.services.form_schema import flatten_fields, resolve_definition_schema
from app.services.graph_utils import find_node, parse_graph, parse_variables, resolve_node_display_name


def _fmt_time(dt: datetime | None) -> str:
    if not dt:
        return '—'
    return dt.strftime('%Y-%m-%d %H:%M')


def _money_numeric(val) -> float | None:
    if val is None or val == '':
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        for key in ('rmb_amount', 'amount'):
            n = val.get(key)
            if n not in (None, ''):
                try:
                    return float(n)
                except (TypeError, ValueError):
                    continue
    return None


def _format_money_total(total: float, currency: str = 'CNY') -> str:
    if currency == 'CNY':
        return f'￥{total:.2f}'
    return f'{total:.2f} {currency}'


def _extract_dept_ids(val) -> list[int]:
    if val is None or val == '':
        return []
    if isinstance(val, list):
        ids: list[int] = []
        for item in val:
            ids.extend(_extract_dept_ids(item))
        return ids
    if isinstance(val, dict):
        for key in ('id', 'department_id', 'value', 'dept_id'):
            raw = val.get(key)
            if raw not in (None, ''):
                try:
                    return [int(raw)]
                except (TypeError, ValueError):
                    continue
        return []
    try:
        return [int(val)]
    except (TypeError, ValueError):
        return []


def _dept_picker_label(val) -> str:
    if val is None or val == '':
        return '—'
    if isinstance(val, dict):
        label = val.get('label') or val.get('name') or val.get('display_name')
        if label:
            return str(label)
    if isinstance(val, list):
        parts = [_dept_picker_label(x) for x in val]
        parts = [p for p in parts if p != '—']
        return '、'.join(parts) if parts else '—'
    dept_ids = _extract_dept_ids(val)
    if not dept_ids:
        return '—'
    names: list[str] = []
    for dept_id in dept_ids:
        dept = Department.query.get(dept_id)
        names.append(dept.name if dept else str(dept_id))
    return '、'.join(names)


def _detail_total_text(field: dict, val) -> str | None:
    if not isinstance(val, list) or not val:
        return None
    columns = (field.get('props') or {}).get('columns') or []
    money_cols = [c for c in columns if c.get('type') in ('money', 'plain_amount') and c.get('key')]
    if not money_cols:
        return None
    total = 0.0
    has_any = False
    for row in val:
        if not isinstance(row, dict):
            continue
        for col in money_cols:
            n = _money_numeric(row.get(col['key']))
            if n is not None:
                total += n
                has_any = True
    if not has_any:
        return None
    return _format_money_total(total)


def _format_field_value(field: dict, val) -> str:
    if val is None or val == '':
        return '—'
    ftype = field.get('type')
    if ftype == 'dept_picker':
        return _dept_picker_label(val)
    if ftype == 'switch':
        return '是' if val else '否'
    if ftype == 'money' and isinstance(val, dict):
        amt = val.get('amount', '')
        cur = val.get('currency') or val.get('unit') or 'CNY'
        return f'￥{amt} {cur}'.strip() if amt not in (None, '') else '—'
    if ftype == 'plain_amount':
        n = _money_numeric(val)
        return _format_money_total(n) if n is not None else '—'
    if ftype == 'date_range':
        from app.services.date_range_value import format_date_range_value, uses_half_day
        return format_date_range_value(val, half_day=uses_half_day(field)) or '—'
    if ftype == 'record_set' and isinstance(val, dict):
        data = val.get('data') or {}
        if not isinstance(data, dict):
            return '—'
        parts = [f'{v}' for v in data.values() if str(v or '').strip()]
        return '；'.join(parts[:5]) if parts else '—'
    if ftype == 'detail' and isinstance(val, list):
        chunks: list[str] = []
        for row in val[:3]:
            if not isinstance(row, dict):
                continue
            parts = [str(v) for v in row.values() if v not in (None, '', [], {})]
            if parts:
                chunks.append(' / '.join(parts)[:120])
        if len(val) > 3:
            chunks.append(f'…共 {len(val)} 行')
        return '；'.join(chunks) if chunks else '—'
    if ftype in ('multi_select', 'checkbox_group') and isinstance(val, list):
        return '、'.join(str(x) for x in val) if val else '—'
    if isinstance(val, list):
        return '、'.join(str(x) for x in val)
    if isinstance(val, dict):
        label = val.get('label') or val.get('name') or val.get('display_name')
        if label:
            return str(label)
        return json.dumps(val, ensure_ascii=False)
    return str(val)


def build_form_summary_lines(inst: WorkflowInstance, max_lines: int = 10) -> list[str]:
    definition = inst.definition
    if not definition:
        return []
    schema = resolve_definition_schema(definition)
    variables = parse_variables(inst.variables)
    form_data = variables.get('form') or {}
    lines: list[str] = []
    for field in flatten_fields(schema):
        ftype = field.get('type')
        if ftype in ('divider', 'text_block', 'section_title', 'attachment', 'image', 'serial_no'):
            continue
        key = field.get('key')
        if not key:
            continue
        label = (field.get('label') or key).strip()
        raw = form_data.get(key)
        if ftype == 'detail':
            total_text = _detail_total_text(field, raw)
            if total_text:
                lines.append(f'合计金额：{total_text}')
            continue
        val = _format_field_value(field, raw)
        if val == '—':
            continue
        lines.append(f'{label}：{val}')
        if len(lines) >= max_lines:
            lines.append('…')
            break
    return lines


def _public_base(public_base_url: str) -> str:
    return (public_base_url or '').strip().rstrip('/')


def build_approval_email(
    task: TaskInstance,
    *,
    public_base_url: str,
    recipient_name: str | None = None,
    include_quick_actions: bool = True,
) -> tuple[str, str, str]:
    """返回 (subject, text_body, html_body)。

    recipient_name: 覆盖问候语中的收件人名称（额外发邮件时使用）。
    include_quick_actions: 是否包含快速同意/驳回链接（仅审批人待办邮件为 True）。
    """
    inst = task.instance
    definition = inst.definition
    assignee = User.query.get(task.assignee_id)
    initiator = User.query.get(inst.initiator_id)
    graph = parse_graph(definition.process_graph if definition else None)
    node = find_node(graph, task.node_id) or {}
    node_label = resolve_node_display_name(node, task.node_id)
    flow_name = definition.name if definition else '审批流程'
    assignee_name = assignee.display_label() if assignee else ''
    initiator_name = initiator.display_label() if initiator else ''
    dept_name = ''
    if inst.department_id:
        d = Department.query.get(inst.department_id)
        dept_name = d.name if d else ''

    base = _public_base(public_base_url)
    task_url = f'{base}/tasks/{task.id}' if base else ''

    quick_approve_url = ''
    quick_reject_url = ''
    show_quick = False
    if include_quick_actions:
        approve_token = create_task_email_token(task, 'approve')
        reject_token = create_task_email_token(task, 'reject')
        quick_approve_url = (
            f'{base}/api/v1/workflow/tasks/email-action?token={approve_token}' if base and approve_token else ''
        )
        quick_reject_url = (
            f'{base}/api/v1/workflow/tasks/email-action?token={reject_token}' if base and reject_token else ''
        )
        show_quick = bool(quick_approve_url or quick_reject_url)

    display_no = (inst.display_no or '').strip() or f'#{inst.id}'
    summary_lines = build_form_summary_lines(inst)
    summary_block = '\n'.join(f'  · {line}' for line in summary_lines) if summary_lines else '  · （无摘要字段）'

    subject = f'【待审批】{flow_name} · {initiator_name}（{display_no}）'
    greet_name = (recipient_name or assignee_name or '').strip()
    greet_line = f'{greet_name}，您好：' if greet_name else '您好：'

    text_parts = [
        greet_line,
        '',
        f'您有一条待审批任务，请查阅以下摘要后处理。',
        '',
        f'流程名称：{flow_name}',
        f'审批编号：{display_no}',
        f'当前环节：{node_label}',
        f'申请人：{initiator_name}',
        f'申请部门：{dept_name or "—"}',
        f'提交时间：{_fmt_time(inst.started_at)}',
        '',
        '申请内容摘要：',
        summary_block,
        '',
    ]
    if task_url:
        text_parts.extend(['进入系统审批：', task_url, ''])
    if show_quick:
        text_parts.append('快速处理（链接 7 日内有效，仅可使用一次）：')
        if quick_approve_url:
            text_parts.extend(['  同意：', quick_approve_url])
        if quick_reject_url:
            text_parts.extend(['  驳回：', quick_reject_url])
        text_parts.append('')
    text_parts.append(EMAIL_FOOTER_LINE)
    text_body = '\n'.join(text_parts)

    summary_html = '<br/>'.join(escape(line) for line in summary_lines) if summary_lines else '（无）'
    btn_style = (
        'display:inline-block;margin:8px 12px 8px 0;padding:10px 20px;'
        'border-radius:6px;text-decoration:none;font-size:14px;'
    )
    buttons = []
    if task_url:
        buttons.append(
            f'<a href="{escape(task_url)}" style="{btn_style}background:#165DFF;color:#fff;">'
            '进入系统查看并审批</a>',
        )
    if quick_approve_url:
        buttons.append(
            f'<a href="{escape(quick_approve_url)}" style="{btn_style}background:#00B42A;color:#fff;">'
            '快速同意</a>',
        )
    if quick_reject_url:
        buttons.append(
            f'<a href="{escape(quick_reject_url)}" style="{btn_style}background:#F53F3F;color:#fff;">'
            '快速驳回</a>',
        )
    quick_hint = ''
    if show_quick:
        quick_hint = (
            '<p style="color:#86909c;font-size:12px;">'
            '快速操作无需登录；若流程要求填写意见或手写签名，请使用「进入系统」链接。'
            '</p>'
        )

    html_body = f"""<!DOCTYPE html><html><body style="font-family:'Segoe UI',PingFang SC,Microsoft YaHei,sans-serif;font-size:14px;color:#1d2129;line-height:1.6;">
<p>{escape(greet_line)}</p>
<p>您有一条待审批任务，摘要如下。</p>
<table style="width:100%;border-collapse:collapse;margin:12px 0;background:#f7f8fa;border-radius:8px;">
<tr>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">流程</th>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">审批编号</th>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">环节</th>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">申请人</th>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">部门</th>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">提交时间</th>
</tr>
<tr>
<td style="padding:8px 12px;"><b>{escape(flow_name)}</b></td>
<td style="padding:8px 12px;">{escape(display_no)}</td>
<td style="padding:8px 12px;">{escape(node_label)}</td>
<td style="padding:8px 12px;">{escape(initiator_name)}</td>
<td style="padding:8px 12px;">{escape(dept_name or '—')}</td>
<td style="padding:8px 12px;">{_fmt_time(inst.started_at)}</td>
</tr>
</table>
<p><b>申请内容摘要</b></p>
<p style="margin:0 0 16px;">{summary_html}</p>
<p>{''.join(buttons)}</p>
{quick_hint}
<p style="color:#86909c;font-size:12px;margin-top:24px;">{escape(EMAIL_FOOTER_LINE)}</p>
</body></html>"""

    return subject, text_body, html_body


def _last_reject_comment(inst: WorkflowInstance) -> str:
    row = (
        InstanceTimeline.query.filter_by(instance_id=inst.id)
        .filter(InstanceTimeline.action.in_(('reject', 'rejected')))
        .order_by(InstanceTimeline.id.desc())
        .first()
    )
    return (row.comment or '').strip() if row else ''


def build_instance_result_email(
    inst: WorkflowInstance,
    *,
    public_base_url: str,
) -> tuple[str, str, str]:
    """流程结束（通过/驳回）时通知申请人。返回 (subject, text_body, html_body)。"""
    definition = inst.definition
    initiator = User.query.get(inst.initiator_id)
    flow_name = definition.name if definition else '审批流程'
    initiator_name = initiator.display_label() if initiator else ''
    dept_name = ''
    if inst.department_id:
        d = Department.query.get(inst.department_id)
        dept_name = d.name if d else ''

    status = (inst.status or '').strip()
    if status == 'approved':
        result_label = '审批通过'
        intro = '您的申请已完成审批，结果为：审批通过。'
    else:
        result_label = '审批驳回'
        intro = '您的申请已完成审批，结果为：审批驳回。'

    display_no = (inst.display_no or '').strip() or f'#{inst.id}'
    public_uuid = ensure_instance_public_uuid(inst)
    base = _public_base(public_base_url)
    detail_url = f'{base}/instances/{public_uuid}' if base and public_uuid else ''

    summary_lines = build_form_summary_lines(inst)
    summary_block = '\n'.join(f'  · {line}' for line in summary_lines) if summary_lines else '  · （无摘要字段）'
    reject_comment = _last_reject_comment(inst) if status == 'rejected' else ''

    subject = f'【{result_label}】{flow_name}（{display_no}）'

    text_parts = [
        f'{initiator_name}，您好：',
        '',
        intro,
        '',
        f'流程名称：{flow_name}',
        f'审批编号：{display_no}',
        f'审批结果：{result_label}',
        f'申请部门：{dept_name or "—"}',
        f'提交时间：{_fmt_time(inst.started_at)}',
        f'完成时间：{_fmt_time(inst.finished_at)}',
    ]
    if reject_comment:
        text_parts.append(f'驳回意见：{reject_comment}')
    text_parts.extend([
        '',
        '申请内容摘要：',
        summary_block,
        '',
    ])
    if detail_url:
        text_parts.extend(['查看申请详情：', detail_url, ''])
    text_parts.append(EMAIL_FOOTER_LINE)
    text_body = '\n'.join(text_parts)

    summary_html = '<br/>'.join(escape(line) for line in summary_lines) if summary_lines else '（无）'
    result_color = '#00B42A' if status == 'approved' else '#F53F3F'
    reject_block = ''
    if reject_comment:
        reject_block = (
            f'<p><b>驳回意见</b></p>'
            f'<p style="margin:0 0 16px;">{escape(reject_comment)}</p>'
        )
    btn_style = (
        'display:inline-block;margin:8px 12px 8px 0;padding:10px 20px;'
        'border-radius:6px;text-decoration:none;font-size:14px;'
    )
    detail_btn = ''
    if detail_url:
        detail_btn = (
            f'<a href="{escape(detail_url)}" style="{btn_style}background:#165DFF;color:#fff;">'
            '查看申请详情</a>'
        )

    html_body = f"""<!DOCTYPE html><html><body style="font-family:'Segoe UI',PingFang SC,Microsoft YaHei,sans-serif;font-size:14px;color:#1d2129;line-height:1.6;">
<p>{escape(initiator_name)}，您好：</p>
<p>{escape(intro)}</p>
<table style="width:100%;border-collapse:collapse;margin:12px 0;background:#f7f8fa;border-radius:8px;">
<tr>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">流程</th>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">审批编号</th>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">审批结果</th>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">申请部门</th>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">提交时间</th>
<th style="padding:8px 12px;color:#86909c;font-weight:normal;text-align:left;">完成时间</th>
</tr>
<tr>
<td style="padding:8px 12px;"><b>{escape(flow_name)}</b></td>
<td style="padding:8px 12px;">{escape(display_no)}</td>
<td style="padding:8px 12px;"><b style="color:{result_color};">{escape(result_label)}</b></td>
<td style="padding:8px 12px;">{escape(dept_name or '—')}</td>
<td style="padding:8px 12px;">{_fmt_time(inst.started_at)}</td>
<td style="padding:8px 12px;">{_fmt_time(inst.finished_at)}</td>
</tr>
</table>
{reject_block}
<p><b>申请内容摘要</b></p>
<p style="margin:0 0 16px;">{summary_html}</p>
<p>{detail_btn}</p>
<p style="color:#86909c;font-size:12px;margin-top:24px;">{escape(EMAIL_FOOTER_LINE)}</p>
</body></html>"""

    return subject, text_body, html_body


_HANDLER_PREP_PLACEHOLDER_RE = re.compile(r'\{\{(\w+)\}\}')


def _render_handler_prep_template(text: str, ctx: dict) -> str:
    if not text:
        return ''

    def repl(m):
        return str(ctx.get(m.group(1), ''))

    return _HANDLER_PREP_PLACEHOLDER_RE.sub(repl, text)


def build_applicant_handler_prep_email(
    inst: WorkflowInstance,
    handler_node: dict,
    *,
    public_base_url: str,
    subject_tpl: str | None = None,
    body_tpl: str | None = None,
) -> tuple[str, str, str]:
    """进入办理人节点时通知申请人准备材料。返回 (subject, text_body, html_body)。"""
    definition = inst.definition
    initiator = User.query.get(inst.initiator_id)
    flow_name = definition.name if definition else '审批流程'
    initiator_name = initiator.display_label() if initiator else ''
    display_no = (inst.display_no or '').strip() or f'#{inst.id}'
    public_uuid = ensure_instance_public_uuid(inst)
    base = _public_base(public_base_url)
    detail_url = f'{base}/instances/{public_uuid}' if base and public_uuid else ''
    handler_node_name = resolve_node_display_name(handler_node, handler_node.get('id'))

    ctx = {
        'flow_name': flow_name,
        'display_no': display_no,
        'initiator_name': initiator_name,
        'detail_url': detail_url,
        'handler_node_name': handler_node_name,
    }

    default_subject = f'【审批通过】请准备票据交财务部（{display_no}）'
    default_body = (
        f'{initiator_name}，您好：\n\n'
        f'您的「{flow_name}」（审批编号 {display_no}）已通过审批。\n\n'
        '请打印申请单并备好相关票据、发票原件，提交至财务部办理付款。'
        '财务部办结后您将收到最终通知。\n\n'
        + (f'查看详情：\n{detail_url}\n\n' if detail_url else '')
        + EMAIL_FOOTER_LINE
    )

    subject = _render_handler_prep_template((subject_tpl or '').strip() or default_subject, ctx)
    body_core = _render_handler_prep_template((body_tpl or '').strip(), ctx) if (body_tpl or '').strip() else ''
    if body_core:
        text_body = body_core
        if detail_url and detail_url not in text_body and '{{detail_url}}' not in (body_tpl or ''):
            text_body += f'\n\n查看详情：\n{detail_url}'
        if EMAIL_FOOTER_LINE not in text_body:
            text_body += f'\n\n{EMAIL_FOOTER_LINE}'
    else:
        text_body = default_body

    summary_lines = build_form_summary_lines(inst)
    summary_html = '<br/>'.join(escape(line) for line in summary_lines) if summary_lines else '（无）'
    body_html = escape(body_core or (
        f'您的「{flow_name}」（审批编号 {display_no}）已通过审批。\n\n'
        '请打印申请单并备好相关票据、发票原件，提交至财务部办理付款。'
        '财务部办结后您将收到最终通知。'
    )).replace('\n', '<br/>')

    detail_btn = ''
    if detail_url:
        btn_style = (
            'display:inline-block;margin:8px 12px 8px 0;padding:10px 20px;'
            'border-radius:6px;text-decoration:none;font-size:14px;'
        )
        detail_btn = (
            f'<a href="{escape(detail_url)}" style="{btn_style}background:#165DFF;color:#fff;">'
            '查看申请详情</a>'
        )

    html_body = f"""<!DOCTYPE html><html><body style="font-family:'Segoe UI',PingFang SC,Microsoft YaHei,sans-serif;font-size:14px;color:#1d2129;line-height:1.6;">
<p>{escape(initiator_name)}，您好：</p>
<p>{body_html}</p>
<p><b>申请内容摘要</b></p>
<p style="margin:0 0 16px;">{summary_html}</p>
<p>{detail_btn}</p>
<p style="color:#86909c;font-size:12px;margin-top:24px;">{escape(EMAIL_FOOTER_LINE)}</p>
</body></html>"""

    return subject, text_body, html_body


def build_node_extra_email(
    inst: WorkflowInstance,
    node: dict,
    *,
    public_base_url: str,
    recipient_name: str,
    trigger: str = 'on_enter',
    subject_tpl: str | None = None,
    body_tpl: str | None = None,
) -> tuple[str, str, str]:
    definition = inst.definition
    flow_name = definition.name if definition else '审批流程'
    initiator = User.query.get(inst.initiator_id)
    initiator_name = initiator.display_label() if initiator else ''
    display_no = (inst.display_no or '').strip() or f'#{inst.id}'
    public_uuid = ensure_instance_public_uuid(inst)
    base = _public_base(public_base_url)
    detail_url = f'{base}/instances/{public_uuid}' if base and public_uuid else ''
    node_name = resolve_node_display_name(node, node.get('id'))

    summary_lines = build_form_summary_lines(inst)
    form_summary = '\n'.join(f'· {line}' for line in summary_lines) if summary_lines else '（无摘要）'

    ctx = {
        'flow_name': flow_name,
        'display_no': display_no,
        'initiator_name': initiator_name,
        'node_name': node_name,
        'recipient_name': recipient_name or '您好',
        'detail_url': detail_url,
        'form_summary': form_summary,
    }

    if trigger == 'on_complete':
        default_subject = f'【{node_name}已完成】{flow_name}（{display_no}）'
        default_body = (
            f'{recipient_name or "您好"}：\n\n'
            f'关于「{flow_name}」（审批编号 {display_no}），「{node_name}」环节已办理完成。\n\n'
            f'申请内容摘要：\n{form_summary}\n\n'
            + (f'查看详情：\n{detail_url}\n\n' if detail_url else '')
            + EMAIL_FOOTER_LINE
        )
    else:
        default_subject = f'【流程到达】{flow_name} · {node_name}（{display_no}）'
        default_body = (
            f'{recipient_name or "您好"}：\n\n'
            f'流程「{flow_name}」（审批编号 {display_no}）已进入「{node_name}」环节。\n'
            f'申请人：{initiator_name}\n\n'
            f'申请内容摘要：\n{form_summary}\n\n'
            + (f'查看详情：\n{detail_url}\n\n' if detail_url else '')
            + EMAIL_FOOTER_LINE
        )

    subject = _render_handler_prep_template((subject_tpl or '').strip() or default_subject, ctx)
    body_core = _render_handler_prep_template((body_tpl or '').strip(), ctx) if (body_tpl or '').strip() else ''
    if body_core:
        text_body = body_core
        if detail_url and detail_url not in text_body and '{{detail_url}}' not in (body_tpl or ''):
            text_body += f'\n\n查看详情：\n{detail_url}'
        if EMAIL_FOOTER_LINE not in text_body:
            text_body += f'\n\n{EMAIL_FOOTER_LINE}'
    else:
        text_body = default_body

    body_html = escape(body_core or text_body.split(EMAIL_FOOTER_LINE)[0].strip()).replace('\n', '<br/>')
    greet = f'{escape(recipient_name)}，您好：' if recipient_name and recipient_name != '您好' else '您好：'
    detail_btn = ''
    if detail_url:
        btn_style = (
            'display:inline-block;margin:8px 12px 8px 0;padding:10px 20px;'
            'border-radius:6px;text-decoration:none;font-size:14px;'
        )
        detail_btn = (
            f'<a href="{escape(detail_url)}" style="{btn_style}background:#165DFF;color:#fff;">'
            '查看申请详情</a>'
        )

    html_body = f"""<!DOCTYPE html><html><body style="font-family:'Segoe UI',PingFang SC,Microsoft YaHei,sans-serif;font-size:14px;color:#1d2129;line-height:1.6;">
<p>{greet}</p>
<p>{body_html}</p>
<p>{detail_btn}</p>
<p style="color:#86909c;font-size:12px;margin-top:24px;">{escape(EMAIL_FOOTER_LINE)}</p>
</body></html>"""

    return subject, text_body, html_body


def build_login_code_email(code: str) -> tuple[str, str, str]:
    subject = f'{APP_DISPLAY_NAME} 登录验证码'
    text_body = (
        f'您的登录验证码为：{code}，10 分钟内有效。\n'
        '如非本人操作请忽略此邮件。'
    )
    html_body = f"""<!DOCTYPE html><html><body style="font-family:sans-serif;font-size:14px;">
<p>您的登录验证码为：<b style="font-size:20px;letter-spacing:2px;">{code}</b>（10 分钟内有效）</p>
<p style="color:#86909c;font-size:12px;">如非本人操作请忽略。</p>
</body></html>"""
    return subject, text_body, html_body


def build_admin_confirm_code_email(
    *,
    purpose: str,
    code: str,
    operator_name: str,
) -> tuple[str, str, str]:
    action_label = '删除审批单'
    if purpose == 'delete_workflow_instance':
        action_label = '删除审批单'
    subject = f'{APP_DISPLAY_NAME} {action_label}确认验证码'
    greet = f'{operator_name}，您好：' if operator_name else '您好：'
    text_body = (
        f'{greet}\n\n'
        f'您正在执行「{action_label}」操作。验证码为：{code}，10 分钟内有效。\n'
        '如非本人操作请忽略此邮件。'
    )
    html_body = f"""<!DOCTYPE html><html><body style="font-family:sans-serif;font-size:14px;">
<p>{escape(greet)}</p>
<p>您正在执行<b>「{escape(action_label)}」</b>操作。</p>
<p>验证码为：<b style="font-size:20px;letter-spacing:2px;">{escape(code)}</b>（10 分钟内有效）</p>
<p style="color:#86909c;font-size:12px;">如非本人操作请忽略此邮件。</p>
</body></html>"""
    return subject, text_body, html_body


def build_test_email() -> tuple[str, str, str]:
    subject = f'{APP_DISPLAY_NAME} 邮件测试'
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    text_body = f'这是一封测试邮件，说明 SMTP 配置可用。\n\n发送时间：{now}'
    html_body = f"""<!DOCTYPE html><html><body style="font-family:sans-serif;font-size:14px;">
<p>这是一封<strong>测试邮件</strong>，说明 SMTP 配置可用。</p>
<p style="color:#86909c;">发送时间：{now}</p>
</body></html>"""
    return subject, text_body, html_body
