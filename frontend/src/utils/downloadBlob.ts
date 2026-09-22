/** 从 Content-Disposition 响应头解析下载文件名 */
export function parseContentDispositionFilename(header?: string | null): string | null {
  if (!header) return null
  const utf8 = /filename\*=UTF-8''([^;\n]+)/i.exec(header)
  if (utf8?.[1]) {
    try {
      return decodeURIComponent(utf8[1].trim())
    } catch {
      return utf8[1].trim()
    }
  }
  const quoted = /filename="([^"]+)"/i.exec(header)
  if (quoted?.[1]) return quoted[1]
  const plain = /filename=([^;\n]+)/i.exec(header)
  return plain?.[1]?.trim() || null
}

/** 触发浏览器下载 Blob */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
