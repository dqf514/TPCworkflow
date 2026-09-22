<template>
  <nav
    class="mobile-tab-bar fixed bottom-0 left-0 right-0 z-50 safe-bottom md:hidden"
    role="navigation"
  >
    <div class="flex items-stretch justify-around h-14 max-w-lg mx-auto">
      <button
        v-for="tab in bottomBarTabs"
        :key="tab.key"
        type="button"
        class="flex flex-1 flex-col items-center justify-center gap-0.5 min-w-0 px-1 text-xs transition-colors"
        :class="active === tab.key ? 'text-[var(--color-primary)]' : 'text-gray-500'"
        @click="go(tab.key)"
      >
        <span class="tab-icon-wrap">
          <component :is="tab.icon" :size="22" />
          <NavBadge v-if="tab.badge" :count="tab.badge" />
        </span>
        <span class="truncate max-w-full">{{ tab.label }}</span>
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import NavBadge from '@/components/NavBadge.vue'
import { useNavMenu } from '@/composables/useNavMenu'

const route = useRoute()
const router = useRouter()
const { bottomBarTabs } = useNavMenu()

const active = computed(() => String(route.name || ''))

function go(name: string) {
  router.push({ name })
}
</script>

<style scoped>
.mobile-tab-bar {
  background: var(--surface);
  border-top: 1px solid var(--border);
  box-shadow: 0 -4px 16px rgba(16, 24, 40, 0.06);
  backdrop-filter: blur(8px);
}

.tab-icon-wrap {
  position: relative;
  display: inline-flex;
  line-height: 0;
}
</style>
