import { api, type ApiResponse } from '@/api/client'

export interface FormFillerContext {
  userId?: number
  primaryDepartmentId?: number
  departmentIds: number[]
}

/** 填表人上下文：当前用户、主部门及任职部门列表 */
export async function loadFormFillerContext(companyId?: number): Promise<FormFillerContext> {
  const ctx: FormFillerContext = { departmentIds: [] }
  try {
    const meRes = await api.get<ApiResponse<{ id: number }>>('/auth/me')
    if (meRes.data.ok) ctx.userId = meRes.data.data.id
  } catch {
    return ctx
  }
  if (!companyId) return ctx
  try {
    const dRes = await api.get<
      ApiResponse<{ department_id: number; is_primary?: boolean }[]>
    >('/org/my-departments', { params: { company_id: companyId } })
    if (!dRes.data.ok) return ctx
    const rows = dRes.data.data || []
    ctx.departmentIds = rows.map((r) => r.department_id)
    const primary = rows.find((r) => r.is_primary)
    ctx.primaryDepartmentId = primary?.department_id ?? rows[0]?.department_id
  } catch {
    /* ignore */
  }
  return ctx
}
