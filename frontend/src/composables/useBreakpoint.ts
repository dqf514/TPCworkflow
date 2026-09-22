import { onBeforeUnmount, onMounted, onUnmounted, ref } from 'vue'

/** <1024 与手机相同布局（含平板）；≥1024 桌面侧栏 */
export const MOBILE_MEDIA_QUERY = '(max-width: 1023px)'
const MQ_MOBILE = MOBILE_MEDIA_QUERY
const MQ_DESKTOP = '(min-width: 1024px)'

export function matchMobileViewport() {
  if (typeof window === 'undefined') return false
  return window.matchMedia(MQ_MOBILE).matches
}

function readBreakpoint() {
  if (typeof window === 'undefined') {
    return { width: 1280, isMobile: false, isDesktop: true }
  }
  return {
    width: window.innerWidth,
    isMobile: window.matchMedia(MQ_MOBILE).matches,
    isDesktop: window.matchMedia(MQ_DESKTOP).matches,
  }
}

export function useBreakpoint() {
  const initial = readBreakpoint()
  const width = ref(initial.width)
  const isMobile = ref(initial.isMobile)
  const isDesktop = ref(initial.isDesktop)

  function update() {
    const next = readBreakpoint()
    width.value = next.width
    isMobile.value = next.isMobile
    isDesktop.value = next.isDesktop
  }

  onMounted(() => {
    update()
    window.addEventListener('resize', update)
    const mq = window.matchMedia(MQ_MOBILE)
    const onMq = () => {
      isMobile.value = mq.matches
      isDesktop.value = window.matchMedia(MQ_DESKTOP).matches
    }
    mq.addEventListener('change', onMq)
    onBeforeUnmount(() => mq.removeEventListener('change', onMq))
  })
  onUnmounted(() => window.removeEventListener('resize', update))

  return { width, isMobile, isDesktop }
}
