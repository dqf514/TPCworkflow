import { onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRouter, type RouteLocationNormalized } from 'vue-router'

export interface UnsavedLeaveGuardOptions {
  /** 是否有未保存更改 */
  isDirty: () => boolean
  /** 保存并退出时调用；返回 true 表示保存成功可离开 */
  onSave?: () => Promise<boolean>
  /** 是否启用守卫，默认始终启用 */
  enabled?: () => boolean
  /** 保存成功后同步基准快照（可选） */
  markSaved?: () => void
}

type PendingRoute = {
  to: RouteLocationNormalized
}

export function useUnsavedLeaveGuard(options: UnsavedLeaveGuardOptions) {
  const router = useRouter()
  const modalVisible = ref(false)
  const saving = ref(false)
  let bypassGuard = false
  let pendingRoute: PendingRoute | null = null
  let pendingAction: (() => void) | null = null

  function guardActive() {
    return (options.enabled?.() ?? true) && options.isDirty()
  }

  function onBeforeUnload(e: BeforeUnloadEvent) {
    if (bypassGuard || !guardActive()) return
    e.preventDefault()
    e.returnValue = ''
  }

  onMounted(() => {
    window.addEventListener('beforeunload', onBeforeUnload)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('beforeunload', onBeforeUnload)
  })

  onBeforeRouteLeave((to, _from, next) => {
    if (bypassGuard || !guardActive()) {
      next()
      return
    }
    pendingRoute = { to }
    pendingAction = null
    modalVisible.value = true
    next(false)
  })

  function cancelLeave() {
    modalVisible.value = false
    pendingRoute = null
    pendingAction = null
  }

  async function proceedLeave() {
    modalVisible.value = false
    const routeTarget = pendingRoute?.to
    const action = pendingAction
    pendingRoute = null
    pendingAction = null

    bypassGuard = true
    try {
      if (routeTarget) {
        // next(false) 已中止导航，不能再次调用 next()，需重新 push
        await router.push(routeTarget)
      } else if (action) {
        action()
      }
    } finally {
      bypassGuard = false
    }
  }

  function discardLeave() {
    void proceedLeave()
  }

  async function saveAndLeave() {
    if (!options.onSave) {
      discardLeave()
      return
    }
    saving.value = true
    try {
      const ok = await options.onSave()
      if (!ok) return
      options.markSaved?.()
      await proceedLeave()
    } finally {
      saving.value = false
    }
  }

  /** 页内操作触发的离开（如返回列表） */
  function requestLeave(action: () => void) {
    if (bypassGuard || !guardActive()) {
      action()
      return
    }
    pendingAction = action
    pendingRoute = null
    modalVisible.value = true
  }

  return {
    modalVisible,
    saving,
    cancelLeave,
    discardLeave,
    saveAndLeave,
    requestLeave,
  }
}
