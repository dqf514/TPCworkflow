<template>
  <nav
    class="mobile-tab-bar fixed bottom-0 left-0 right-0 z-50 safe-bottom md:hidden"
    role="navigation"
  >
    <div class="mobile-tab-bar__inner">
      <button
        v-for="tab in bottomBarTabs"
        :key="tab.key"
        type="button"
        class="mobile-tab"
        :class="{ 'is-active': active === tab.key }"
        @click="go(tab.key)"
      >
        <span class="tab-icon-wrap">
          <component :is="tab.icon" :size="20" />
          <NavBadge v-if="tab.badge" :count="tab.badge" />
        </span>
        <span class="tab-label">{{ tab.label }}</span>
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
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  border-top: 1px solid var(--border);
  backdrop-filter: saturate(180%) blur(16px);
}

.mobile-tab-bar__inner {
  display: flex;
  align-items: stretch;
  justify-content: space-around;
  height: 3.5rem;
  max-width: 32rem;
  margin: 0 auto;
}

.mobile-tab {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 0 0.25rem;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: color var(--dur-fast) var(--ease-out);
}

.mobile-tab.is-active {
  color: var(--brand);
}

.tab-icon-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 24px;
  border-radius: var(--radius-pill);
  line-height: 0;
  transition: background-color var(--dur-base) var(--ease-out);
}

.mobile-tab.is-active .tab-icon-wrap {
  background: var(--brand-soft);
}

.tab-label {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}
</style>
