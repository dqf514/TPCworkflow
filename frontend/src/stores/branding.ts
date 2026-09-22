import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, type ApiResponse } from '@/api/client'
import { APP_DISPLAY_NAME } from '@/constants/branding'

export const useBrandingStore = defineStore('branding', () => {
  const companyName = ref('')
  const appName = ref(APP_DISPLAY_NAME)
  const companyLogoUrl = ref('')
  const logoCacheKey = ref(0)
  const loaded = ref(false)

  const logoUrl = computed(() => {
    if (!companyLogoUrl.value) return ''
    const sep = companyLogoUrl.value.includes('?') ? '&' : '?'
    return `${companyLogoUrl.value}${sep}v=${logoCacheKey.value}`
  })

  function setLogoUrl(url: string | null | undefined) {
    companyLogoUrl.value = url || ''
    logoCacheKey.value = Date.now()
  }

  async function load() {
    try {
      const res = await api.get<
        ApiResponse<{ company_name?: string; app_name?: string; company_logo_url?: string | null }>
      >('/auth/login-methods')
      if (res.data.ok) {
        companyName.value = res.data.data.company_name || ''
        appName.value = res.data.data.app_name || APP_DISPLAY_NAME
        setLogoUrl(res.data.data.company_logo_url)
      }
    } catch {
      companyName.value = ''
      appName.value = APP_DISPLAY_NAME
      companyLogoUrl.value = ''
    } finally {
      loaded.value = true
    }
  }

  const headerTitle = () => companyName.value || appName.value

  return {
    companyName,
    appName,
    companyLogoUrl,
    logoUrl,
    logoCacheKey,
    loaded,
    load,
    setLogoUrl,
    headerTitle,
  }
})
