/** 当前审批节点已持续时长（本地时间） */
export function formatStepDuration(
  iso: string | null | undefined,
  now: Date = new Date(),
): string {
  if (!iso) return ''
  const start = new Date(iso)
  if (Number.isNaN(start.getTime())) return ''
  let sec = Math.floor((now.getTime() - start.getTime()) / 1000)
  if (sec < 0) sec = 0
  const d = Math.floor(sec / 86400)
  sec %= 86400
  const h = Math.floor(sec / 3600)
  sec %= 3600
  const m = Math.floor(sec / 60)
  if (d > 0) return `已等待 ${d} 天 ${h} 小时`
  if (h > 0) return `已等待 ${h} 小时 ${m} 分钟`
  if (m > 0) return `已等待 ${m} 分钟`
  return '刚刚到达本节点'
}
