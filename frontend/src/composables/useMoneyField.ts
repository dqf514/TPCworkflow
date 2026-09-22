import { ref } from 'vue'
import { api, type ApiResponse } from '@/api/client'

export const BASE_CURRENCY = 'CNY'

export interface MoneyValue {
  currency: string
  amount: number | null
  exchange_rate: number
  rmb_amount: number | null
}

export interface ExchangeRateRow {
  currency_code: string
  currency_name: string
  rate_to_cny: number
}

const ratesCache = ref<ExchangeRateRow[] | null>(null)
const rateMap = ref<Record<string, number>>({ [BASE_CURRENCY]: 1 })

export function createEmptyMoney(currency = BASE_CURRENCY, rate = 1): MoneyValue {
  return {
    currency,
    amount: null,
    exchange_rate: rate,
    rmb_amount: null,
  }
}

export function calcRmbAmount(amount: number | null | undefined, rate: number): number | null {
  if (amount == null || amount === '' || Number.isNaN(Number(amount))) return null
  const n = Number(amount)
  const r = Number(rate)
  if (Number.isNaN(n) || Number.isNaN(r)) return null
  return Math.round(n * r * 100) / 100
}

export function normalizeMoneyValue(raw: unknown, defaultRate?: number): MoneyValue {
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    const o = raw as Record<string, unknown>
    const currency = String(o.currency || BASE_CURRENCY).toUpperCase()
    const rate =
      o.exchange_rate != null && o.exchange_rate !== ''
        ? Number(o.exchange_rate)
        : (defaultRate ?? rateMap.value[currency] ?? 1)
    const amount =
      o.amount == null || o.amount === '' ? null : Number(o.amount)
    const rmb =
      o.rmb_amount != null && o.rmb_amount !== ''
        ? Number(o.rmb_amount)
        : calcRmbAmount(amount, rate)
    return {
      currency,
      amount: Number.isNaN(amount as number) ? null : amount,
      exchange_rate: Number.isNaN(rate) ? 1 : rate,
      rmb_amount: rmb == null || Number.isNaN(rmb) ? null : rmb,
    }
  }
  if (typeof raw === 'number' && !Number.isNaN(raw)) {
    return {
      currency: BASE_CURRENCY,
      amount: raw,
      exchange_rate: 1,
      rmb_amount: raw,
    }
  }
  return createEmptyMoney()
}

export function getPlainAmountNumber(raw: unknown): number {
  if (raw == null || raw === '') return 0
  if (typeof raw === 'number' && !Number.isNaN(raw)) return raw
  const n = Number(String(raw).replace(/,/g, ''))
  return Number.isNaN(n) ? 0 : n
}

export function getAmountColumnTotal(raw: unknown, fieldType?: string): number {
  if (fieldType === 'money') return getMoneyRmbTotal(raw)
  if (fieldType === 'plain_amount') return getPlainAmountNumber(raw)
  return getPlainAmountNumber(raw)
}

/** 明细/打印中参与底部汇总的金额类控件 */
export const AMOUNT_SUMMARY_FIELD_TYPES = ['money', 'plain_amount'] as const

export function isAmountSummaryFieldType(type: string | undefined): boolean {
  return (AMOUNT_SUMMARY_FIELD_TYPES as readonly string[]).includes(type || '')
}

export function getMoneyRmbTotal(raw: unknown): number {
  const m = normalizeMoneyValue(raw)
  if (m.rmb_amount != null && !Number.isNaN(m.rmb_amount)) return m.rmb_amount
  const calc = calcRmbAmount(m.amount, m.exchange_rate)
  return calc ?? 0
}

export function applyMoneyPatch(
  current: MoneyValue,
  patch: Partial<MoneyValue>,
): MoneyValue {
  const next = { ...current, ...patch }
  if (patch.currency && patch.currency !== current.currency) {
    const code = patch.currency.toUpperCase()
    next.exchange_rate = rateMap.value[code] ?? (code === BASE_CURRENCY ? 1 : next.exchange_rate)
  }
  if (patch.amount !== undefined || patch.exchange_rate !== undefined || patch.currency !== undefined) {
    next.rmb_amount = calcRmbAmount(next.amount, next.exchange_rate)
  }
  return next
}

export async function loadExchangeRates(force = false) {
  if (ratesCache.value && !force) return ratesCache.value
  const res = await api.get<ApiResponse<ExchangeRateRow[]>>('/exchange-rates')
  if (res.data.ok) {
    ratesCache.value = res.data.data
    const map: Record<string, number> = { [BASE_CURRENCY]: 1 }
    for (const r of res.data.data) {
      map[r.currency_code] = r.rate_to_cny
    }
    rateMap.value = map
    return res.data.data
  }
  return []
}

export function getRateForCurrency(code: string) {
  const c = (code || BASE_CURRENCY).toUpperCase()
  return rateMap.value[c] ?? 1
}

/** 与系统汇率的相对偏差比例（0~∞），系统汇率为 0 时若与用户值不同则视为 100% 偏差 */
export function exchangeRateDeviationRatio(userRate: number, systemRate: number): number {
  if (Number.isNaN(userRate) || Number.isNaN(systemRate)) return 0
  if (!systemRate || systemRate <= 0) {
    return userRate === systemRate ? 0 : 1
  }
  return Math.abs(userRate - systemRate) / systemRate
}

export const EXCHANGE_RATE_CONFIRM_THRESHOLD = 0.2

export function exchangeRateExceedsThreshold(
  userRate: number,
  systemRate: number,
  threshold = EXCHANGE_RATE_CONFIRM_THRESHOLD,
): boolean {
  return exchangeRateDeviationRatio(userRate, systemRate) > threshold
}

export function clearExchangeRateCache() {
  ratesCache.value = null
  rateMap.value = { [BASE_CURRENCY]: 1 }
}

export function currencyOptions(rates: ExchangeRateRow[]) {
  return rates.map((r) => ({
    label: `${r.currency_name}（${r.currency_code}）`,
    value: r.currency_code,
  }))
}
