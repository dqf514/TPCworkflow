# -*- coding: utf-8 -*-
"""应用启动时的可选维护任务（默认跳过，避免每次 restart 长时间阻塞）。"""
from __future__ import annotations

import os
import time

from flask import Flask

from app.extensions import db


def _env_truthy(name: str, default: str = '0') -> bool:
    return os.environ.get(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


def should_run_startup_maintenance() -> bool:
    """默认快速启动；仅显式开启或开发调试时跑迁移/种子。"""
    if _env_truthy('TPC_SKIP_STARTUP_MAINTENANCE'):
        return False
    if _env_truthy('TPC_RUN_STARTUP_MAINTENANCE'):
        return True
    # 仅本地开发（FLASK_DEBUG=1）自动维护；生产请保持 FLASK_DEBUG=0
    return _env_truthy('FLASK_DEBUG', '0')


def ensure_db_tables(app: Flask) -> None:
    """已有库时跳过 create_all，缩短 worker 冷启动时间。"""
    from sqlalchemy import inspect

    with app.app_context():
        insp = inspect(db.engine)
        if insp.get_table_names():
            return
        db.create_all()


def run_startup_maintenance(app: Flask) -> None:
    if not should_run_startup_maintenance():
        app.logger.info(
            '已跳过启动维护（快速启动）。升级后请执行: python scripts/upgrade_db.py '
            '或设置 TPC_RUN_STARTUP_MAINTENANCE=1 后重启',
        )
        return

    from scripts.bootstrap import ensure_bootstrap
    from scripts.upgrade_db import _ensure_columns, _migrate_department_unique_constraint

    t0 = time.perf_counter()
    with app.app_context():
        db.create_all()
        _ensure_columns()
        _migrate_department_unique_constraint()
        ensure_bootstrap()
    app.logger.info('启动维护完成，耗时 %.1fs', time.perf_counter() - t0)
