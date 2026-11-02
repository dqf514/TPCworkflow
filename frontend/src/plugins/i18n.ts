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
import { profileEn, profileZh } from '@/i18n/bundles/profile'
import { financeEn, financeZh } from '@/i18n/bundles/finance'

export const arcoLocaleMap: Record<string, typeof arcoZhCN> = {
  'zh-CN': arcoZhCN,
  'en-US': arcoEnUS,
}

/**
 * 扁平字典转嵌套结构。
 *
 * 字典里可能同时存在「叶子键」与「同名前缀键」（如 common 与 common.save），
 * 两者在嵌套结构里会互相覆盖。这里让叶子键优先占用该路径，
 * 被占用前缀下的子键不再嵌套，改由 missing 兜底按完整 key 回查，
 * 保证两边都不会丢。
 */
function nestMessages(flat: Record<string, string>): Record<string, unknown> {
  const root: Record<string, unknown> = {}
  for (const [fullKey, value] of Object.entries(flat)) {
    const parts = fullKey.split('.')
    // 父路径已被叶子键占用时无法再挂子键，交给 missing 按扁平 key 回查
    let blocked = false
    for (let i = 1; i < parts.length; i++) {
      if (Object.prototype.hasOwnProperty.call(flat, parts.slice(0, i).join('.'))) {
        blocked = true
        break
      }
    }
    if (blocked) continue
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

/** 各语言的扁平字典：用于「叶子键 + 同名前缀键」冲突时按完整 key 回查 */
const flatMessageStore: Record<string, Record<string, string>> = {}

/**
 * vue-i18n v9 把 `@` 当作「引用其他词条」的前缀（`@:other.key`），
 * 文案里出现裸 `@`（如 `@internal:8080/v1`）会让整条消息编译失败，
 * 表现为「Invalid linked format / Unexpected lexical analysis」控制台报错。
 *
 * 这里把非引用形式的 `@` 转义成 vue-i18n 的字面量写法 `{'@'}`；
 * 已经写成 `{'@'}` 的不会二次转义，`@:key` 这种真正的引用也原样保留。
 */
function escapeLinkedAt(text: string): string {
  return text.replace(/(?<!\{')@(?!:)/g, "{'@'}")
}

/** 对整份扁平字典做转义；返回新对象，不改原对象 */
function sanitizeFlat(flat: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(flat)) out[k] = escapeLinkedAt(v)
  return out
}

/** 把 vue-i18n 的字面量转义还原成普通字符（用于 missing 回查等非编译路径） */
function unescapeLinkedAt(text: string): string {
  return text.replace(/\{'@'\}/g, '@')
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
  missing: (locale, key) => {
    // 嵌套结构里被叶子键挤掉的子键，这里按扁平 key 回查
    const store = flatMessageStore[locale as string] || flatMessageStore['zh-CN']
    const text = store?.[key]
    if (text) return unescapeLinkedAt(text)
    if (import.meta.env.DEV) console.warn('[i18n] missing:', key)
    return key
  },
})

const NAMESPACES =
  'common,menu,auth,login,workflow,monitor,dashboard,apply,validation,admin,studio,org,designer,flowRole,flowDesign,wfSettings,settings,client,leave_calendar,print,profile,finance'

/** 命名空间列表变更时递增，使浏览器旧 sessionStorage 缓存失效 */
const I18N_BUNDLE_CACHE_ID = 'v32-i18n-at-escape'

/** 远端若仍存含 ${ 的旧公式文案，会触发 vue-i18n 编译错误导致属性面板空白 */
const I18N_UNSAFE_VALUE = /\$\{|\{\{/

function isUnsafeI18nValue(key: string, value: string): boolean {
  if (!value || !I18N_UNSAFE_VALUE.test(value)) return false
  if (key.startsWith('designer.formula')) return true
  if (key.startsWith('flowDesign.') && (key.includes('email') || key.includes('notify'))) return true
  return false
}

const localeFallbackByLocale: Record<string, Record<string, string>> = {
  'zh-CN': { ...menuNavZh, ...settingsZh, ...designerZh, ...studioOrgZh, ...workflowApplyZh, ...adminLogsZh, ...printZh, ...clientZh, ...profileZh, ...financeZh },
  'en-US': { ...menuNavEn, ...settingsEn, ...designerEn, ...studioOrgEn, ...workflowApplyEn, ...adminLogsEn, ...printEn, ...clientEn, ...profileEn, ...financeEn },
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

/** sessionStorage 读写在隐私模式/配额超限时可能抛错，统一兜住 */
function safeSessionGet(key: string): string | null {
  try {
    return sessionStorage.getItem(key)
  } catch (e) {
    if (import.meta.env.DEV) console.warn('[i18n] sessionStorage read failed', e)
    return null
  }
}

function safeSessionSet(key: string, value: string): void {
  try {
    sessionStorage.setItem(key, value)
  } catch (e) {
    if (import.meta.env.DEV) console.warn('[i18n] sessionStorage write failed', e)
  }
}

function safeSessionRemove(key: string): void {
  try {
    sessionStorage.removeItem(key)
  } catch (e) {
    if (import.meta.env.DEV) console.warn('[i18n] sessionStorage remove failed', e)
  }
}

function safeLocalSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch (e) {
    if (import.meta.env.DEV) console.warn('[i18n] localStorage write failed', e)
  }
}

/**
 * 只用本地兜底包装配文案：远端字典不可用时的兜底，保证界面不会出现空白文案
 */
export function applyLocalBundleMessages(locale: string): void {
  const raw = localeFallbackByLocale[locale] || localeFallbackByLocale['zh-CN']
  if (!raw || Object.keys(raw).length === 0) return
  flatMessageStore[locale] = { ...raw }
  i18n.global.setLocaleMessage(locale, nestMessages(sanitizeFlat(raw)) as never)
  i18n.global.locale.value = locale as 'zh-CN' | 'en-US'
  document.documentElement.lang = locale
}

export async function loadLocaleMessages(locale: string, force = false): Promise<void> {
  try {
    await doLoadLocaleMessages(locale, force)
  } catch (e) {
    // 任何异常都不能阻断启动：退回本地兜底包继续渲染
    if (import.meta.env.DEV) console.warn('[i18n] load failed, fallback to local bundle', e)
    applyLocalBundleMessages(locale)
  }
}

async function doLoadLocaleMessages(locale: string, force: boolean): Promise<void> {
  const cacheKey = `i18n:${locale}:${I18N_BUNDLE_CACHE_ID}:${NAMESPACES}`
  if (force) {
    safeSessionRemove(cacheKey)
  }
  const cachedRaw = safeSessionGet(cacheKey)
  let cached: { version?: number; messages?: Record<string, string> } | null = null
  if (cachedRaw) {
    try {
      const parsed = JSON.parse(cachedRaw)
      cached = parsed && typeof parsed === 'object' ? parsed : null
    } catch (e) {
      // 缓存被写坏时直接丢弃，不能让 JSON.parse 的异常冒到启动流程
      if (import.meta.env.DEV) console.warn('[i18n] cache parse failed', e)
      safeSessionRemove(cacheKey)
      cached = null
    }
  }

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

  // 远端与本地文案都可能含裸 `@`，统一转义后再交给 vue-i18n 编译
  const rawFlat = flat
  flat = sanitizeFlat(flat)

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
    flatMessageStore[locale] = { ...rawFlat }
    i18n.global.setLocaleMessage(locale, nested as never)
    safeSessionSet(cacheKey, JSON.stringify({ version, messages: rawFlat }))
  }

  i18n.global.locale.value = locale as 'zh-CN' | 'en-US'
  document.documentElement.lang = locale
  safeLocalSet('locale', locale)
}
