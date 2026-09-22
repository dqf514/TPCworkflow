import axios from 'axios'

import { FRONTEND_UPLOAD_MAX_MB } from '@/utils/attachmentUpload'

import {
  resetSessionRedirectFlag,
  scheduleSessionExpiredRedirect,
  shouldRedirectOn401,
} from '@/utils/sessionRedirect'



export const api = axios.create({

  baseURL: '/api/v1',

  withCredentials: true,

  timeout: 30000,

})



api.interceptors.response.use(

  (res) => {

    resetSessionRedirectFlag()

    return res

  },

  async (err) => {

    if (err.response?.status === 401) {

      const url = String(err.config?.url || '')

      // 登录/验证码等认证接口也会返回 401（如账号密码错误），不应当成会话过期
      if (shouldRedirectOn401(url)) {

        try {

          const { useAuthStore } = await import('@/stores/auth')

          const auth = useAuthStore()

          auth.user = null

          auth.loaded = true

        } catch {

          /* ignore */

        }

        scheduleSessionExpiredRedirect('session_expired')

        return Promise.reject(new Error('登录已过期，请重新登录'))

      }

      const msg = err.response?.data?.message || err.message || '请求失败'

      return Promise.reject(new Error(msg))

    }

    if (err.response?.status === 413) {

      return Promise.reject(new Error(`文件过大，单文件不能超过 ${FRONTEND_UPLOAD_MAX_MB} MB`))

    }

    const msg = err.response?.data?.message || err.message || '请求失败'

    return Promise.reject(new Error(msg))

  },

)



export interface ApiResponse<T = unknown> {

  ok: boolean

  data: T

  message: string

  code?: string

}


