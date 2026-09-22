import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type ApiResponse } from '@/api/client'

export interface Membership {
  id: number
  company_id: number
  company_name: string | null
  department_id: number
  department_name: string | null
  is_primary: boolean
  job_title: string | null
}

export interface UserProfile {
  id: number
  username: string
  display_name: string
  email: string | null
  phone: string | null
  job_title: string | null
  locale: string
  is_system_admin: boolean
  is_sector_admin?: boolean
  is_global_admin?: boolean
  sector_ids?: number[]
  can_design_workflow?: boolean
  can_view_instances?: boolean
  can_export_instances?: boolean
  has_password?: boolean
  need_set_password?: boolean
  avatar_path?: string | null
  avatar_url?: string | null
  memberships: Membership[]
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserProfile | null>(null)
  const loaded = ref(false)

  async function fetchMe() {
    try {
      const res = await api.get<ApiResponse<UserProfile>>('/auth/me')
      if (res.data.ok) user.value = res.data.data
    } catch {
      user.value = null
    } finally {
      loaded.value = true
    }
  }

  async function login(
    username: string,
    password: string,
    remember = false,
    captcha?: { captcha_id: string; captcha_code: string },
  ) {
    const res = await api.post<ApiResponse<UserProfile>>('/auth/login', {
      mode: 'password',
      username,
      identifier: username,
      password,
      remember,
      ...captcha,
    })
    if (!res.data.ok) throw new Error(res.data.message)
    user.value = res.data.data
  }

  async function updateProfile(body: { display_name?: string; phone?: string; locale?: string }) {
    const res = await api.patch<ApiResponse<UserProfile>>('/auth/me', body)
    if (!res.data.ok) throw new Error(res.data.message)
    user.value = res.data.data
  }

  async function changePassword(body: { old_password?: string; new_password: string }) {
    const res = await api.put<ApiResponse<UserProfile>>('/auth/password', body)
    if (!res.data.ok) throw new Error(res.data.message)
    user.value = res.data.data
  }

  async function logout() {
    await api.post('/auth/logout')
    user.value = null
  }

  return { user, loaded, fetchMe, login, logout, updateProfile, changePassword }
})
