import { createI18n } from 'vue-i18n'
import arcoZhCN from '@arco-design/web-vue/es/locale/lang/zh-cn'
import arcoEnUS from '@arco-design/web-vue/es/locale/lang/en-us'
import { api, type ApiResponse } from '@/api/client'
import { designerEn, designerZh } from '@/i18n/bundles/designer'
import { settingsEn, settingsZh } from '@/i18n/bundles/settings'
import { studioOrgEn, studioOrgZh } from '@/i18n/bundles/studioOrg'
import { workflowApplyEn, workflowApplyZh } from '@/i18n/bundles/workflowApply'
import { menuNavEn, menuNavZh } from '@/i18n/bundles/menuNav'
import { adminLogsEn, adminLogsZh } from '@/i18n/bundles/adminLogs'
import { printEn, printZh } from '@/i18n/bundles/print'
import { clientEn, clientZh } from '@/i18n/bundles/client'

export const arcoLocaleMap: Record<string, typeof arcoZhCN> = {
  'zh-CN': arcoZhCN,
  'en-US': arcoEnUS,
}

function nestMessages(flat: Record<string, string>): Record<string, unknown> {
  const root: Record<string, unknown> = {}
  for (const [fullKey, value] of Object.entries(flat)) {
    const parts = fullKey.split('.')
    let cur = root
    for (let i = 0; i < parts.length - 1; i++) {
      const p = parts[i]
      if (!cur[p] || typeof cur[p] !== 'object') cur[p] = {}
      cur = cur[p] as Record<string, unknown>
    }
    cur[parts[parts.length - 1]] = value
  }
  return root
}

function deepMerge(
  base: Record<string, unknown>,
  over: Record<string, unknown>,
): Record<string, unknown> {
  const out = { ...base }
  for (const [k, v] of Object.entries(over)) {
    if (v && typeof v === 'object' && !Array.isArray(v) && typeof out[k] === 'object') {
      out[k] = deepMerge(out[k] as Record<string, unknown>, v as Record<string, unknown>)
    } else {
      out[k] = v
    }
  }
  return out
}

export const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: {},
  missing: (_locale, key) => {
    if (import.meta.env.DEV) console.warn('[i18n] missing:', key)
    return key
  },
})

const NAMESPACES =
  'common,menu,auth,login,workflow,monitor,dashboard,apply,validation,admin,studio,org,designer,flowRole,flowDesign,wfSettings,settings,client,leave_calendar'

/** 命名空间列表变更时递增，使浏览器旧 sessionStorage 缓存失效 */
const I18N_BUNDLE_CACHE_ID = 'v28-calendar-holidays'

/** 远端若仍存含 ${ 的旧公式文案，会触发 vue-i18n 编译错误导致属性面板空白 */
const I18N_UNSAFE_VALUE = /\$\{|\{\{/

function isUnsafeI18nValue(key: string, value: string): boolean {
  if (!value || !I18N_UNSAFE_VALUE.test(value)) return false
  if (key.startsWith('designer.formula')) return true
  if (key.startsWith('flowDesign.') && (key.includes('email') || key.includes('notify'))) return true
  return false
}

const localeFallbackByLocale: Record<string, Record<string, string>> = {
  'zh-CN': { ...menuNavZh, ...settingsZh, ...designerZh, ...studioOrgZh, ...workflowApplyZh, ...adminLogsZh, ...printZh, ...clientZh },
  'en-US': { ...menuNavEn, ...settingsEn, ...designerEn, ...studioOrgEn, ...workflowApplyEn, ...adminLogsEn, ...printEn, ...clientEn },
}

function mergeFlat(
  base: Record<string, string>,
  over: Record<string, string> | null | undefined,
): Record<string, string> {
  const out = { ...base }
  if (!over) return out
  for (const [k, v] of Object.entries(over)) {
    const text = (v ?? '').trim()
    // 远端未翻译或误存键名时，保留本地兜底文案
    if (!text || text === k) continue
    if (isUnsafeI18nValue(k, text)) continue
    out[k] = v
  }
  return out
}

async function fetchNamespaceMessages(
  locale: string,
  namespaces: string,
): Promise<Record<string, string>> {
  const res = await api.get<ApiResponse<{ version: number; messages: Record<string, string> }>>(
    '/i18n/messages',
    { params: { locale, namespaces } },
  )
  if (res.data?.ok && res.data.data?.messages) {
    return res.data.data.messages
  }
  return {}
}

export async function loadLocaleMessages(locale: string, force = false): Promise<void> {
  const cacheKey = `i18n:${locale}:${I18N_BUNDLE_CACHE_ID}:${NAMESPACES}`
  if (force) {
    sessionStorage.removeItem(cacheKey)
  }
  const cachedRaw = sessionStorage.getItem(cacheKey)
  const cached = cachedRaw ? JSON.parse(cachedRaw) : null

  let flat: Record<string, string> | null = null
  let version = 0

  try {
    const res = await api.get<ApiResponse<{ version: number; messages: Record<string, string> }>>(
      '/i18n/messages',
      {
        params: { locale, namespaces: NAMESPACES },
        headers: cached && !force ? { 'X-I18n-Version': String(cached.version) } : {},
        validateStatus: (s) => s === 200 || s === 304,
      },
    )

    if (res.status === 304 && cached?.messages) {
      flat = cached.messages
      version = cached.version
    } else if (res.data?.ok && res.data.data) {
      flat = res.data.data.messages || {}
      version = res.data.data.version
    }
  } catch (e) {
    if (import.meta.env.DEV) console.warn('[i18n] load failed', e)
    if (cached?.messages) {
      flat = cached.messages
      version = cached.version
    }
  }

  const fallback = localeFallbackByLocale[locale] || localeFallbackByLocale['zh-CN']
  flat = mergeFlat(fallback, flat)

  const ensureNamespaces: string[] = []
  if (!flat['settings.page_desc']) ensureNamespaces.push('settings')
  if (!flat['wfSettings.apply_visibility']) ensureNamespaces.push('wfSettings')
  if (!flat['studio.title']) ensureNamespaces.push('studio')
  if (!flat['flowDesign.node_start']) ensureNamespaces.push('flowDesign')
  if (ensureNamespaces.length) {
    try {
      const extra = await fetchNamespaceMessages(locale, [...new Set(ensureNamespaces)].join(','))
      flat = mergeFlat(flat, extra)
    } catch (e) {
      if (import.meta.env.DEV) {
        console.warn('[i18n] supplemental namespace fetch failed', ensureNamespaces, e)
      }
    }
  }

  if (!flat || Object.keys(flat).length === 0) {
    if (locale !== 'zh-CN') {
      await loadLocaleMessages('zh-CN', false)
      const zh = i18n.global.getLocaleMessage('zh-CN') as Record<string, unknown>
      i18n.global.setLocaleMessage(locale, structuredClone(zh) as never)
    }
  } else {
    let nested = nestMessages(flat)
    if (locale !== 'zh-CN' && Object.keys(flat).length < 5) {
      const zh = i18n.global.getLocaleMessage('zh-CN') as Record<string, unknown>
      nested = deepMerge(zh, nested)
    }
    i18n.global.setLocaleMessage(locale, nested as never)
    sessionStorage.setItem(cacheKey, JSON.stringify({ version, messages: flat }))
  }

  i18n.global.locale.value = locale as 'zh-CN' | 'en-US'
  document.documentElement.lang = locale
  localStorage.setItem('locale', locale)
}
