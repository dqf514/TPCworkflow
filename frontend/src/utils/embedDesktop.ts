import type { LocationQueryRaw, RouteLocationNormalized, Router } from 'vue-router'

export const EMBED_DESKTOP_QUERY = 'desktop'
export const EMBED_DESKTOP_SESSION_KEY = 'tpc_embed_desktop'

type WebViewWindow = Window & { chrome?: { webview?: unknown } }

/** 是否运行在 Windows 客户端 WebView2 内 */
export function isWebViewHost(): boolean {
  return !!(window as WebViewWindow).chrome?.webview
}

export function markEmbedDesktopSession(): void {
  try {
    sessionStorage.setItem(EMBED_DESKTOP_SESSION_KEY, '1')
  } catch {
    /* ignore */
  }
}

/** 当前是否处于桌面客户端嵌入模式（URL 参数 / WebView / 会话标记） */
export function isEmbedDesktopActive(to?: {
  query?: RouteLocationNormalized['query'] | LocationQueryRaw
}): boolean {
  const q = to?.query?.embed
  if (q === EMBED_DESKTOP_QUERY) return true
  if (isWebViewHost()) return true
  try {
    return sessionStorage.getItem(EMBED_DESKTOP_SESSION_KEY) === '1'
  } catch {
    return false
  }
}

export function withEmbedQuery(query: LocationQueryRaw = {}): LocationQueryRaw {
  if (!isEmbedDesktopActive({ query })) return query
  return { ...query, embed: EMBED_DESKTOP_QUERY }
}

/** 路由守卫：内嵌模式下始终保留 embed=desktop，避免 SPA 跳转后露出 Web 导航 */
export function ensureEmbedDesktopQuery(to: RouteLocationNormalized) {
  if (!isEmbedDesktopActive(to)) return null
  markEmbedDesktopSession()
  if (to.meta.public) return null
  if (to.query.embed === EMBED_DESKTOP_QUERY) return null
  return {
    path: to.path,
    query: { ...to.query, embed: EMBED_DESKTOP_QUERY },
    hash: to.hash,
    replace: true,
  }
}

export function syncEmbedDesktopDocumentClass(active: boolean): void {
  document.documentElement.classList.toggle('tpc-embed-desktop', active)
}

export function routerPushWithEmbed(router: Router, to: Parameters<Router['push']>[0]) {
  if (!isEmbedDesktopActive()) return router.push(to)
  if (typeof to === 'string') {
    return router.push({ path: to, query: { embed: EMBED_DESKTOP_QUERY } })
  }
  const loc = typeof to === 'object' && to ? to : {}
  const query = withEmbedQuery((loc as { query?: LocationQueryRaw }).query || {})
  return router.push({ ...loc, query })
}
