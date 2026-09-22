/** 企业办公流常见流程图标（Canvas 绘制，缓存为 Data URL） */

export type ProcessIconKey =
  | 'general'
  | 'approval'
  | 'travel'
  | 'expense'
  | 'reimburse'
  | 'leave'
  | 'overtime'
  | 'purchase'
  | 'contract'
  | 'seal'
  | 'meeting'
  | 'recruitment'
  | 'onboarding'
  | 'offboarding'
  | 'asset'
  | 'invoice'
  | 'payment'
  | 'budget'
  | 'project'
  | 'customer'
  | 'supplier'
  | 'inventory'
  | 'maintenance'
  | 'it'
  | 'permission'
  | 'report'
  | 'loan'
  | 'gift'
  | 'training'
  | 'safety'
  | 'quality'
  | 'logistics'
  | 'ship'
  | 'hr'
  | 'finance'
  | 'admin'

export interface ProcessIconMeta {
  key: ProcessIconKey
  label: string
  color: string
}

export const PROCESS_ICON_CATALOG: ProcessIconMeta[] = [
  { key: 'general', label: '通用', color: '#5034ff' },
  { key: 'approval', label: '审批', color: '#5034ff' },
  { key: 'travel', label: '差旅', color: '#0ea5e9' },
  { key: 'expense', label: '费用', color: '#f59e0b' },
  { key: 'reimburse', label: '报销', color: '#10b981' },
  { key: 'leave', label: '请假', color: '#8b5cf6' },
  { key: 'overtime', label: '加班', color: '#6366f1' },
  { key: 'purchase', label: '采购', color: '#ec4899' },
  { key: 'contract', label: '合同', color: '#14b8a6' },
  { key: 'seal', label: '用印', color: '#ef4444' },
  { key: 'meeting', label: '会议', color: '#3b82f6' },
  { key: 'recruitment', label: '招聘', color: '#06b6d4' },
  { key: 'onboarding', label: '入职', color: '#22c55e' },
  { key: 'offboarding', label: '离职', color: '#64748b' },
  { key: 'asset', label: '资产', color: '#a855f7' },
  { key: 'invoice', label: '发票', color: '#f97316' },
  { key: 'payment', label: '付款', color: '#eab308' },
  { key: 'budget', label: '预算', color: '#0d9488' },
  { key: 'project', label: '项目', color: '#2563eb' },
  { key: 'customer', label: '客户', color: '#7c3aed' },
  { key: 'supplier', label: '供应商', color: '#db2777' },
  { key: 'inventory', label: '库存', color: '#ca8a04' },
  { key: 'maintenance', label: '维保', color: '#475569' },
  { key: 'it', label: 'IT', color: '#0284c7' },
  { key: 'permission', label: '权限', color: '#4f46e5' },
  { key: 'report', label: '报告', color: '#0891b2' },
  { key: 'loan', label: '借款', color: '#b45309' },
  { key: 'gift', label: '礼品', color: '#e11d48' },
  { key: 'training', label: '培训', color: '#059669' },
  { key: 'safety', label: '安全', color: '#dc2626' },
  { key: 'quality', label: '质量', color: '#16a34a' },
  { key: 'logistics', label: '物流', color: '#d97706' },
  { key: 'ship', label: '船舶', color: '#1d4ed8' },
  { key: 'hr', label: '人事', color: '#9333ea' },
  { key: 'finance', label: '财务', color: '#c2410c' },
  { key: 'admin', label: '行政', color: '#334155' },
]

const cache = new Map<string, string>()

/** 超采样倍数：生成 3 倍像素再缩小显示，Retina 屏也清晰 */
const RENDER_SCALE = 3

function metaOf(key: string): ProcessIconMeta {
  return PROCESS_ICON_CATALOG.find((m) => m.key === key) || PROCESS_ICON_CATALOG[0]
}

type Ctx = CanvasRenderingContext2D

function roundRect(ctx: Ctx, x: number, y: number, w: number, h: number, r: number) {
  const rr = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + rr, y)
  ctx.arcTo(x + w, y, x + w, y + h, rr)
  ctx.arcTo(x + w, y + h, x, y + h, rr)
  ctx.arcTo(x, y + h, x, y, rr)
  ctx.arcTo(x, y, x + w, y, rr)
  ctx.closePath()
}

function drawBase(ctx: Ctx, size: number, color: string) {
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  const pad = size * 0.12
  const g = ctx.createLinearGradient(0, 0, size, size)
  g.addColorStop(0, color)
  g.addColorStop(1, shade(color, -18))
  ctx.fillStyle = g
  roundRect(ctx, pad, pad, size - pad * 2, size - pad * 2, size * 0.22)
  ctx.fill()
  ctx.fillStyle = 'rgba(255,255,255,0.98)'
  ctx.strokeStyle = 'rgba(255,255,255,0.35)'
  ctx.lineWidth = Math.max(1.5, size * 0.04)
}

const ICON_FONT = '"PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif'

function shade(hex: string, pct: number): string {
  const n = hex.replace('#', '')
  const num = parseInt(n.length === 3 ? n.split('').map((c) => c + c).join('') : n, 16)
  const r = Math.min(255, Math.max(0, ((num >> 16) & 255) + pct))
  const g = Math.min(255, Math.max(0, ((num >> 8) & 255) + pct))
  const b = Math.min(255, Math.max(0, (num & 255) + pct))
  return `rgb(${r},${g},${b})`
}

const drawers: Record<ProcessIconKey, (ctx: Ctx, s: number) => void> = {
  general: (ctx, s) => {
    ctx.beginPath()
    ctx.arc(s * 0.5, s * 0.42, s * 0.14, 0, Math.PI * 2)
    ctx.fill()
    roundRect(ctx, s * 0.32, s * 0.58, s * 0.36, s * 0.22, s * 0.06)
    ctx.fill()
  },
  approval: (ctx, s) => {
    ctx.beginPath()
    ctx.moveTo(s * 0.28, s * 0.52)
    ctx.lineTo(s * 0.44, s * 0.68)
    ctx.lineTo(s * 0.72, s * 0.34)
    ctx.stroke()
  },
  travel: (ctx, s) => {
    roundRect(ctx, s * 0.3, s * 0.38, s * 0.4, s * 0.28, s * 0.06)
    ctx.fill()
    ctx.beginPath()
    ctx.arc(s * 0.38, s * 0.72, s * 0.07, 0, Math.PI * 2)
    ctx.arc(s * 0.62, s * 0.72, s * 0.07, 0, Math.PI * 2)
    ctx.fill()
  },
  expense: (ctx, s) => {
    ctx.font = `600 ${s * 0.36}px ${ICON_FONT}`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('¥', s * 0.5, s * 0.52)
  },
  reimburse: (ctx, s) => {
    ctx.beginPath()
    ctx.moveTo(s * 0.34, s * 0.36)
    ctx.lineTo(s * 0.66, s * 0.36)
    ctx.lineTo(s * 0.66, s * 0.68)
    ctx.lineTo(s * 0.34, s * 0.68)
    ctx.closePath()
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(s * 0.42, s * 0.5)
    ctx.lineTo(s * 0.58, s * 0.5)
    ctx.stroke()
  },
  leave: (ctx, s) => {
    roundRect(ctx, s * 0.32, s * 0.32, s * 0.36, s * 0.4, s * 0.05)
    ctx.stroke()
    ctx.fillRect(s * 0.38, s * 0.4, s * 0.24, s * 0.06)
    ctx.fillRect(s * 0.38, s * 0.52, s * 0.18, s * 0.06)
  },
  overtime: (ctx, s) => {
    ctx.beginPath()
    ctx.arc(s * 0.5, s * 0.5, s * 0.2, 0, Math.PI * 2)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(s * 0.5, s * 0.5)
    ctx.lineTo(s * 0.5, s * 0.36)
    ctx.moveTo(s * 0.5, s * 0.5)
    ctx.lineTo(s * 0.6, s * 0.54)
    ctx.stroke()
  },
  purchase: (ctx, s) => {
    ctx.beginPath()
    ctx.moveTo(s * 0.32, s * 0.4)
    ctx.lineTo(s * 0.68, s * 0.4)
    ctx.lineTo(s * 0.62, s * 0.68)
    ctx.lineTo(s * 0.38, s * 0.68)
    ctx.closePath()
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(s * 0.36, s * 0.4)
    ctx.lineTo(s * 0.4, s * 0.32)
    ctx.lineTo(s * 0.6, s * 0.32)
    ctx.lineTo(s * 0.64, s * 0.4)
    ctx.stroke()
  },
  contract: (ctx, s) => {
    roundRect(ctx, s * 0.3, s * 0.32, s * 0.4, s * 0.42, s * 0.04)
    ctx.stroke()
    for (let i = 0; i < 3; i++) {
      ctx.fillRect(s * 0.36, s * (0.4 + i * 0.1), s * 0.28, s * 0.05)
    }
  },
  seal: (ctx, s) => {
    ctx.beginPath()
    ctx.arc(s * 0.5, s * 0.5, s * 0.18, 0, Math.PI * 2)
    ctx.stroke()
    ctx.font = `600 ${s * 0.2}px ${ICON_FONT}`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('印', s * 0.5, s * 0.52)
  },
  meeting: (ctx, s) => {
    roundRect(ctx, s * 0.28, s * 0.42, s * 0.44, s * 0.22, s * 0.05)
    ctx.fill()
    ctx.beginPath()
    ctx.arc(s * 0.38, s * 0.36, s * 0.06, 0, Math.PI * 2)
    ctx.arc(s * 0.5, s * 0.34, s * 0.06, 0, Math.PI * 2)
    ctx.arc(s * 0.62, s * 0.36, s * 0.06, 0, Math.PI * 2)
    ctx.fill()
  },
  recruitment: (ctx, s) => {
    ctx.beginPath()
    ctx.arc(s * 0.5, s * 0.38, s * 0.1, 0, Math.PI * 2)
    ctx.fill()
    ctx.beginPath()
    ctx.moveTo(s * 0.34, s * 0.68)
    ctx.quadraticCurveTo(s * 0.5, s * 0.5, s * 0.66, s * 0.68)
    ctx.fill()
  },
  onboarding: (ctx, s) => {
    ctx.beginPath()
    ctx.moveTo(s * 0.34, s * 0.62)
    ctx.lineTo(s * 0.5, s * 0.34)
    ctx.lineTo(s * 0.66, s * 0.62)
    ctx.closePath()
    ctx.stroke()
    ctx.fillRect(s * 0.46, s * 0.62, s * 0.08, s * 0.1)
  },
  offboarding: (ctx, s) => {
    ctx.beginPath()
    ctx.moveTo(s * 0.34, s * 0.38)
    ctx.lineTo(s * 0.66, s * 0.62)
    ctx.moveTo(s * 0.66, s * 0.38)
    ctx.lineTo(s * 0.34, s * 0.62)
    ctx.stroke()
  },
  asset: (ctx, s) => {
    roundRect(ctx, s * 0.32, s * 0.36, s * 0.36, s * 0.32, s * 0.06)
    ctx.stroke()
    ctx.fillRect(s * 0.38, s * 0.42, s * 0.24, s * 0.06)
  },
  invoice: (ctx, s) => {
    roundRect(ctx, s * 0.3, s * 0.34, s * 0.4, s * 0.38, s * 0.04)
    ctx.fill()
    ctx.fillStyle = metaOf('invoice').color
    ctx.fillRect(s * 0.36, s * 0.44, s * 0.28, s * 0.04)
    ctx.fillStyle = 'rgba(255,255,255,0.95)'
  },
  payment: (ctx, s) => {
    ctx.beginPath()
    ctx.moveTo(s * 0.3, s * 0.5)
    ctx.lineTo(s * 0.7, s * 0.5)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(s * 0.58, s * 0.38)
    ctx.lineTo(s * 0.7, s * 0.5)
    ctx.lineTo(s * 0.58, s * 0.62)
    ctx.stroke()
  },
  budget: (ctx, s) => {
    ctx.beginPath()
    ctx.moveTo(s * 0.32, s * 0.62)
    ctx.lineTo(s * 0.42, s * 0.46)
    ctx.lineTo(s * 0.52, s * 0.54)
    ctx.lineTo(s * 0.68, s * 0.34)
    ctx.stroke()
  },
  project: (ctx, s) => {
    for (let i = 0; i < 3; i++) {
      ctx.fillRect(s * (0.32 + i * 0.12), s * (0.58 - i * 0.08), s * 0.1, s * (0.14 + i * 0.08))
    }
  },
  customer: (ctx, s) => {
    ctx.beginPath()
    ctx.arc(s * 0.42, s * 0.4, s * 0.08, 0, Math.PI * 2)
    ctx.arc(s * 0.58, s * 0.4, s * 0.08, 0, Math.PI * 2)
    ctx.fill()
    roundRect(ctx, s * 0.32, s * 0.52, s * 0.36, s * 0.18, s * 0.08)
    ctx.fill()
  },
  supplier: (ctx, s) => {
    roundRect(ctx, s * 0.3, s * 0.38, s * 0.4, s * 0.3, s * 0.05)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(s * 0.3, s * 0.5)
    ctx.lineTo(s * 0.7, s * 0.5)
    ctx.stroke()
  },
  inventory: (ctx, s) => {
    for (let r = 0; r < 2; r++) {
      for (let c = 0; c < 2; c++) {
        roundRect(ctx, s * (0.32 + c * 0.2), s * (0.36 + r * 0.2), s * 0.16, s * 0.16, s * 0.03)
        ctx.stroke()
      }
    }
  },
  maintenance: (ctx, s) => {
    ctx.beginPath()
    ctx.arc(s * 0.46, s * 0.46, s * 0.12, 0.2, Math.PI * 1.2)
    ctx.stroke()
    roundRect(ctx, s * 0.54, s * 0.54, s * 0.14, s * 0.06, s * 0.02)
    ctx.fill()
  },
  it: (ctx, s) => {
    ctx.font = `700 ${s * 0.28}px ${ICON_FONT}`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('IT', s * 0.5, s * 0.52)
  },
  permission: (ctx, s) => {
    roundRect(ctx, s * 0.38, s * 0.48, s * 0.24, s * 0.2, s * 0.04)
    ctx.fill()
    ctx.beginPath()
    ctx.arc(s * 0.5, s * 0.42, s * 0.1, Math.PI, 0)
    ctx.stroke()
  },
  report: (ctx, s) => {
    roundRect(ctx, s * 0.32, s * 0.34, s * 0.36, s * 0.4, s * 0.04)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(s * 0.38, s * 0.58)
    ctx.lineTo(s * 0.46, s * 0.48)
    ctx.lineTo(s * 0.54, s * 0.54)
    ctx.lineTo(s * 0.62, s * 0.42)
    ctx.stroke()
  },
  loan: (ctx, s) => {
    ctx.beginPath()
    ctx.arc(s * 0.5, s * 0.5, s * 0.18, 0, Math.PI * 2)
    ctx.stroke()
    ctx.font = `600 ${s * 0.22}px ${ICON_FONT}`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('借', s * 0.5, s * 0.52)
  },
  gift: (ctx, s) => {
    roundRect(ctx, s * 0.32, s * 0.44, s * 0.36, s * 0.24, s * 0.04)
    ctx.fill()
    ctx.fillRect(s * 0.46, s * 0.36, s * 0.08, s * 0.32)
  },
  training: (ctx, s) => {
    roundRect(ctx, s * 0.3, s * 0.4, s * 0.4, s * 0.28, s * 0.04)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(s * 0.42, s * 0.54)
    ctx.lineTo(s * 0.5, s * 0.48)
    ctx.lineTo(s * 0.58, s * 0.54)
    ctx.stroke()
  },
  safety: (ctx, s) => {
    ctx.beginPath()
    ctx.moveTo(s * 0.5, s * 0.32)
    ctx.lineTo(s * 0.68, s * 0.66)
    ctx.lineTo(s * 0.32, s * 0.66)
    ctx.closePath()
    ctx.stroke()
    ctx.fillRect(s * 0.47, s * 0.46, s * 0.06, s * 0.14)
  },
  quality: (ctx, s) => {
    ctx.beginPath()
    ctx.moveTo(s * 0.34, s * 0.52)
    ctx.lineTo(s * 0.46, s * 0.64)
    ctx.lineTo(s * 0.68, s * 0.38)
    ctx.stroke()
  },
  logistics: (ctx, s) => {
    roundRect(ctx, s * 0.28, s * 0.44, s * 0.44, s * 0.22, s * 0.05)
    ctx.fill()
    ctx.beginPath()
    ctx.moveTo(s * 0.28, s * 0.44)
    ctx.lineTo(s * 0.36, s * 0.34)
    ctx.lineTo(s * 0.64, s * 0.34)
    ctx.lineTo(s * 0.72, s * 0.44)
    ctx.stroke()
  },
  ship: (ctx, s) => {
    ctx.beginPath()
    ctx.moveTo(s * 0.28, s * 0.56)
    ctx.lineTo(s * 0.72, s * 0.56)
    ctx.lineTo(s * 0.66, s * 0.68)
    ctx.lineTo(s * 0.34, s * 0.68)
    ctx.closePath()
    ctx.fill()
    ctx.beginPath()
    ctx.moveTo(s * 0.5, s * 0.32)
    ctx.lineTo(s * 0.42, s * 0.56)
    ctx.lineTo(s * 0.58, s * 0.56)
    ctx.closePath()
    ctx.fill()
  },
  hr: (ctx, s) => {
    ctx.font = `700 ${s * 0.26}px ${ICON_FONT}`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('HR', s * 0.5, s * 0.52)
  },
  finance: (ctx, s) => {
    ctx.font = `600 ${s * 0.3}px ${ICON_FONT}`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('财', s * 0.5, s * 0.52)
  },
  admin: (ctx, s) => {
    roundRect(ctx, s * 0.32, s * 0.34, s * 0.36, s * 0.38, s * 0.04)
    ctx.stroke()
    ctx.fillRect(s * 0.38, s * 0.42, s * 0.08, s * 0.08)
    ctx.fillRect(s * 0.5, s * 0.42, s * 0.12, s * 0.08)
    ctx.fillRect(s * 0.38, s * 0.54, s * 0.24, s * 0.08)
  },
}

export function getProcessIconDataUrl(key: string, size = 72): string {
  const k = (PROCESS_ICON_CATALOG.some((m) => m.key === key) ? key : 'general') as ProcessIconKey
  const cacheKey = `${k}_${size}_hd${RENDER_SCALE}`
  const hit = cache.get(cacheKey)
  if (hit) return hit
  const canvas = document.createElement('canvas')
  const pixelSize = Math.round(size * RENDER_SCALE)
  canvas.width = pixelSize
  canvas.height = pixelSize
  const ctx = canvas.getContext('2d')
  if (!ctx) return ''
  ctx.scale(RENDER_SCALE, RENDER_SCALE)
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'
  const { color } = metaOf(k)
  drawBase(ctx, size, color)
  const draw = drawers[k] || drawers.general
  draw(ctx, size)
  const url = canvas.toDataURL('image/png')
  cache.set(cacheKey, url)
  return url
}
