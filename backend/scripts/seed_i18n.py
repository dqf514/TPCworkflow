# -*- coding: utf-8 -*-
"""写入/更新 zh-CN 与 en-US 词典种子。

默认仅：补全缺失键、填充空译文，不覆盖已在后台修改过的词条。
开发需用种子强制覆盖时：I18N_FORCE_SEED_SYNC=1 python scripts/seed_i18n.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extensions import db
from app.models import I18nMessage
from app.services.i18n import bump_bundle_version
from scripts.i18n_bundle_loader import collect_all_extra
from scripts.seed_i18n_en_us import SEED_MESSAGES_EN
from scripts.seed_i18n_zh_cn import SEED_MESSAGES


def _force_seed_sync() -> bool:
    return os.environ.get('I18N_FORCE_SEED_SYNC', '').strip().lower() in ('1', 'true', 'yes', 'on')


def _merged_seed_messages() -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    existing = {(ns, k) for ns, k, _ in SEED_MESSAGES}
    extra_zh, extra_en = collect_all_extra(existing)
    return SEED_MESSAGES + extra_zh, SEED_MESSAGES_EN + extra_en


def seed_all_locales(*, force_sync: bool | None = None) -> int:
    force = _force_seed_sync() if force_sync is None else force_sync
    added = 0
    zh_messages, en_messages = _merged_seed_messages()
    for locale, items in (('zh-CN', zh_messages), ('en-US', en_messages)):
        for namespace, msg_key, msg_value in items:
            row = I18nMessage.query.filter_by(
                namespace=namespace,
                msg_key=msg_key,
                locale=locale,
            ).first()
            if row:
                if force and row.msg_value != msg_value:
                    row.msg_value = msg_value
                    added += 1
                elif not (row.msg_value or '').strip():
                    row.msg_value = msg_value
                    added += 1
            else:
                db.session.add(
                    I18nMessage(
                        namespace=namespace,
                        msg_key=msg_key,
                        locale=locale,
                        msg_value=msg_value,
                    ),
                )
                added += 1
    db.session.commit()
    if added:
        bump_bundle_version()
    return added


if __name__ == '__main__':
    from app import create_app

    app = create_app()
    with app.app_context():
        n = seed_all_locales()
        mode = '强制同步' if _force_seed_sync() else '仅补缺/空值'
        print(f'词典种子完成（{mode}），变更 {n} 条')
