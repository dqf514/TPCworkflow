import type { FormSchema } from '@/types/form'
import { applyFormFormulas } from '@/utils/formFormula'

export { applyFormFormulas, evaluateFormFormula, formatFormulaResult, collectFormulaRefOptions } from '@/utils/formFormula'

export function syncFormFormulas(schema: FormSchema, model: Record<string, unknown>): void {
  applyFormFormulas(schema, model)
}
