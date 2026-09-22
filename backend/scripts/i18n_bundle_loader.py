# -*- coding: utf-8 -*-
"""从前端 i18n bundle 文件解析词条，供种子脚本合并。"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE_DIR = ROOT / 'frontend' / 'src' / 'i18n' / 'bundles'

# 'namespace.key': 'value' 或跨行字符串（简化：仅匹配单行值）
_ENTRY = re.compile(
    r"'((?:[a-zA-Z][a-zA-Z0-9_]*)\.([a-zA-Z0-9_.]+))'\s*:\s*"
    r"(?:'((?:\\'|[^'])*)'|\"((?:\\\"|[^\"])*)\")",
    re.MULTILINE,
)


def parse_ts_record(path: Path) -> dict[str, str]:
    text = path.read_text(encoding='utf-8')
    out: dict[str, str] = {}
    for m in _ENTRY.finditer(text):
        full_key = m.group(1)
        val = m.group(3) if m.group(3) is not None else m.group(4)
        val = val.replace("\\'", "'").replace('\\"', '"')
        out[full_key] = val
    return out


def to_seed_tuples(flat: dict[str, str]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for full_key in sorted(flat):
        ns, msg_key = full_key.split('.', 1)
        rows.append((ns, msg_key, flat[full_key]))
    return rows


def load_bundle_pair(filename: str, zh_export: str, en_export: str) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    path = BUNDLE_DIR / filename
    text = path.read_text(encoding='utf-8')
    zh_block = _extract_export_block(text, zh_export)
    en_block = _extract_export_block(text, en_export)
    zh = _parse_block(zh_block)
    en = _parse_block(en_block)
    return to_seed_tuples(zh), to_seed_tuples(en)


def _extract_export_block(text: str, export_name: str) -> str:
    marker = f'export const {export_name}'
    start = text.find(marker)
    if start < 0:
        return ''
    brace = text.find('{', start)
    if brace < 0:
        return ''
    depth = 0
    for i in range(brace, len(text)):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[brace : i + 1]
    return ''


def _parse_block(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not block:
        return out
    for m in _ENTRY.finditer(block):
        out[m.group(1)] = (m.group(3) if m.group(3) is not None else m.group(4)).replace("\\'", "'")
    return out


def bundle_designer() -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    return load_bundle_pair('designer.ts', 'designerZh', 'designerEn')


def bundle_admin_logs() -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    return load_bundle_pair('adminLogs.ts', 'adminLogsZh', 'adminLogsEn')


def bundle_menu_nav() -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    return load_bundle_pair('menuNav.ts', 'menuNavZh', 'menuNavEn')


def bundle_workflow_apply_extra() -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    zh_all, en_all = load_bundle_pair('workflowApply.ts', 'workflowApplyZh', 'workflowApplyEn')
    zh = [r for r in zh_all if r[0] == 'unsaved']
    en = [r for r in en_all if r[0] == 'unsaved']
    return zh, en


def bundle_settings_extra(existing_zh: set[tuple[str, str]]) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    path = BUNDLE_DIR / 'settings.ts'
    text = path.read_text(encoding='utf-8')
    zh = _parse_block(_extract_export_block(text, 'settingsZh'))
    en = _parse_block(_extract_export_block(text, 'settingsEn'))
    zh_rows = [to_seed_tuples({k: v for k, v in zh.items() if (k.split('.', 1)[0], k.split('.', 1)[1]) not in existing_zh})][0]
    en_rows = []
    for ns, msg_key, _ in zh_rows:
        full = f'{ns}.{msg_key}'
        if full in en:
            en_rows.append((ns, msg_key, en[full]))
        elif (ns, msg_key) in {(r[0], r[1]) for r in en_rows}:
            continue
        else:
            en_rows.append((ns, msg_key, en.get(full, msg_key)))
    # rebuild en properly
    en_rows = []
    for ns, msg_key, _ in zh_rows:
        full = f'{ns}.{msg_key}'
        en_rows.append((ns, msg_key, en.get(full, msg_key)))
    return zh_rows, en_rows


def bundle_studio_extra(existing_zh: set[tuple[str, str]]) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    extra_keys = {
        'studio.col_sector': ('业务板块', 'Business sector'),
        'studio.sector_unset': ('未设置', 'Not set'),
        'studio.sector_saved': ('板块已更新', 'Sector updated'),
        'studio.sector_save_failed': ('板块保存失败', 'Failed to save sector'),
        'studio.status_archived': ('已归档', 'Archived'),
        'studio.create_builtin': ('从内置模板创建', 'Built-in template'),
        'studio.pick_builtin': ('内置模板', 'Built-in template'),
        'studio.pick_builtin_template': ('请选择内置模板', 'Select a built-in template'),
        'studio.builtin_ph': ('选择系统内置表单模板', 'Select built-in form template'),
        'studio.builtin_hint': ('内置模板含示例字段与审批流程，保存前请修改表单标识', 'Includes sample fields and flow; change the form key before saving'),
        'studio.builtin_alert': ('将加载内置模板，可在设计页按需调整后保存发布', 'Loads a built-in template; adjust in the designer before publishing'),
        'studio.builtin_loaded_ok': ('已加载内置模板', 'Built-in template loaded'),
        'studio.unpublish': ('取消发布', 'Unpublish'),
        'studio.unpublish_confirm': ('取消发布后用户将无法发起新申请，确定继续？', 'Users cannot start new requests until republished. Continue?'),
        'studio.unpublish_failed': ('取消发布失败', 'Unpublish failed'),
        'studio.unpublished_ok': ('已取消发布', 'Unpublished'),
        'studio.last_published': ('上次发布', 'Last published'),
    }
    zh_rows = []
    en_rows = []
    for full, (zh_val, en_val) in extra_keys.items():
        ns, msg_key = full.split('.', 1)
        if (ns, msg_key) in existing_zh:
            continue
        zh_rows.append((ns, msg_key, zh_val))
        en_rows.append((ns, msg_key, en_val))
    return zh_rows, en_rows


def collect_all_extra(existing_zh: set[tuple[str, str]]) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    zh: list[tuple[str, str, str]] = []
    en: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    def merge(z_rows, e_rows):
        nonlocal seen
        for z, e in zip(z_rows, e_rows):
            key = (z[0], z[1])
            if key in seen or key in existing_zh:
                continue
            seen.add(key)
            zh.append(z)
            en.append(e)

    dzh, den = bundle_designer()
    merge(dzh, den)
    mzh, men = bundle_menu_nav()
    merge(mzh, men)
    alzh, alen = bundle_admin_logs()
    merge(alzh, alen)
    uzh, uen = bundle_workflow_apply_extra()
    merge(uzh, uen)
    szh, sen = bundle_settings_extra(existing_zh | seen)
    merge(szh, sen)
    stzh, sten = bundle_studio_extra(existing_zh | seen)
    merge(stzh, sten)
    return zh, en
