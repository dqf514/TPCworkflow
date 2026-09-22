# -*- coding: utf-8 -*-
"""流程条件比较用的标量归一化。"""
from __future__ import annotations

from typing import Any


def _money_scalar(val: dict) -> float | None:
    for key in ('rmb_amount', 'amount'):
        raw = val.get(key)
        if raw in (None, ''):
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def normalize_condition_scalar(val: Any) -> Any:
    """将表单值/条件期望值统一为可比较标量。"""
    if val is None or val == '':
        return val
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return val
    if isinstance(val, dict):
        if 'amount' in val or 'rmb_amount' in val or 'currency' in val:
            return _money_scalar(val)
        return val
    if isinstance(val, list):
        return [normalize_condition_scalar(x) for x in val]
    if isinstance(val, str):
        s = val.strip()
        if s.lower() == 'true':
            return True
        if s.lower() == 'false':
            return False
        if s in ('1', '0'):
            return s == '1'
        if s != '' and _is_numeric_string(s):
            try:
                return float(s) if '.' in s else int(s)
            except ValueError:
                pass
        return s
    return val


def _is_numeric_string(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def condition_values_equal(actual: Any, expected: Any) -> bool:
    a = normalize_condition_scalar(actual)
    b = normalize_condition_scalar(expected)
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) is bool(b)
    return a == b


def condition_values_not_equal(actual: Any, expected: Any) -> bool:
    return not condition_values_equal(actual, expected)
