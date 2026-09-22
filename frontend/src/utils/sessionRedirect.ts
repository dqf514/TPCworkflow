import { isEmbedDesktopActive } from '@/utils/embedDesktop'

/** 会话过期后跳转登录（使用硬跳转，避免在路由守卫中 router.push 死锁） */
let redirectScheduled = false

function isAuthProbeUrl(url: string): boolean {
  return /\/auth\/(me|login|login-methods|captcha|logout)(?:\?|$)/.test(url)
}

export function shouldRedirectOn401(url: string): boolean {
  if (isAuthProbeUrl(url)) return false
  if (window.location.pathname.startsWith('/login')) return false
  if (window.location.pathname.startsWith('/auth/azure')) return false
  return true
}

export function scheduleSessionExpiredRedirect(reason = 'session_expired') {
  if (redirectScheduled) return
  if (window.location.pathname.startsWith('/login')) return
  // 桌面客户端 WebView：认证由宿主处理，不在内嵌页弹出 Web 登录
  if (isEmbedDesktopActive()) return
  redirectScheduled = true
  window.setTimeout(() => {
    const redirect = encodeURIComponent(
      window.location.pathname + window.location.search + window.location.hash,
    )
    window.location.assign(`/login?reason=${reason}&redirect=${redirect}`)
  }, 50)
}

export function resetSessionRedirectFlag() {
  redirectScheduled = false
}
