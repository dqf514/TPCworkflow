import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  EMBED_DESKTOP_QUERY,
  isEmbedDesktopActive,
  markEmbedDesktopSession,
  routerPushWithEmbed,
  syncEmbedDesktopDocumentClass,
  withEmbedQuery,
} from '@/utils/embedDesktop'

type ClientMessage = {
  type: string
  [key: string]: unknown
}

export function useEmbedDesktop() {
  const route = useRoute()
  const router = useRouter()

  const isEmbedDesktop = computed(() => isEmbedDesktopActive(route))

  watch(
    isEmbedDesktop,
    (active) => {
      if (active) markEmbedDesktopSession()
      syncEmbedDesktopDocumentClass(active)
    },
    { immediate: true },
  )

  function notifyClient(payload: ClientMessage) {
    const host = (window as Window & { chrome?: { webview?: { postMessage: (msg: unknown) => void } } })
      .chrome?.webview
    if (host) host.postMessage(payload)
  }

  /** 嵌入模式下通知客户端并阻止 Web 内跳转 */
  function embedNavigate(
    name: string,
    params?: Record<string, string | number>,
    query?: Record<string, string>,
  ) {
    if (!isEmbedDesktop.value) {
      void routerPushWithEmbed(router, { name, params, query })
      return
    }
    const path = router.resolve({
      name,
      params,
      query: withEmbedQuery(query),
    }).fullPath
    notifyClient({ type: 'navigate', path })
  }

  function embedBack(defaultName = 'tasks') {
    if (!isEmbedDesktop.value) {
      void routerPushWithEmbed(router, { name: defaultName })
      return
    }
    const path = defaultName === 'tasks' ? '/tasks' : `/${defaultName}`
    notifyClient({ type: 'navigate', path: `${path}?embed=${EMBED_DESKTOP_QUERY}` })
  }

  function embedRefreshBadges() {
    if (isEmbedDesktop.value) notifyClient({ type: 'refresh_badges' })
  }

  return { isEmbedDesktop, notifyClient, embedNavigate, embedBack, embedRefreshBadges, routerPushWithEmbed }
}
