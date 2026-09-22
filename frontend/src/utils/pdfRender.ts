import * as pdfjsLib from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { api } from '@/api/client'

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl

const PDFJS_ASSET_BASE = `${import.meta.env.BASE_URL}pdfjs/`

function pdfDocumentOptions(data: ArrayBuffer | Uint8Array) {
  return {
    data,
    cMapUrl: `${PDFJS_ASSET_BASE}cmaps/`,
    cMapPacked: true,
    standardFontDataUrl: `${PDFJS_ASSET_BASE}standard_fonts/`,
    useSystemFonts: true,
    disableFontFace: false,
  }
}

const cache = new Map<string, Promise<string[]>>()

/** 规范化 URL 路径中的中文等非 ASCII 字符，避免 Chrome 请求失败 */
function encodeUrlPath(url: string): string {
  if (!url) return url
  try {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      const u = new URL(url)
      u.pathname = u.pathname
        .split('/')
        .map((seg) => (seg ? encodeURIComponent(decodeURIComponent(seg)) : seg))
        .join('/')
      return u.toString()
    }
    return url
      .split('/')
      .map((seg) => (seg ? encodeURIComponent(decodeURIComponent(seg)) : seg))
      .join('/')
  } catch {
    return url
  }
}

/** 经 axios 带登录态下载 PDF，避免 pdf.js Worker 在 Chrome 中无法携带 Cookie */
async function loadPdfBytes(url: string): Promise<ArrayBuffer> {
  const encoded = encodeUrlPath(url)

  if (encoded.startsWith('http://') || encoded.startsWith('https://')) {
    const origin = window.location.origin
    if (encoded.startsWith(origin)) {
      const apiPath = new URL(encoded).pathname.replace(/^\/api\/v1/, '')
      const res = await api.get<ArrayBuffer>(apiPath, { responseType: 'arraybuffer' })
      return res.data
    }
    const res = await fetch(encoded, { credentials: 'include' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.arrayBuffer()
  }

  const apiPath = encoded.replace(/^\/api\/v1/, '')
  const res = await api.get<ArrayBuffer>(apiPath, { responseType: 'arraybuffer' })
  return res.data
}

/** 将 PDF 渲染为 JPEG 图片 data URL 列表，供打印预览与输出使用 */
export function renderPdfToImages(url: string, scale = 1.8): Promise<string[]> {
  const key = `${url}@${scale}`
  const hit = cache.get(key)
  if (hit) return hit

  const task = (async () => {
    const data = await loadPdfBytes(url)
    const doc = await pdfjsLib.getDocument(pdfDocumentOptions(data)).promise
    const images: string[] = []
    for (let pageNum = 1; pageNum <= doc.numPages; pageNum++) {
      const page = await doc.getPage(pageNum)
      const viewport = page.getViewport({ scale })
      const canvas = document.createElement('canvas')
      canvas.width = Math.floor(viewport.width)
      canvas.height = Math.floor(viewport.height)
      const ctx = canvas.getContext('2d')
      if (!ctx) continue
      await page.render({ canvasContext: ctx, viewport, canvas }).promise
      images.push(canvas.toDataURL('image/jpeg', 0.92))
    }
    return images
  })()

  cache.set(key, task)
  task.catch(() => cache.delete(key))
  return task
}

export { encodeUrlPath }
