# -*- coding: utf-8 -*-
"""表单控件联动与条件显示。"""
from __future__ import annotations

LINKAGE_SOURCE_TYPES = frozenset({
    'select', 'radio', 'switch', 'multi_select', 'checkbox_group',
})


def _normalize_option_value(raw) -> str:
    if raw is True or raw == 'true' or raw == 1 or raw == '1':
        return '1'
    if raw is False or raw == 'false' or raw == 0 or raw == '0':
        return '0'
    if raw is None:
        return ''
    return str(raw)


def _selected_values(raw, source_type: str) -> list[str]:
    if source_type == 'switch':
        return [_normalize_option_value(raw)]
    if isinstance(raw, list):
        return [v for v in (_normalize_option_value(x) for x in raw) if v]
    one = _normalize_option_value(raw)
    return [one] if one else []


def _get_linkage(field: dict) -> dict | None:
    props = field.get('props') or {}
    linkage = props.get('linkage')
    if not isinstance(linkage, dict):
        return None
    rules = linkage.get('rules') or []
    return linkage if rules else None


def _get_show_when(obj: dict):
    return obj.get('showWhen')


def _rule_matches(rule: dict, selected: list[str], source_type: str) -> bool:
    target = _normalize_option_value(rule.get('optionValue'))
    if not target or not selected:
        return False
    if source_type in ('multi_select', 'checkbox_group'):
        return target in selected
    return selected[0] == target


def _build_linkage_index(schema: dict) -> tuple[dict[str, list], dict[str, list], dict[str, dict]]:
    field_targets: dict[str, list] = {}
    section_targets: dict[str, list] = {}
    field_by_key: dict[str, dict] = {}
    for sec in schema.get('sections') or []:
        for field in sec.get('fields') or []:
            key = field.get('key')
            if key:
                field_by_key[key] = field
            linkage = _get_linkage(field)
            if not linkage:
                continue
            for rule in linkage.get('rules') or []:
                for fid in rule.get('showFieldIds') or []:
                    field_targets.setdefault(str(fid), []).append(rule)
                for sid in rule.get('showSectionIds') or []:
                    section_targets.setdefault(str(sid), []).append(rule)
    return field_targets, section_targets, field_by_key


def _evaluate_show_when(obj: dict, data: dict, field_by_key: dict[str, dict]) -> bool:
    show_when = _get_show_when(obj)
    if not show_when:
        return True
    rules = show_when if isinstance(show_when, list) else [show_when]
    logic = obj.get('showWhenLogic') or 'or'
    results = []
    for rule in rules:
        source = field_by_key.get(rule.get('fieldKey') or '')
        if not source:
            results.append(False)
            continue
        key = source.get('key')
        selected = _selected_values(data.get(key), source.get('type') or '')
        want = [
            _normalize_option_value(v)
            for v in (rule.get('values') or [])
            if _normalize_option_value(v)
        ]
        if not want:
            results.append(True)
            continue
        match = rule.get('match') or 'any'
        if match == 'all':
            results.append(all(w in selected for w in want))
        else:
            results.append(any(w in selected for w in want))
    if logic == 'and':
        return all(results)
    return any(results)


def _evaluate_linkage_target(
    target_rules: list,
    schema: dict,
    data: dict,
) -> bool:
    if not target_rules:
        return True
    for sec in schema.get('sections') or []:
        for source in sec.get('fields') or []:
            linkage = _get_linkage(source)
            if not linkage or not source.get('key'):
                continue
            selected = _selected_values(data.get(source['key']), source.get('type') or '')
            for rule in linkage.get('rules') or []:
                if rule not in target_rules:
                    continue
                if _rule_matches(rule, selected, source.get('type') or ''):
                    return True
    return False


def field_is_visible(field: dict, schema: dict, data: dict, index=None) -> bool:
    if field.get('visible') is False:
        return False
    if index is None:
        index = _build_linkage_index(schema)
    field_targets, section_targets, field_by_key = index
    if not _evaluate_show_when(field, data, field_by_key):
        return False
    fid = str(field.get('id') or '')
    rules = field_targets.get(fid) or []
    if rules and not _evaluate_linkage_target(rules, schema, data):
        return False
    return True


def section_is_visible(section: dict, schema: dict, data: dict, index=None) -> bool:
    if index is None:
        index = _build_linkage_index(schema)
    field_targets, section_targets, field_by_key = index
    if not _evaluate_show_when(section, data, field_by_key):
        return False
    sid = str(section.get('id') or '')
    rules = section_targets.get(sid) or []
    if rules and not _evaluate_linkage_target(rules, schema, data):
        return False
    return True
