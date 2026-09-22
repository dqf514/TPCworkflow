# -*- coding: utf-8 -*-
"""对比前端 t() 键、种子词典与数据库，输出缺失项。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import I18nMessage
from scripts.i18n_bundle_loader import collect_all_extra
from scripts.seed_i18n_en_us import SEED_MESSAGES_EN
from scripts.seed_i18n_zh_cn import SEED_MESSAGES

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / 'frontend' / 'src'
BUNDLES = FRONTEND / 'i18n' / 'bundles'

T_PATTERN = re.compile(r"""t\(\s*['"]([a-zA-Z][a-zA-Z0-9_]*\.[^'"]+)['"]""")
BUNDLE_PATTERN = re.compile(r"""'((?:designer|flowRole|org|flowDesign|finance|settings|wfSettings|studio)\.[^']+)'""")


def collect_frontend_keys() -> set[str]:
    used: set[str] = set()
    for p in FRONTEND.rglob('*'):
        if p.suffix not in ('.vue', '.ts', '.tsx'):
            continue
        try:
            text = p.read_text(encoding='utf-8')
        except OSError:
            continue
        used.update(T_PATTERN.findall(text))
    return used


def collect_bundle_fallback() -> set[str]:
    keys: set[str] = set()
    for p in BUNDLES.glob('*.ts'):
        try:
            text = p.read_text(encoding='utf-8')
        except OSError:
            continue
        keys.update(BUNDLE_PATTERN.findall(text))
    return keys


def main() -> None:
    existing = {(ns, k) for ns, k, _ in SEED_MESSAGES}
    extra_zh, extra_en = collect_all_extra(existing)
    seed_zh = {f'{ns}.{k}': v for ns, k, v in SEED_MESSAGES + extra_zh}
    seed_en = {f'{ns}.{k}': v for ns, k, v in SEED_MESSAGES_EN + extra_en}
    used = collect_frontend_keys()
    fallback = collect_bundle_fallback()

    missing_seed = sorted(k for k in used if k not in seed_zh)
    in_fallback_not_seed = sorted(k for k in fallback if k not in seed_zh)

    app = create_app()
    with app.app_context():
        missing_db_zh: list[str] = []
        missing_db_en: list[str] = []
        for key in sorted(seed_zh):
            ns, msg_key = key.split('.', 1)
            if not I18nMessage.query.filter_by(namespace=ns, msg_key=msg_key, locale='zh-CN').first():
                missing_db_zh.append(key)
            if not I18nMessage.query.filter_by(namespace=ns, msg_key=msg_key, locale='en-US').first():
                missing_db_en.append(key)

    print('=== 前端使用但种子未收录 ===')
    for k in missing_seed:
        tag = ' [仅本地兜底]' if k in fallback else ''
        print(f'  {k}{tag}')
    print(f'共 {len(missing_seed)} 条\n')

    print('=== 本地兜底 bundle 有但种子未收录 ===')
    for k in in_fallback_not_seed:
        print(f'  {k}')
    print(f'共 {len(in_fallback_not_seed)} 条\n')

    print('=== 种子有但数据库缺失 (zh-CN) ===')
    for k in missing_db_zh:
        print(f'  {k}')
    print(f'共 {len(missing_db_zh)} 条\n')

    print('=== 种子有但数据库缺失 (en-US) ===')
    for k in missing_db_en:
        print(f'  {k}')
    print(f'共 {len(missing_db_en)} 条')


if __name__ == '__main__':
    main()
