/**
 * 将 pdfjs-dist 的 CMap / 标准字体复制到 public，供中文 PDF 正确渲染。
 */
import { cpSync, existsSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const pkgRoot = join(root, 'node_modules', 'pdfjs-dist')
const outRoot = join(root, 'public', 'pdfjs')

if (!existsSync(pkgRoot)) {
  console.warn('[copy-pdfjs-assets] pdfjs-dist 未安装，跳过')
  process.exit(0)
}

mkdirSync(outRoot, { recursive: true })
for (const dir of ['cmaps', 'standard_fonts']) {
  const src = join(pkgRoot, dir)
  const dest = join(outRoot, dir)
  if (!existsSync(src)) {
    console.warn(`[copy-pdfjs-assets] 缺少 ${dir}，跳过`)
    continue
  }
  cpSync(src, dest, { recursive: true, force: true })
}

console.log('[copy-pdfjs-assets] 已同步到 public/pdfjs')
