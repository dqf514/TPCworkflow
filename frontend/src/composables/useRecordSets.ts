import { ref } from 'vue'
import { api, type ApiResponse } from '@/api/client'

export interface RecordSetColumn {
  field_key: string
  label: string
  sort_order?: number
  /** 24 栅格宽度，与表单设计器一致；默认 24 独占一行 */
  span?: number
}

export interface RecordSetRow {
  row_code: string
  data: Record<string, string>
  label?: string
  value?: string
  source?: 'company' | 'personal'
  owner_user_id?: number
}

export type RecordSetDataScope = 'mixed' | 'company' | 'personal'

export interface RecordSetPayload {
  code: string
  name: string
  data_scope?: RecordSetDataScope
  columns: RecordSetColumn[]
  records: RecordSetRow[]
}

export interface RecordSetValue {
  row_code: string
  data: Record<string, string>
  source?: 'company' | 'personal' | 'custom'
}

export interface RecordSetLoadOptions {
  includeCompany?: boolean
  includePersonal?: boolean
  force?: boolean
}

const listCache = ref<{ id: number; code: string; name: string }[] | null>(null)
const payloadCache = new Map<string, RecordSetPayload>()

function cacheKey(code: string, opts?: RecordSetLoadOptions) {
  const c = opts?.includeCompany !== false ? '1' : '0'
  const p = opts?.includePersonal !== false ? '1' : '0'
  return `${code}|${c}|${p}`
}

export async function loadRecordSetList(force = false) {
  if (listCache.value && !force) return listCache.value
  const res = await api.get<ApiResponse<{ id: number; code: string; name: string }[]>>(
    '/option-sets',
    { params: { set_type: 'record' } },
  )
  if (res.data.ok) {
    listCache.value = res.data.data
    return res.data.data
  }
  return []
}

export async function loadRecordSetPayload(
  code: string,
  opts?: RecordSetLoadOptions,
): Promise<RecordSetPayload | null> {
  const key = code.trim()
  if (!key) return null
  const ck = cacheKey(key, opts)
  if (!opts?.force && payloadCache.has(ck)) return payloadCache.get(ck)!
  const includeCompany = opts?.includeCompany !== false
  const includePersonal = opts?.includePersonal !== false
  const res = await api.get<ApiResponse<RecordSetPayload>>(
    `/option-sets/${encodeURIComponent(key)}/records`,
    {
      params: {
        include_company: includeCompany ? '1' : '0',
        include_personal: includePersonal ? '1' : '0',
      },
    },
  )
  if (res.data.ok) {
    payloadCache.set(ck, res.data.data)
    return res.data.data
  }
  return null
}

export function recordDisplayLabel(
  row: RecordSetRow,
  columns: RecordSetColumn[],
  labelField?: string,
): string {
  const data = row.data || {}
  if (labelField && data[labelField]) return String(data[labelField])
  for (const c of columns) {
    const v = data[c.field_key]
    if (v) return String(v)
  }
  return row.row_code
}

export function formatRecordSetValueForPrint(
  val: unknown,
  columns?: RecordSetColumn[],
): string {
  if (!val || typeof val !== 'object') return '—'
  const v = val as RecordSetValue
  const data = v.data || {}
  const cols = columns || []
  if (!cols.length) {
    return Object.entries(data)
      .map(([k, val]) => `${k}: ${val}`)
      .join('；') || '—'
  }
  return cols
    .map((c) => {
      const text = data[c.field_key]
      if (!text) return ''
      return `${c.label}: ${text}`
    })
    .filter(Boolean)
    .join('；') || '—'
}

export function clearRecordSetCache() {
  listCache.value = null
  payloadCache.clear()
}

export interface MyRecordSetOverview {
  id: number
  code: string
  name: string
  description: string
  data_scope?: RecordSetDataScope
  personal_count: number
}

export async function loadMyRecordSetsOverview() {
  const res = await api.get<ApiResponse<MyRecordSetOverview[]>>('/me/record-sets')
  return res.data.ok ? res.data.data : []
}

export async function loadMyRecordSetDetail(code: string) {
  const res = await api.get<ApiResponse<RecordSetPayload>>(
    `/me/record-sets/${encodeURIComponent(code)}`,
  )
  return res.data.ok ? res.data.data : null
}

export async function saveMyRecord(code: string, row: { row_code?: string; data: Record<string, string> }) {
  if (row.row_code) {
    const res = await api.put<ApiResponse<RecordSetRow>>(
      `/me/record-sets/${encodeURIComponent(code)}/records/${encodeURIComponent(row.row_code)}`,
      { data: row.data },
    )
    return res.data
  }
  const res = await api.post<ApiResponse<RecordSetRow>>(
    `/me/record-sets/${encodeURIComponent(code)}/records`,
    { data: row.data },
  )
  return res.data
}

export async function deleteMyRecord(code: string, rowCode: string) {
  return api.delete<ApiResponse<unknown>>(
    `/me/record-sets/${encodeURIComponent(code)}/records/${encodeURIComponent(rowCode)}`,
  )
}
