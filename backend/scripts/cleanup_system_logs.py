# -*- coding: utf-8 -*-
"""清理系统运行日志（登录/访问、邮件通知、过期邮件审批令牌）。"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from app.extensions import db
from app.models import LoginAccessLog, NotificationLog, TaskEmailToken


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='清理 IMC Workflow 系统运行日志')
    parser.add_argument(
        '--mode',
        choices=('all', 'days'),
        required=True,
        help='all=全量清理；days=按天数清理更早记录',
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='mode=days 时保留最近 N 天（默认 30）',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == 'days' and args.days < 1:
        print('错误：--days 必须大于 0')
        return 1

    app = create_app()
    with app.app_context():
        now = datetime.now()
        login_q = LoginAccessLog.query
        notify_q = NotificationLog.query
        token_q = TaskEmailToken.query.filter(TaskEmailToken.expires_at < now)

        if args.mode == 'days':
            cutoff = now - timedelta(days=args.days)
            login_q = login_q.filter(LoginAccessLog.created_at < cutoff)
            notify_q = notify_q.filter(NotificationLog.created_at < cutoff)
            scope = f'{args.days} 天前（早于 {cutoff.strftime("%Y-%m-%d %H:%M:%S")}）'
        else:
            scope = '全部'

        login_n = login_q.delete(synchronize_session=False)
        notify_n = notify_q.delete(synchronize_session=False)
        token_n = token_q.delete(synchronize_session=False)
        db.session.commit()

        print(f'清理范围：{scope}')
        print(f'  登录/访问日志：{login_n} 条')
        print(f'  邮件通知日志：{notify_n} 条')
        print(f'  过期邮件审批令牌：{token_n} 条')
        print('说明：审批环节记录（instance_timelines）属于审批单历史，本脚本不会清理。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
