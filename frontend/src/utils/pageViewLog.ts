import type { RouteLocationNormalized } from 'vue-router'

import { api } from '@/api/client'

const ROUTE_TITLES: Record<string, string> = {
  dashboard: '工作台',
  apply: '发起申请',
  'apply-start': '填写申请',
  tasks: '待办',
  'task-detail': '待办详情',
  'instance-detail': '申请详情',
  'my-instances': '我的申请',
  'admin-org': '组织架构',
  'admin-form-studio': '表单与流程设计',
  'admin-sector-monitor': '板块流程统计',
  'admin-finance-export': '财务凭证导出',
  'admin-settings': '系统设置',
  'admin-logs': '系统日志',
}

const SETTINGS_TAB_TITLES: Record<string, string> = {
  brand: '组织品牌',
  sectors: '业务板块',
  admins: '管理员',
  mail: '邮件',
  attachments: '附件上传',
  sms: '短信',
  azure: 'Azure SSO',
  'option-sets': '选项配置表',
  'record-sets': '控件配置表',
  'exchange-rates': '汇率管理',
  llm: '大模型',
  'workflow-instances': '全部审批单',
  'print-templates': '打印模板',
  i18n: '多语言',
}

function resolvePageTitle(to: RouteLocationNormalized): string {
  const routeName = String(to.name || '')
  if (routeName === 'admin-settings') {
    const tab = typeof to.query.tab === 'string' ? to.query.tab : ''
    if (tab && SETTINGS_TAB_TITLES[tab]) {
      return `系统设置 · ${SETTINGS_TAB_TITLES[tab]}`
    }
    return '系统设置'
  }
  if (routeName === 'admin-org') {
    const tab = typeof to.query.tab === 'string' ? to.query.tab : ''
    if (tab === 'roles') return '组织架构 · 流程角色'
    return '组织架构'
  }
  if (routeName === 'task-detail' && to.params.id) {
    return `待办详情 #${to.params.id}`
  }
  if (routeName === 'instance-detail' && to.params.uuid) {
    return '申请详情'
  }
  if (routeName === 'apply-start' && to.query.definition_id) {
    return '填写申请'
  }
  return ROUTE_TITLES[routeName] || routeName || to.path
}

let lastReportKey = ''
let lastReportAt = 0

/** 路由切换后上报页面访问（同一路径 2 秒内不重复上报）。 */
export async function reportPageView(to: RouteLocationNormalized) {
  if (to.meta.public) return
  const path = to.fullPath || to.path
  const key = `${String(to.name || '')}|${path}`
  const now = Date.now()
  if (key === lastReportKey && now - lastReportAt < 2000) return
  lastReportKey = key
  lastReportAt = now

  const routeName = String(to.name || '')
  const title = resolvePageTitle(to)
  try {
    await api.post('/auth/page-view', {
      path,
      route_name: routeName,
      title,
    })
  } catch {
    /* 页面访问日志失败不影响正常使用 */
  }
}
