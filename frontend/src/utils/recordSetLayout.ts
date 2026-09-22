import type { RecordSetColumn } from '@/composables/useRecordSets'

export const RECORD_SET_GRID_TOTAL = 24

export function normalizeRecordSetColumnSpan(raw: unknown): number {
  const n = Number(raw)
  if (!Number.isFinite(n)) return RECORD_SET_GRID_TOTAL
  let v = Math.max(6, Math.min(RECORD_SET_GRID_TOTAL, Math.round(n)))
  if (v % 2) v -= 1
  return Math.max(6, v)
}

export function recordSetColumnSpan(
  col: RecordSetColumn,
  device: 'desktop' | 'mobile' = 'desktop',
): number {
  if (device === 'mobile') return RECORD_SET_GRID_TOTAL
  return normalizeRecordSetColumnSpan(col.span ?? RECORD_SET_GRID_TOTAL)
}
