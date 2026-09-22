# -*- coding: utf-8 -*-
"""从 seed_i18n_studio_org 导出前端 studio / flowDesign / wfSettings 兜底词条。"""
from pathlib import Path

from scripts.seed_i18n_studio_org import STUDIO_ORG_EN, STUDIO_ORG_ZH

NAMESPACES = frozenset({'wfSettings', 'studio', 'flowDesign'})
OUT = Path(__file__).resolve().parents[2] / 'frontend' / 'src' / 'i18n' / 'bundles' / 'studioOrg.ts'


def _escape(val: str) -> str:
    return val.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')


def _emit(items, var_name: str) -> str:
    lines = [f'export const {var_name}: Record<string, string> = {{']
    for ns, key, val in items:
        if ns not in NAMESPACES:
            continue
        lines.append(f"  '{ns}.{key}': '{_escape(val)}',")
    lines.append('}')
    return '\n'.join(lines)


def main() -> None:
    body = (
        '// 与 backend/scripts/seed_i18n_studio_org.py 同步（本地兜底；运行本脚本可重新生成）\n'
        + _emit(STUDIO_ORG_ZH, 'studioOrgZh')
        + '\n\n'
        + _emit(STUDIO_ORG_EN, 'studioOrgEn')
        + '\n'
    )
    OUT.write_text(body, encoding='utf-8')
    n = sum(1 for x in STUDIO_ORG_ZH if x[0] in NAMESPACES)
    print(f'wrote {OUT} ({n} zh keys per locale block)')


if __name__ == '__main__':
    main()
