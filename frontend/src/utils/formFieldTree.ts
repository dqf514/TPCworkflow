import type { FormFieldDef, FormSchema } from '@/types/form'

export interface FormFieldTreeRow {
  key: string
  label: string
  type?: string
  indent: number
  parentKey?: string
}

/** 扁平化表单字段（含明细列），供流程节点权限表使用 */
export function flattenFormFieldsForPermissions(schema: FormSchema | undefined): FormFieldTreeRow[] {
  if (!schema?.sections?.length) return []
  const rows: FormFieldTreeRow[] = []
  for (const sec of schema.sections) {
    for (const field of sec.fields || []) {
      if (!field.key && !['detail'].includes(field.type)) continue
      if (field.type === 'detail') {
        if (field.key) {
          rows.push({ key: field.key, label: field.label || field.key, type: field.type, indent: 0 })
        }
        for (const col of (field.props?.columns as FormFieldDef[]) || []) {
          if (!col.key) continue
          rows.push({
            key: col.key,
            label: `${field.label || field.key} · ${col.label || col.key}`,
            type: col.type,
            indent: 1,
            parentKey: field.key,
          })
        }
        continue
      }
      if (!field.key) continue
      if (['divider', 'text_block', 'section_title'].includes(field.type)) continue
      rows.push({ key: field.key, label: field.label || field.key, type: field.type, indent: 0 })
    }
  }
  return rows
}
