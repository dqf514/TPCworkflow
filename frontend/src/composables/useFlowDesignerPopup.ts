import { computed, inject, provide, type ComputedRef, type InjectionKey } from 'vue'

export const flowDesignerPopupKey: InjectionKey<ComputedRef<HTMLElement | null | undefined>> =
  Symbol('flowDesignerPopupContainer')

export function provideFlowDesignerPopup(
  container: ComputedRef<HTMLElement | null | undefined>,
) {
  provide(flowDesignerPopupKey, container)
}

/** 全屏流程设计时挂载弹层到全屏根节点，避免被 z-index 1100 遮挡 */
export function useFlowDesignerPopup() {
  const source = inject(flowDesignerPopupKey, null)
  return computed(() => source?.value || undefined)
}
