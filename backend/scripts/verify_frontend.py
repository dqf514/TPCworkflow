"""Playwright 回归校验：路由渲染、控制台错误、占位文案、横向溢出、主色。"""
import json
import re
import sys

from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5321'
COOKIE = sys.argv[1] if len(sys.argv) > 1 else ''

ROUTES = [
    ('/', '首页'),
    ('/instances', '我发起的'),
    ('/tasks', '待办'),
    ('/apply', '发起申请'),
    ('/leave-calendar', '日历'),
    ('/admin/org', '组织架构'),
    ('/admin/form-studio', '表单设计'),
    ('/admin/workflows', '流程管理'),
    ('/admin/users', '用户管理'),
    ('/admin/flow-roles', '流程角色'),
    ('/admin/sector-monitor', '板块监控'),
    ('/admin/finance-export', '财务导出'),
    ('/admin/i18n', '国际化'),
    ('/admin/settings', '系统设置'),
    ('/admin/logs', '审计日志'),
]

BAD_TEXT = re.compile(r'No Data|undefined|NaN|PARTICULARS|\[object Object\]')
VIEWPORTS = [(375, 812), (900, 900), (1280, 900)]

problems = []


def check_route(page, path, name, errors):
    page.goto(BASE + path, wait_until='networkidle')
    page.wait_for_timeout(600)
    body = page.inner_text('body')
    if BAD_TEXT.search(body):
        problems.append(f'{name} ({path}) 出现占位/异常文案: '
                        f'{BAD_TEXT.search(body).group(0)!r}')
    overflow = page.evaluate(
        '() => document.documentElement.scrollWidth - document.documentElement.clientWidth')
    if overflow > 2:
        problems.append(f'{name} ({path}) 横向溢出 {overflow}px')
    if not body.strip():
        problems.append(f'{name} ({path}) 页面为空')


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={'width': 1280, 'height': 900})
    ctx.add_cookies([{'name': 'session', 'value': COOKIE, 'url': BASE}])
    page = ctx.new_page()

    errors = []
    page.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type == 'error' else None)
    page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))

    for path, name in ROUTES:
        errors.clear()
        try:
            check_route(page, path, name, errors)
        except Exception as exc:  # noqa: BLE001
            problems.append(f'{name} ({path}) 加载异常: {exc}')
        real = [e for e in errors if 'favicon' not in e and 'Failed to load resource' not in e]
        if real:
            problems.append(f'{name} ({path}) 控制台错误: {real[:3]}')

    # 主色：Arco --primary-6 应为品牌紫 80,52,255
    page.goto(BASE + '/', wait_until='networkidle')
    primary = page.evaluate(
        "() => getComputedStyle(document.body).getPropertyValue('--primary-6').trim()")
    if primary != '80, 52, 255':
        problems.append(f'--primary-6 = {primary!r}，期望 "80, 52, 255"')

    # 各断点横向溢出
    for w, h in VIEWPORTS:
        page.set_viewport_size({'width': w, 'height': h})
        for path, name in ROUTES:
            page.goto(BASE + path, wait_until='networkidle')
            page.wait_for_timeout(300)
            ov = page.evaluate(
                '() => document.documentElement.scrollWidth - document.documentElement.clientWidth')
            if ov > 2:
                problems.append(f'{name} ({path}) @{w}px 横向溢出 {ov}px')

    browser.close()

print(json.dumps({'problems': problems}, ensure_ascii=False, indent=2))
print('PROBLEMS:', len(problems))
