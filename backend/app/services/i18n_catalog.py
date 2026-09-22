# -*- coding: utf-8 -*-
"""从种子汇总全部 namespace + msg_key，供词典管理对照与补全。"""
from __future__ import annotations

from scripts.seed_i18n_en_us import SEED_MESSAGES_EN
from scripts.seed_i18n_zh_cn import SEED_MESSAGES


def build_seed_catalog() -> dict[tuple[str, str], dict[str, str]]:
    """(namespace, msg_key) -> zh_seed / en_seed 参考译文。"""
    catalog: dict[tuple[str, str], dict[str, str]] = {}
    for namespace, msg_key, msg_value in SEED_MESSAGES:
        ns, key = namespace.strip(), msg_key.strip()
        if not ns or not key:
            continue
        entry = catalog.setdefault((ns, key), {'zh_seed': '', 'en_seed': ''})
        entry['zh_seed'] = msg_value or ''
    for namespace, msg_key, msg_value in SEED_MESSAGES_EN:
        ns, key = namespace.strip(), msg_key.strip()
        if not ns or not key:
            continue
        entry = catalog.setdefault((ns, key), {'zh_seed': '', 'en_seed': ''})
        entry['en_seed'] = msg_value or ''
    return catalog


def list_catalog_entries(
    namespace: str | None = None,
    q: str | None = None,
) -> list[dict]:
    catalog = build_seed_catalog()
    ql = (q or '').strip().lower()
    items: list[dict] = []
    for (ns, key), refs in sorted(catalog.items(), key=lambda x: (x[0][0], x[0][1])):
        if namespace and ns != namespace:
            continue
        if ql:
            hay = ' '.join([ns, key, refs['zh_seed'], refs['en_seed']]).lower()
            if ql not in hay:
                continue
        items.append({
            'namespace': ns,
            'msg_key': key,
            'zh_seed': refs['zh_seed'],
            'en_seed': refs['en_seed'],
        })
    return items
