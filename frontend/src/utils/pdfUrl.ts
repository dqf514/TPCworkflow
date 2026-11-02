/**
 * PDF 相关 URL 处理。
 *
 * 单独成文件，避免引用方为了一个 URL 工具函数把 pdfjs-dist（约 800KB）
 * 静态打进首屏 bundle。真正的渲染逻辑在 utils/pdfRender.ts，走动态 import。
 */

/** 规范化 URL 路径中的中文等非 ASCII 字符，避免 Chrome 请求失败 */
export function encodeUrlPath(url: string): string {
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
