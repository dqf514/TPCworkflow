import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import { normalizeMoneyValue } from '@/composables/useMoneyField'
import { normalizeConditionScalar } from '@/utils/conditionFieldMeta'

/** 将表单字段值转为条件比较用的标量（金额优先取人民币折算值） */
export function normalizeFormValueForCondition(val: unknown): unknown {
  if (val === null || val === undefined || val === '') return val
  if (typeof val === 'boolean') return val
  if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
    const o = val as Record<string, unknown>
    if ('amount' in o || 'rmb_amount' in o || 'currency' in o) {
      const normalized = normalizeMoneyValue(val)
      if (normalized.rmb_amount != null && !Number.isNaN(normalized.rmb_amount)) {
        return normalized.rmb_amount
      }
      if (normalized.amount != null && !Number.isNaN(normalized.amount)) {
        return normalized.amount
      }
      return null
    }
    return val
  }
  return normalizeConditionScalar(val)
}

/** 构建流程条件评估用的 variables（与后端 variables.form 对齐） */
export function buildPreviewFormVariables(
  formData: Record<string, unknown> | undefined | null,
): Record<string, unknown> {
  const raw = formData ?? {}
  const form: Record<string, unknown> = {}
  for (const [key, val] of Object.entries(raw)) {
    form[key] = normalizeFormValueForCondition(val)
  }
  return { form }
}

/**
 * 填表时根据 formData 构建可响应的条件变量。
 * 通过 JSON.stringify 触达全部字段，避免 props 浅层传递导致预览不刷新。
 */
export function useFormPreviewVariables(
  formData: MaybeRefOrGetter<Record<string, unknown> | undefined>,
) {
  return computed(() => {
    const raw = toValue(formData)
    JSON.stringify(raw ?? {})
    return buildPreviewFormVariables(raw)
  })
}
