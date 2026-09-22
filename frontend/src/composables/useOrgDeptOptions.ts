import { api, type ApiResponse } from '@/api/client'
import type { FormSchema } from '@/types/form'

export interface DeptTreeNode {
  id: number
  name: string
  children?: DeptTreeNode[]
}

/** 将组织树扁平为下拉选项 */
export function flattenDeptTree(
  nodes: DeptTreeNode[],
  prefix = '',
): { label: string; value: number }[] {
  const out: { label: string; value: number }[] = []
  for (const n of nodes) {
    const label = prefix ? `${prefix} / ${n.name}` : n.name
    out.push({ label, value: n.id })
    if (n.children?.length) {
      out.push(...flattenDeptTree(n.children, label))
    }
  }
  return out
}

export async function loadCompanyDeptOptions(companyId: number) {
  const res = await api.get<ApiResponse<{ tree: DeptTreeNode[] }>>(
    `/org/companies/${companyId}/structure`,
  )
  if (!res.data.ok) return []
  return flattenDeptTree(res.data.data.tree || [])
}

/** 补全表单中已保存、但不在公司树选项里的部门 ID（跨部门历史数据等） */
export async function resolveDepartmentLabels(
  ids: number[],
): Promise<{ label: string; value: number }[]> {
  const uniq = [...new Set(ids.filter((id) => id > 0))]
  if (!uniq.length) return []
  const res = await api.get<ApiResponse<Record<string, string>>>('/org/departments/resolve', {
    params: { ids: uniq.join(',') },
  })
  if (!res.data.ok) return []
  const map = res.data.data || {}
  return uniq.map((id) => ({
    value: id,
    label: map[String(id)] || `部门 #${id}`,
  }))
}

export function collectDeptIdsFromModel(schema: FormSchema, model: Record<string, unknown>): number[] {
  const ids: number[] = []
  const push = (v: unknown) => {
    if (v == null || v === '') return
    if (Array.isArray(v)) v.forEach(push)
    else ids.push(Number(v))
  }
  for (const sec of schema.sections || []) {
    for (const field of sec.fields || []) {
      if (field.type === 'dept_picker' && field.key) push(model[field.key])
      if (field.type === 'detail' && field.key) {
        const rows = model[field.key]
        if (!Array.isArray(rows)) continue
        for (const row of rows) {
          if (!row || typeof row !== 'object') continue
          for (const col of field.props?.columns || []) {
            if (col.type === 'dept_picker' && col.key) push((row as Record<string, unknown>)[col.key])
          }
        }
      }
    }
  }
  return ids.filter((id) => !Number.isNaN(id) && id > 0)
}
