/**
 * 应用外壳内的滚动容器。
 *
 * 应用外壳（`.app-shell`）是 `height:100dvh; overflow:hidden`，
 * 真正滚动的是 `.app-content`（`overflow-y:auto`），
 * 因此 vue-router 默认的 window 滚动复位对本站无效 —— 必须显式复位该容器。
 */
export const APP_SCROLL_CONTAINER_SELECTOR = '.app-content'

/** 把应用内容区滚动回顶部（左上角），无滚动容器时静默跳过。 */
export function resetAppScroll(): void {
  if (typeof document === 'undefined') return
  const el = document.querySelector<HTMLElement>(APP_SCROLL_CONTAINER_SELECTOR)
  if (!el) return
  if (typeof el.scrollTo === 'function') {
    el.scrollTo({ top: 0, left: 0 })
  } else {
    el.scrollTop = 0
    el.scrollLeft = 0
  }
}
