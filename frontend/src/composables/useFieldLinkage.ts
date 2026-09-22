import type {
  FieldLinkageConfig,
  FieldLinkageRule,
  FieldShowWhenRule,
  FormFieldDef,
  FormSchema,
  FormSection,
} from '@/types/form'

export type { FieldLinkageConfig, FieldLinkageRule, FieldShowWhenRule }

/** 可作为联动源的控件类型 */
export const LINKAGE_SOURCE_TYPES = [
  'select',
  'radio',
  'switch',
  'multi_select',
  'checkbox_group',
] as const

export type LinkageSourceType = (typeof LINKAGE_SOURCE_TYPES)[number]

export interface LinkageVisibilityContext {
  fieldTargets: Map<string, FieldLinkageRule[]>
  sectionTargets: Map<string, FieldLinkageRule[]>
  fieldById: Map<string, FormFieldDef>
  fieldByKey: Map<string, FormFieldDef>
}

function normalizeOptionValue(raw: unknown): string {
  if (raw === true || raw === 'true' || raw === 1 || raw === '1') return '1'
  if (raw === false || raw === 'false' || raw === 0 || raw === '0') return '0'
  if (raw == null) return ''
  return String(raw)
}

function normalizeSelectedValues(raw: unknown, sourceType: string): string[] {
  if (sourceType === 'switch') {
    return [normalizeOptionValue(raw)]
  }
  if (Array.isArray(raw)) {
    return raw.map((v) => normalizeOptionValue(v)).filter(Boolean)
  }
  const one = normalizeOptionValue(raw)
  return one ? [one] : []
}

export function isLinkageSourceType(type: string): type is LinkageSourceType {
  return (LINKAGE_SOURCE_TYPES as readonly string[]).includes(type)
}

export function getFieldLinkage(field: FormFieldDef | undefined): FieldLinkageConfig | null {
  if (!field?.props?.linkage) return null
  const raw = field.props.linkage as FieldLinkageConfig
  if (!raw?.rules?.length) return null
  return raw
}

export function getFieldShowWhen(
  field: FormFieldDef | FormSection,
): FieldShowWhenRule | FieldShowWhenRule[] | undefined {
  return (field as FormFieldDef & FormSection).showWhen
}

function ruleMatchesValue(
  rule: FieldLinkageRule,
  selected: string[],
  sourceType: string,
): boolean {
  const target = normalizeOptionValue(rule.optionValue)
  if (!target) return false
  if (!selected.length) return false
  if (sourceType === 'multi_select' || sourceType === 'checkbox_group') {
    return selected.includes(target)
  }
  return selected[0] === target
}

export function buildLinkageContext(schema: FormSchema): LinkageVisibilityContext {
  const fieldTargets = new Map<string, FieldLinkageRule[]>()
  const sectionTargets = new Map<string, FieldLinkageRule[]>()
  const fieldById = new Map<string, FormFieldDef>()
  const fieldByKey = new Map<string, FormFieldDef>()

  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      fieldById.set(field.id, field)
      if (field.key) fieldByKey.set(field.key, field)
      const linkage = getFieldLinkage(field)
      if (!linkage) continue
      for (const rule of linkage.rules) {
        for (const fid of rule.showFieldIds || []) {
          const list = fieldTargets.get(fid) || []
          list.push(rule)
          fieldTargets.set(fid, list)
        }
        for (const sid of rule.showSectionIds || []) {
          const list = sectionTargets.get(sid) || []
          list.push(rule)
          sectionTargets.set(sid, list)
        }
      }
    }
  }

  return { fieldTargets, sectionTargets, fieldById, fieldByKey }
}

function evaluateShowWhenRules(
  rules: FieldShowWhenRule[],
  logic: 'and' | 'or',
  model: Record<string, unknown>,
  fieldByKey: Map<string, FormFieldDef>,
): boolean {
  const results = rules.map((rule) => {
    const source = fieldByKey.get(rule.fieldKey)
    if (!source?.key) return false
    const selected = normalizeSelectedValues(model[source.key], source.type)
    const want = (rule.values || []).map((v) => normalizeOptionValue(v)).filter(Boolean)
    if (!want.length) return true
    const match = rule.match || 'any'
    if (match === 'all') {
      return want.every((w) => selected.includes(w))
    }
    return want.some((w) => selected.includes(w))
  })
  return logic === 'and' ? results.every(Boolean) : results.some(Boolean)
}

function evaluateLinkageTargetSimple(
  targetRules: FieldLinkageRule[],
  schema: FormSchema,
  model: Record<string, unknown>,
): boolean {
  for (const sec of schema.sections || []) {
    for (const source of sec.fields || []) {
      const linkage = getFieldLinkage(source)
      if (!source.key || !linkage) continue
      const selected = normalizeSelectedValues(model[source.key], source.type)
      for (const r of linkage.rules) {
        if (!targetRules.includes(r)) continue
        if (ruleMatchesValue(r, selected, source.type)) return true
      }
    }
  }
  return false
}

export function shouldDisplayField(
  field: FormFieldDef,
  schema: FormSchema,
  model: Record<string, unknown>,
  ctx?: LinkageVisibilityContext,
  extra?: { printMode?: boolean; fieldPerm?: 'hidden' | 'read' | 'edit' },
): boolean {
  if (field.visible === false) return false
  if (extra?.printMode && field.printable === false) return false
  if (extra?.fieldPerm === 'hidden') return false

  const context = ctx || buildLinkageContext(schema)

  const showWhen = getFieldShowWhen(field)
  if (showWhen) {
    const rules = Array.isArray(showWhen) ? showWhen : [showWhen]
    const logic = field.showWhenLogic || 'or'
    if (!evaluateShowWhenRules(rules, logic, model, context.fieldByKey)) return false
  }

  const targetRules = context.fieldTargets.get(field.id)
  if (targetRules?.length) {
    if (!evaluateLinkageTargetSimple(targetRules, schema, model)) return false
  }

  return true
}

export function shouldDisplaySection(
  section: FormSection,
  schema: FormSchema,
  model: Record<string, unknown>,
  ctx?: LinkageVisibilityContext,
): boolean {
  const context = ctx || buildLinkageContext(schema)

  const showWhen = getFieldShowWhen(section)
  if (showWhen) {
    const rules = Array.isArray(showWhen) ? showWhen : [showWhen]
    const logic = section.showWhenLogic || 'or'
    if (!evaluateShowWhenRules(rules, logic, model, context.fieldByKey)) return false
  }

  const targetRules = context.sectionTargets.get(section.id)
  if (targetRules?.length) {
    if (!evaluateLinkageTargetSimple(targetRules, schema, model)) return false
  }

  return true
}

/** 设计器：该控件是否被某联动规则引用为显示目标 */
export function isLinkageTargetField(fieldId: string, schema: FormSchema): boolean {
  const ctx = buildLinkageContext(schema)
  return ctx.fieldTargets.has(fieldId)
}

export function listAllFields(schema: FormSchema): Array<FormFieldDef & { sectionId: string; sectionTitle: string }> {
  const out: Array<FormFieldDef & { sectionId: string; sectionTitle: string }> = []
  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (!field.key && !['section_title', 'text_block', 'divider'].includes(field.type)) continue
      out.push({
        ...field,
        sectionId: sec.id,
        sectionTitle: sec.title || '',
      })
    }
  }
  return out
}

export function clearHiddenFieldValues(
  schema: FormSchema,
  model: Record<string, unknown>,
  ctx?: LinkageVisibilityContext,
) {
  const context = ctx || buildLinkageContext(schema)
  for (const sec of schema.sections || []) {
    if (!shouldDisplaySection(sec, schema, model, context)) {
      for (const field of sec.fields || []) {
        if (field.key) delete model[field.key]
      }
      continue
    }
    for (const field of sec.fields || []) {
      if (!field.key) continue
      if (!shouldDisplayField(field, schema, model, context)) {
        delete model[field.key]
      }
    }
  }
}
