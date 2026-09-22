# -*- coding: utf-8 -*-
"""流程实例对外编号：YYYY-MM-DD-0001（按自然日递增）。"""
from __future__ import annotations

from datetime import datetime

from app.models import WorkflowInstance


def allocate_workflow_display_no() -> str:
    today = datetime.now().strftime('%Y-%m-%d')
    prefix = f'{today}-'
    last_row = (
        WorkflowInstance.query.filter(WorkflowInstance.display_no.like(f'{prefix}%'))
        .order_by(WorkflowInstance.display_no.desc())
        .first()
    )
    seq = 1
    if last_row and last_row.display_no:
        try:
            seq = int(str(last_row.display_no).rsplit('-', 1)[-1]) + 1
        except ValueError:
            seq = 1
    return f'{prefix}{seq:04d}'
