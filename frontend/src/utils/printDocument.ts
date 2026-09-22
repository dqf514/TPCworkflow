/**
 * 在当前页面唤起打印，不打开 about:blank 新窗口。
 * 配合 body.wf-print-active 与 styles/print.css 仅输出打印稿 DOM。
 */
import { Message } from '@arco-design/web-vue'

const BODY_CLASS = 'wf-print-active'
const PRINT_VIEW_CLASS = 'wf-print-view'

/** 清除打印预览/打印会话留在 body 上的样式类，避免路由切换后导航栏消失 */
export function clearPrintBodyClasses(): void {
  document.body.classList.remove(BODY_CLASS)
  document.body.classList.remove(PRINT_VIEW_CLASS)
}

export function beginPrintSession(): void {
  document.body.classList.add(BODY_CLASS)
}

export function endPrintSession(): void {
  document.body.classList.remove(BODY_CLASS)
}

export function setPrintViewMode(active: boolean): void {
  document.body.classList.toggle(PRINT_VIEW_CLASS, active)
  if (!active) endPrintSession()
}

/** 使嵌套 PDF 查看器等失焦，避免 Chrome 拦截父页面 window.print() */
function focusPrintRoot(): void {
  const active = document.activeElement
  if (active instanceof HTMLIFrameElement || active instanceof HTMLObjectElement) {
    active.blur()
  } else if (active instanceof HTMLElement && active !== document.body) {
    active.blur()
  }
  window.focus()
}

/** 系统打印前移除预览阶段的 Toast 等浮层，避免进入 PDF */
function dismissTransientUiBeforePrint(): void {
  Message.clear()
  document
    .querySelectorAll('.arco-message-wrapper, .arco-message-list, .arco-notification-wrapper')
    .forEach((el) => el.remove())
}

export function printElement(_element: HTMLElement, docTitle = ' '): void {
  const prevTitle = document.title
  const safe = (docTitle || ' ').replace(/</g, '')
  if (safe.trim()) document.title = safe

  focusPrintRoot()
  dismissTransientUiBeforePrint()
  beginPrintSession()

  const cleanup = () => {
    endPrintSession()
    document.title = prevTitle
    window.removeEventListener('afterprint', cleanup)
  }
  window.addEventListener('afterprint', cleanup, { once: true })

  // 必须在用户点击事件的同步调用栈内触发，否则浏览器会拦截 window.print()
  window.print()
  setTimeout(() => {
    if (document.body.classList.contains(BODY_CLASS)) cleanup()
  }, 2000)
}
