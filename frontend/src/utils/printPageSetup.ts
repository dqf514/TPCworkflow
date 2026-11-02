/**
 * 打印纸张设置（@page 动态注入）。
 *
 * 背景：print.css 里原本写死了 `@page { size: A4 portrait; margin: 12mm }`，
 * 表单/打印模板上配置的 pageSize、orientation、marginMm 因此全部失效（横向 A4 打不出来）。
 * 浏览器对 `@page` 内的 CSS 变量支持很有限（Chrome 不支持），
 * 所以采用「容器上写 CSS 变量 + 打印前动态注入真实 @page 规则」的方案：
 * 组件把纸张设置写到打印容器（.wf-print-mount）的自定义属性上，
 * printElement() 在 window.print() 之前读取这些变量并注入 @page 规则。
 */

/** 打印容器上承载纸张设置的自定义属性 */
export const PRINT_VAR_SIZE = '--wf-print-page-size'
export const PRINT_VAR_ORIENTATION = '--wf-print-orientation'
export const PRINT_VAR_MARGIN = '--wf-print-margin'
export const PRINT_VAR_WIDTH = '--wf-print-page-width'
export const PRINT_VAR_HEIGHT = '--wf-print-page-height'

/** 动态注入的 @page 样式节点 id */
const PAGE_STYLE_ID = 'wf-print-page-style'

export interface PrintPageSetup {
  /** 纸张尺寸，如 A4 / A3 */
  size?: string | null
  /** 方向 */
  orientation?: string | null
  /** 页边距（毫米） */
  marginMm?: number | null
}

export interface ResolvedPrintPageSetup {
  size: string
  orientation: 'portrait' | 'landscape'
  marginMm: number
  widthMm: number
  heightMm: number
}

const DEFAULT_SIZE = 'A4'
const DEFAULT_ORIENTATION = 'portrait'
const DEFAULT_MARGIN_MM = 12
const MAX_MARGIN_MM = 50

/** 允许的纸张尺寸白名单，避免非法值让整条 @page 规则失效 */
const ALLOWED_SIZES = ['A3', 'A4', 'A5', 'B4', 'B5', 'Letter', 'Legal', 'Tabloid']

/** 纸张物理尺寸（毫米，竖向） */
const PAGE_DIMENSIONS: Record<string, [number, number]> = {
  A3: [297, 420],
  A4: [210, 297],
  A5: [148, 210],
  B4: [250, 353],
  B5: [176, 250],
  Letter: [215.9, 279.4],
  Legal: [215.9, 355.6],
  Tabloid: [279.4, 431.8],
}

/** 归一化纸张设置：非法值一律退回默认，避免打印直接失败 */
export function normalizePrintPageSetup(setup?: PrintPageSetup | null): ResolvedPrintPageSetup {
  const rawSize = String(setup?.size || '').trim().toUpperCase()
  const size = ALLOWED_SIZES.includes(rawSize) ? rawSize : DEFAULT_SIZE
  const orientation =
    String(setup?.orientation || '').trim().toLowerCase() === 'landscape'
      ? 'landscape'
      : DEFAULT_ORIENTATION
  const rawMargin = Number(setup?.marginMm)
  const marginMm = Number.isFinite(rawMargin)
    ? Math.min(Math.max(rawMargin, 0), MAX_MARGIN_MM)
    : DEFAULT_MARGIN_MM
  const [baseWidth, baseHeight] = PAGE_DIMENSIONS[size] || PAGE_DIMENSIONS[DEFAULT_SIZE]
  return {
    size,
    orientation,
    marginMm,
    widthMm: orientation === 'landscape' ? baseHeight : baseWidth,
    heightMm: orientation === 'landscape' ? baseWidth : baseHeight,
  }
}

/** 生成打印容器上承载纸张设置的 CSS 变量 */
export function printPageVars(setup?: PrintPageSetup | null): Record<string, string> {
  const s = normalizePrintPageSetup(setup)
  return {
    [PRINT_VAR_SIZE]: s.size,
    [PRINT_VAR_ORIENTATION]: s.orientation,
    [PRINT_VAR_MARGIN]: `${s.marginMm}mm`,
    [PRINT_VAR_WIDTH]: `${s.widthMm}mm`,
    [PRINT_VAR_HEIGHT]: `${s.heightMm}mm`,
  }
}

/** 从元素上读取 CSS 变量值（自定义属性会继承） */
function readVar(host: HTMLElement | null, name: string): string {
  if (!host) return ''
  try {
    return String(getComputedStyle(host).getPropertyValue(name) || '').trim()
  } catch {
    return ''
  }
}

/** 解析 "12mm" / "12" 形式的页边距 */
function parseMargin(raw: string): number | null {
  if (!raw) return null
  const n = Number.parseFloat(raw)
  if (!Number.isFinite(n)) return null
  return n
}

/**
 * 读取打印容器上的纸张设置。
 * 优先取 .wf-print-mount（整份文档的纸张设置），取不到再退回元素自身。
 */
export function readPrintPageSetup(el: HTMLElement | null): ResolvedPrintPageSetup {
  const host = (el?.closest('.wf-print-mount') as HTMLElement | null) || el
  const size = readVar(host, PRINT_VAR_SIZE)
  const orientation = readVar(host, PRINT_VAR_ORIENTATION)
  const marginMm = parseMargin(readVar(host, PRINT_VAR_MARGIN))
  return normalizePrintPageSetup({
    size: size || undefined,
    orientation: orientation || undefined,
    marginMm: marginMm == null ? undefined : marginMm,
  })
}

/** 注入（或更新）真实的 @page 规则 */
export function applyPrintPageStyle(setup?: PrintPageSetup | null): void {
  if (typeof document === 'undefined') return
  const s = normalizePrintPageSetup(setup)
  const css = `@media print { @page { size: ${s.size} ${s.orientation}; margin: ${s.marginMm}mm; } }`
  let style = document.getElementById(PAGE_STYLE_ID) as HTMLStyleElement | null
  if (!style) {
    style = document.createElement('style')
    style.id = PAGE_STYLE_ID
    document.head.appendChild(style)
  }
  if (style.textContent !== css) style.textContent = css
}

/** 移除动态注入的 @page 规则 */
export function clearPrintPageStyle(): void {
  if (typeof document === 'undefined') return
  const style = document.getElementById(PAGE_STYLE_ID)
  if (style && style.parentNode) style.parentNode.removeChild(style)
}
