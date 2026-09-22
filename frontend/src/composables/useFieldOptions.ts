import { ref } from 'vue'
import { api, type ApiResponse } from '@/api/client'
import type { FormFieldDef } from '@/types/form'

export interface FieldOptionItem {
  id?: number
  code?: string
  name?: string
  label: string
  value: string
}

const setListCache = ref<{ code: string; name: string; id: number }[] | null>(null)
const itemsCache = new Map<string, FieldOptionItem[]>()

export function formatOptionLabel(name: string, code: string) {
  const n = (name || '').trim()
  const c = (code || '').trim()
  if (n && c) return `${n}（${c}）`
  return n || c
}

export function normalizeManualOption(raw: {
  id?: number
  label?: string
  value?: string
  name?: string
  code?: string
}): FieldOptionItem {
  const name = (raw.name || raw.label || '').trim()
  const code = (raw.code || raw.value || name).trim()
  return {
    id: raw.id,
    name,
    code,
    label: formatOptionLabel(name, code),
    value: code,
  }
}

/** 将 select / radio 等存值解析为展示文本（兼容 code 与配置表项 id） */
export function resolveOptionLabel(val: unknown, opts: FieldOptionItem[]): string {
  if (val === undefined || val === null || val === '') return '—'

  const pickOne = (v: unknown): string => {
    const text = String(v).trim()
    if (!text) return '—'
    const num = Number(v)
    const hit = opts.find((o) => {
      if (o.value === text || o.value === v) return true
      if (o.code != null && String(o.code) === text) return true
      if (o.id != null && Number.isFinite(num) && o.id === num) return true
      return false
    })
    if (hit?.label) return hit.label
    if (hit?.name) return formatOptionLabel(hit.name, hit.code || hit.value)
    return text
  }

  if (Array.isArray(val)) {
    const parts = val.map(pickOne).filter((x) => x !== '—')
    return parts.length ? parts.join('、') : '—'
  }
  return pickOne(val)
}

export async function loadOptionSetList(force = false) {
  if (setListCache.value && !force) return setListCache.value
  const res = await api.get<ApiResponse<{ id: number; code: string; name: string }[]>>('/option-sets', {
    params: { set_type: 'option' },
  })
  if (res.data.ok) {
    setListCache.value = res.data.data
    return res.data.data
  }
  return []
}

export async function loadOptionsBySetCode(code: string, force = false): Promise<FieldOptionItem[]> {
  const key = code.trim()
  if (!key) return []
  if (!force && itemsCache.has(key)) return itemsCache.get(key)!
  const res = await api.get<ApiResponse<FieldOptionItem[]>>(`/option-sets/${encodeURIComponent(key)}/options`)
  if (res.data.ok) {
    itemsCache.set(key, res.data.data)
    return res.data.data
  }
  return []
}

export function fieldOptionsToSelectOpts(items: FieldOptionItem[]): { label: string; value: string }[] {
  return items.map((o) => ({
    label: o.label || formatOptionLabel(o.name || '', o.code || o.value),
    value: String(o.value || o.code || ''),
  }))
}

export async function resolveFieldOptions(field: FormFieldDef): Promise<FieldOptionItem[]> {
  const props = field.props || {}
  const code = String(props.optionSetCode || '').trim()
  const useSet = props.optionSource === 'option_set' || !!code
  if (useSet && code) {
    return loadOptionsBySetCode(code)
  }
  const rows = (props.options as FieldOptionItem[]) || []
  return rows.map((o) => normalizeManualOption(o))
}

export function clearOptionSetCache() {
  setListCache.value = null
  itemsCache.clear()
}
