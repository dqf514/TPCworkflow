<template>
  <span
    v-if="display"
    class="nav-badge"
    :class="{ 'nav-badge--inline': inline }"
    aria-hidden="true"
  >
    {{ display }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    count?: number
    inline?: boolean
  }>(),
  {
    count: 0,
    inline: false,
  },
)

const display = computed(() => {
  const n = props.count || 0
  if (n <= 0) return ''
  return n > 99 ? '99+' : String(n)
})
</script>

<style scoped>
.nav-badge {
  position: absolute;
  top: -4px;
  right: -8px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: #f53f3f;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
  box-shadow: 0 0 0 1.5px var(--surface, #fff);
  pointer-events: none;
}

.nav-badge--inline {
  position: static;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 6px;
  vertical-align: middle;
  box-shadow: none;
}
</style>
