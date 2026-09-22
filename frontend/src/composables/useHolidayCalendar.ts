import { computed, ref, watch, type MaybeRefOrGetter, toValue } from 'vue'
import { api, type ApiResponse } from '@/api/client'

export interface HolidayCalendarPayload {
  region: string
  regions?: string[]
  region_name: string
  off_days: string[]
  holidays: string[]
  weekends: string[]
  makeup_workdays: string[]
  source?: string
}

const cache = new Map<string, HolidayCalendarPayload>()

function yearWindow(): { from: string; to: string } {
  const y = new Date().getFullYear()
  return { from: `${y - 1}-01-01`, to: `${y + 1}-12-31` }
}

export async function loadHolidayCalendar(
  companyId?: number,
  userId?: number,
): Promise<HolidayCalendarPayload> {
  const { from, to } = yearWindow()
  const key = `${companyId || 0}|${userId || 0}|${from}|${to}`
  const hit = cache.get(key)
  if (hit) return hit
  const res = await api.get<ApiResponse<HolidayCalendarPayload>>('/holidays/calendar', {
    params: {
      company_id: companyId || undefined,
      user_id: userId || undefined,
      from,
      to,
    },
  })
  const data = res.data.data || {
    region: 'CN',
    region_name: '中国大陆',
    off_days: [],
    holidays: [],
    weekends: [],
    makeup_workdays: [],
  }
  cache.set(key, data)
  return data
}

export function useHolidayCalendar(
  companyId: MaybeRefOrGetter<number | undefined>,
  userId?: MaybeRefOrGetter<number | undefined>,
) {
  const region = ref('CN')
  const regionName = ref('')
  const offDays = ref<string[]>([])
  const makeupWorkdays = ref<string[]>([])
  const loaded = ref(false)

  async function reload() {
    const cid = toValue(companyId)
    const uid = toValue(userId)
    try {
      const data = await loadHolidayCalendar(cid, uid)
      region.value = data.region || 'CN'
      regionName.value = data.region_name || ''
      offDays.value = data.off_days || []
      makeupWorkdays.value = data.makeup_workdays || []
    } catch {
      offDays.value = []
      makeupWorkdays.value = []
    } finally {
      loaded.value = true
    }
  }

  watch(
    () => [toValue(companyId), toValue(userId)].join('|'),
    () => { void reload() },
    { immediate: true },
  )

  return {
    region,
    regionName,
    offDays,
    makeupWorkdays,
    loaded,
    reload,
    hints: computed(() => ({
      offDays: offDays.value,
      makeupWorkdays: makeupWorkdays.value,
    })),
  }
}
