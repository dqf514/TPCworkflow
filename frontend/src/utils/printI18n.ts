import { i18n } from '@/plugins/i18n'

export function isPrintLocaleEn(): boolean {
  return String(i18n.global.locale.value).startsWith('en')
}

export function printT(key: string, params?: Record<string, unknown>): string {
  return String(i18n.global.t(key, params ?? {}))
}

export function printNumberLocale(): string {
  return isPrintLocaleEn() ? 'en-US' : 'zh-CN'
}

export function printListJoin(items: string[]): string {
  return items.join(isPrintLocaleEn() ? ', ' : '、')
}

export function printAttachmentListJoin(items: string[]): string {
  return items.join(isPrintLocaleEn() ? '; ' : '；')
}
