<template>
  <PageChrome :title="t('menu.dashboard')" :description="welcomeLine">
    <div class="dashboard-grid">
      <router-link :to="{ name: 'tasks' }" class="stat-card stat-card-accent app-card-hover block no-underline">
        <span class="stat-label">{{ t('workflow.todo') }}</span>
        <span class="stat-value">{{ todoCount }}</span>
        <span class="stat-hint">{{ t('dashboard.hint_todo') }}</span>
      </router-link>

      <router-link :to="{ name: 'apply' }" class="stat-card app-card-hover block no-underline">
        <span class="stat-label">{{ t('menu.apply') }}</span>
        <span class="stat-value stat-value--sm">{{ t('dashboard.hint_apply_action') }}</span>
        <span class="stat-hint">{{ t('dashboard.hint_apply') }}</span>
      </router-link>

      <router-link :to="{ name: 'my-instances' }" class="stat-card app-card-hover block no-underline">
        <span class="stat-label">{{ t('workflow.my_instances') }}</span>
        <span class="stat-value stat-value--sm">{{ t('dashboard.hint_instances_action') }}</span>
        <span class="stat-hint">{{ t('dashboard.hint_instances') }}</span>
      </router-link>
    </div>

    <section v-if="membershipLine" class="dashboard-panel app-card">
      <h2 class="panel-title">{{ t('dashboard.membership_title') }}</h2>
      <p class="panel-text">{{ membershipLine }}</p>
    </section>
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowBadgesStore } from '@/stores/workflowBadges'
import PageChrome from '@/components/layout/PageChrome.vue'

const { t } = useI18n()
const auth = useAuthStore()
const badges = useWorkflowBadgesStore()

const todoCount = computed(() => badges.todoCount)

const welcomeLine = computed(() => {
  const name = auth.user?.display_name || ''
  return name ? t('dashboard.welcome_named', { name }) : t('dashboard.welcome_anon')
})

const membershipLine = computed(() => {
  const m = auth.user?.memberships
  if (!m?.length) return ''
  return m.map((x) => `${x.company_name} / ${x.department_name}`).join('、')
})

onMounted(() => {
  void badges.refresh()
})
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(1, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 1.25rem;
}

@media (min-width: 640px) {
  .dashboard-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.stat-label {
  display: block;
  font-size: var(--app-font-sm, 14px);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 0.375rem;
}

.stat-value {
  display: block;
  font-size: 2.25rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--brand);
  line-height: 1.1;
}

.stat-value--sm {
  font-size: 1.5rem;
  color: var(--text);
}

.stat-hint {
  display: block;
  margin-top: 0.5rem;
  font-size: var(--app-font-xs, 13px);
  color: var(--text-tertiary);
}

.dashboard-panel {
  padding: 1rem 1.25rem;
}

.panel-title {
  margin: 0 0 0.375rem;
  font-size: var(--app-font-base, 16px);
  font-weight: 700;
  color: var(--text);
}

.panel-text {
  margin: 0;
  font-size: var(--app-font-sm, 14px);
  color: var(--text-secondary);
  line-height: 1.5;
}
</style>
