# -*- coding: utf-8 -*-
import json
import operator


def parse_graph(raw: str | None) -> dict:
    if not raw:
        return {'nodes': [], 'edges': []}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {'nodes': [], 'edges': []}
    if 'nodes' not in data:
        return {'nodes': data if isinstance(data, list) else [], 'edges': []}
    return data


def find_node(graph: dict, node_id: str) -> dict | None:
    for node in graph.get('nodes') or []:
        if node.get('id') == node_id:
            return node
    return None


_NODE_TYPE_LABELS = {
    'start': '开始',
    'approver': '审批',
    'handler': '办理',
    'cc': '抄送',
    'condition': '条件分支',
    'end': '结束',
}


def resolve_node_display_name(node: dict | None, node_id: str | None = None) -> str:
    """流程节点展示名：优先设计器 config.title，其次 text/name，再按类型兜底。"""
    nid = (node_id or (node or {}).get('id') or '').strip()
    if not node:
        return nid
    config = node.get('config') or {}
    title = (config.get('title') or node.get('text') or node.get('name') or '').strip()
    if title:
        return title
    return _NODE_TYPE_LABELS.get(node.get('type'), nid)


def parse_settings(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def parse_variables(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def get_outgoing_targets(graph: dict, node_id: str) -> list[str]:
    targets = []
    for edge in graph.get('edges') or []:
        if edge.get('source') == node_id and edge.get('target'):
            targets.append(edge['target'])
    node = find_node(graph, node_id)
    if node and not targets:
        nxt = node.get('next')
        if isinstance(nxt, list):
            targets.extend([x for x in nxt if x])
    return targets


def resolve_next_node_ids(graph: dict, node_id: str, variables: dict) -> list[str]:
    node = find_node(graph, node_id)
    if not node:
        return []
    ntype = node.get('type')
    if ntype == 'condition':
        branches = sorted(
            node.get('branches') or [],
            key=lambda b: b.get('priority') if b.get('priority') is not None else 99,
        )
        for branch in branches:
            if eval_condition(branch.get('expr'), variables):
                t = branch.get('target')
                return [t] if t else []
        return get_outgoing_targets(graph, node_id)
    edges = [e for e in graph.get('edges') or [] if e.get('source') == node_id]
    if edges:
        matched = []
        default_target = None
        for edge in edges:
            cond = edge.get('condition')
            if cond is None and edge.get('default'):
                default_target = edge.get('target')
                continue
            if cond is None and not edge.get('condition_expr'):
                default_target = default_target or edge.get('target')
                continue
            expr = edge.get('condition_expr') or cond
            if eval_condition(expr, variables):
                matched.append(edge.get('target'))
        if matched:
            return [x for x in matched if x]
        if default_target:
            return [default_target]
        return [e.get('target') for e in edges if e.get('target')]
    return get_outgoing_targets(graph, node_id)


_OPS = {
    'eq': operator.eq,
    'ne': operator.ne,
    'gt': operator.gt,
    'gte': operator.ge,
    'lt': operator.lt,
    'lte': operator.le,
}


def eval_condition(expr, variables: dict) -> bool:
    from app.services.condition_value import (
        condition_values_equal,
        condition_values_not_equal,
        normalize_condition_scalar,
    )

    if expr is None or expr == '' or expr is True or expr == 'default':
        return True
    if isinstance(expr, bool):
        return expr
    if isinstance(expr, str):
        if expr.strip() == 'default':
            return True
        if expr.strip() == 'true':
            return True
        if expr.strip() == 'false':
            return False
    if isinstance(expr, dict):
        if expr.get('default'):
            return True
        field = expr.get('field') or expr.get('key')
        op = expr.get('op', 'eq')
        expected = expr.get('value')
        if field:
            actual = normalize_condition_scalar(_get_var(variables, field))
            expected_norm = normalize_condition_scalar(expected)
            try:
                if op in ('gt', 'gte', 'lt', 'lte'):
                    return _OPS[op](float(actual), float(expected_norm))
            except (TypeError, ValueError):
                return False
            if op == 'ne':
                return condition_values_not_equal(actual, expected_norm)
            return condition_values_equal(actual, expected_norm)
    return bool(expr)


def _get_var(variables: dict, field: str):
    if not field:
        return None
    if field in variables:
        return variables[field]
    form = variables.get('form') if isinstance(variables.get('form'), dict) else {}
    if field in form:
        return form[field]
    if field.startswith('form.'):
        return form.get(field[5:])
    if field.startswith('org.'):
        org = variables.get('org') or {}
        return org.get(field[4:])
    parts = field.split('.')
    cur = variables
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    if cur is not None:
        return cur
    return form.get(field)
