# -*- coding: utf-8 -*-
"""将内置模板写入数据库（已存在的 key 不会覆盖 schema，仅补缺发布状态）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.extensions import db
from app.models import FormDefinition
from app.services.form_templates.registry import BUILTIN_FORM_TEMPLATES, list_builtin_templates
from scripts.bootstrap import _ensure_builtin_published_templates


def main() -> None:
    app = create_app()
    with app.app_context():
        before = {r.key for r in FormDefinition.query.all()}
        _ensure_builtin_published_templates()
        after = FormDefinition.query.filter(
            FormDefinition.key.in_(list(BUILTIN_FORM_TEMPLATES.keys())),
        ).all()
        created = [f for f in after if f.key not in before]
        print(f'内置模板共 {len(list_builtin_templates())} 个：')
        for meta in list_builtin_templates():
            print(f'  - {meta["key"]}: {meta["name"]}')
        if created:
            print(f'\n本次新建 {len(created)} 个已发布表单：')
            for f in created:
                print(f'  + {f.key} ({f.name})')
        else:
            print('\n无新建（均已存在，未覆盖已有 schema）。')


if __name__ == '__main__':
    main()
