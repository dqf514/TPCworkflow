<template>
  <!-- 徽标不再对读屏隐藏：role=status 让读屏能播报数量变化 -->
  <span
    v-if="display"
    class="nav-badge"
    :class="{ 'nav-badge--inline': inline }"
    role="status"
    :aria-label="ariaLabel"
  >
    <span aria-hidden="true">{{ display }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    count?: number
    inline?: boolean
    /** 读屏播报文案；不传时使用「N 条待办」的通用表述 */
    ariaLabel?: string
  }>(),
  {
    count: 0,
    inline: false,
    ariaLabel: '',
  },
)

const display = computed(() => {
  const n = props.count || 0
  if (n <= 0) return ''
  return n > 99 ? '99+' : String(n)
})

const ariaLabel = computed(() => {
  if (props.ariaLabel) return props.ariaLabel
  return `${display.value} 条待办`
})
</script>

<style scoped>
.nav-badge {
  position: absolute;
  top: -4px;
  right: -8px;
  min-width: 16px;
  height: 16px;
  padding: 0 var(--app-space-4);
  border-radius: var(--radius-pill);
  background: #f53f3f;
  color: #fff;
  font-size: var(--app-font-2xs);
  font-weight: 700;
  line-height: 16px;
  text-align: center;
  box-shadow: 0 0 0 1.5px var(--surface);
  pointer-events: none;
}

.nav-badge--inline {
  position: static;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: var(--app-space-6);
  vertical-align: middle;
  box-shadow: none;
}
</style>
