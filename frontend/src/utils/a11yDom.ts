/**
 * 全局无障碍增强（DOM 后处理）。
 *
 * 背景：Arco Design 2.57 的 `FormItemLabel` **从不输出 `for` 属性**，
 * `a-form-item` 的 `field` prop 只会：
 *   1. 把字段注册进所属 `a-form`（使 `:required` / `:rules` 变成真校验）；
 *   2. 给 label 所在列容器生成稳定 id（`getFormElementId(form.id, field)`）。
 * 因此「label ↔ 控件」的程序化关联必须由这里补上，否则读屏只念 placeholder。
 *
 * 同时补齐表格语义：`<th scope="col">` 与（可选的）`<caption>`。
 */

/** 表单项内的第一个可用表单控件 */
const CONTROL_SELECTOR = [
  'input:not([type="hidden"]):not([disabled])',
  'textarea:not([disabled])',
  'select:not([disabled])',
].join(',')

let idCounter = 0

function nextFieldId(): string {
  idCounter += 1
  return `tpc-field-${idCounter}`
}

/**
 * 为每个 `a-form-item` 的 `<label>` 补 `for`，并给控件补 `id`。
 * 已经有关联的项直接跳过，重复调用是幂等的。
 */
export function applyFormLabelAssociations(root: ParentNode = document): void {
  if (!root || typeof root.querySelectorAll !== 'function') return
  const items = root.querySelectorAll<HTMLElement>('.arco-form-item')
  items.forEach((item) => {
    const label = item.querySelector<HTMLLabelElement>('label.arco-form-item-label')
    if (!label) return
    if (label.getAttribute('for')) return
    // 只在该表单项自己的内容区里找控件，避免误关联到相邻表单项
    const scope =
      item.querySelector<HTMLElement>('.arco-form-item-content') ||
      item.querySelector<HTMLElement>('.arco-form-item-content-wrapper') ||
      item
    const control = scope.querySelector<HTMLElement>(CONTROL_SELECTOR)
    if (!control) return
    if (!control.id) control.id = nextFieldId()
    label.setAttribute('for', control.id)
  })
}

/** 给表头单元格补 `scope="col"`（Arco 的 a-table 不提供该属性） */
export function applyTableHeaderScopes(root: ParentNode = document): void {
  if (!root || typeof root.querySelectorAll !== 'function') return
  root.querySelectorAll<HTMLTableCellElement>('table thead th').forEach((th) => {
    if (!th.getAttribute('scope')) th.setAttribute('scope', 'col')
  })
}

/**
 * 为带有 `data-caption` 的 Arco 表格插入 `<caption>`。
 * Arco 的 `a-table` 不支持 caption 插槽，只能在 DOM 层补。
 */
export function applyTableCaptions(root: ParentNode = document): void {
  if (!root || typeof root.querySelectorAll !== 'function') return
  root.querySelectorAll<HTMLElement>('.arco-table[data-caption]').forEach((wrap) => {
    const text = wrap.getAttribute('data-caption')
    if (!text) return
    const table = wrap.querySelector('table')
    if (!table) return
    if (table.querySelector('caption')) return
    const caption = document.createElement('caption')
    caption.className = 'a11y-table-caption'
    caption.textContent = text
    table.insertBefore(caption, table.firstChild)
  })
}

/** 一次性执行全部 DOM 无障碍增强 */
export function applyA11yDomEnhancements(root: ParentNode = document): void {
  applyFormLabelAssociations(root)
  applyTableHeaderScopes(root)
  applyTableCaptions(root)
}

let observer: MutationObserver | null = null
let scheduled = false

/**
 * 安装全局 DOM 增强：
 * - 首次挂载后执行一次；
 * - 之后监听 DOM 变化（去抖到下一帧）增量补齐。
 */
export function installA11yDomEnhancements(): void {
  if (typeof document === 'undefined') return
  applyA11yDomEnhancements()

  if (observer || typeof MutationObserver === 'undefined') return
  observer = new MutationObserver(() => {
    if (scheduled) return
    scheduled = true
    const run = () => {
      scheduled = false
      applyA11yDomEnhancements()
    }
    if (typeof requestAnimationFrame === 'function') requestAnimationFrame(run)
    else setTimeout(run, 0)
  })
  observer.observe(document.body, { childList: true, subtree: true })
}

/** 停止 DOM 增强监听（测试 / 卸载时使用） */
export function uninstallA11yDomEnhancements(): void {
  observer?.disconnect()
  observer = null
}
