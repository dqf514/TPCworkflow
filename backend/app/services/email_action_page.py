# -*- coding: utf-8 -*-
"""邮件快速审批确认页（HTML）。"""
from __future__ import annotations

from html import escape

from app.models import TaskInstance, User
from app.utils.branding import APP_DISPLAY_NAME


def render_email_action_error(message: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"/></head>
<body style="font-family:PingFang SC,Microsoft YaHei,sans-serif;max-width:520px;margin:48px auto;padding:0 16px;">
<h2>{escape(APP_DISPLAY_NAME)}</h2>
<p style="color:#F53F3F;">{escape(message)}</p>
<p style="color:#86909c;font-size:13px;">请登录系统，在「待办」中处理该任务。</p>
</body></html>"""

from app.services.email_content import build_form_summary_lines
from app.services.graph_utils import find_node, parse_graph, resolve_node_display_name


def render_email_action_page(
    *,
    task: TaskInstance,
    action: str,
    token: str,
    error: str | None = None,
    success: str | None = None,
) -> str:
    inst = task.instance
    definition = inst.definition
    flow_name = definition.name if definition else '审批流程'
    graph = parse_graph(definition.process_graph if definition else None)
    node = find_node(graph, task.node_id) or {}
    node_label = resolve_node_display_name(node, task.node_id)
    initiator = User.query.get(inst.initiator_id)
    initiator_name = initiator.display_label() if initiator else '—'
    display_no = (inst.display_no or '').strip() or f'#{inst.id}'
    summary = build_form_summary_lines(inst, max_lines=8)
    summary_html = '<br/>'.join(escape(line) for line in summary) if summary else '（无）'

    action_label = '同意' if action == 'approve' else '驳回'
    action_color = '#00B42A' if action == 'approve' else '#F53F3F'

    err_block = f'<p style="color:#F53F3F;">{escape(error)}</p>' if error else ''
    ok_block = f'<p style="color:#00B42A;font-size:16px;"><b>{escape(success)}</b></p>' if success else ''

    form_block = ''
    if not success and not error:
        form_block = f"""
<form method="post" style="margin-top:20px;">
  <input type="hidden" name="token" value="{escape(token)}" />
  <input type="hidden" name="confirm" value="yes" />
  <p>确认要<b style="color:{action_color}">「{action_label}」</b>该申请吗？</p>
  <button type="submit" style="background:{action_color};color:#fff;border:none;padding:12px 28px;border-radius:6px;font-size:15px;cursor:pointer;margin-right:12px;">确认{action_label}</button>
  <a href="javascript:window.close()" style="color:#86909c;">关闭窗口</a>
</form>"""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>邮件审批 - {escape(action_label)}</title></head>
<body style="font-family:PingFang SC,Microsoft YaHei,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;color:#1d2129;">
<h2 style="margin:0 0 8px;">{escape(APP_DISPLAY_NAME)} · 邮件{escape(action_label)}</h2>
{ok_block}{err_block}
<p><b>{escape(flow_name)}</b>（{escape(display_no)}）</p>
<table style="width:100%;background:#f7f8fa;border-radius:8px;margin:12px 0;">
<tr><td style="padding:8px 12px;color:#86909c;width:88px;">环节</td><td style="padding:8px 12px;">{escape(node_label)}</td></tr>
<tr><td style="padding:8px 12px;color:#86909c;">申请人</td><td style="padding:8px 12px;">{escape(initiator_name)}</td></tr>
</table>
<p><b>内容摘要</b></p>
<p style="line-height:1.7;">{summary_html}</p>
{form_block}
<p style="color:#86909c;font-size:12px;margin-top:32px;">如需查看完整表单或填写审批意见，请登录系统打开待办。</p>
</body></html>"""
