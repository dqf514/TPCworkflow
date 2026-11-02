/**
 * 稳定的 v-for key 生成器。
 *
 * 用数组下标当 key 时，Vue 依赖 diff 只按位置复用 DOM：数据重排或增删后，
 * 会把上一条记录的 DOM 原地改成另一条内容，出现「渲染错位」。
 * 这里按内容派生 key，内容重复时追加序号保证唯一。
 */

/** 为一组元素生成稳定且唯一的 key */
export function stableKeys<T>(
  items: readonly T[] | undefined | null,
  keyOf: (item: T, index: number) => string,
): string[] {
  if (!items || !items.length) return []
  const seen = new Map<string, number>()
  return items.map((item, i) => {
    const base = (keyOf(item, i) || '').trim() || `i-${i}`
    const n = seen.get(base) || 0
    seen.set(base, n + 1)
    return n === 0 ? base : `${base}#${n}`
  })
}

/** 用行内容拼出一个签名，作为明细行的稳定 key（无业务主键时使用） */
export function rowSignature(
  row: Record<string, unknown> | undefined | null,
  columns: readonly string[],
): string {
  if (!row) return ''
  return columns.map((c) => String(row[c] ?? '')).join('|')
}
