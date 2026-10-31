<template>
  <a-menu
    class="side-menu"
    :class="{ 'side-menu--collapsed': collapsed }"
    :collapsed="collapsed"
    :selected-keys="selectedKeys"
    v-model:open-keys="openKeys"
    auto-open-selected
    @menu-item-click="onMenuClick"
  >
    <a-menu-item v-for="item in primaryItems" :key="item.key">
      <template #icon><component :is="item.icon" /></template>
      {{ item.label }}
      <NavBadge v-if="!props.collapsed && item.badge" :count="item.badge" inline class="side-menu-badge" />
    </a-menu-item>

    <a-sub-menu v-if="showStatsGroup" key="group-stats">
      <template #icon><icon-bar-chart /></template>
      <template #title>{{ t('menu.stats_group') }}</template>
      <a-menu-item v-if="showSectorMonitor" key="admin-sector-monitor">
        <template #icon><icon-storage /></template>
        {{ t('menu.sector_monitor') }}
      </a-menu-item>
      <a-menu-item v-if="showFinanceExport" key="admin-finance-export">
        <template #icon><icon-export /></template>
        {{ t('menu.finance_export') }}
      </a-menu-item>
    </a-sub-menu>

    <a-sub-menu v-if="showSystemAdmin" key="group-system">
      <template #icon><icon-settings /></template>
      <template #title>{{ t('menu.system_admin') }}</template>

      <a-menu-item key="settings-tab-brand">
        <template #icon><icon-settings /></template>
        {{ t('menu.system_settings_group') }}
      </a-menu-item>

      <a-menu-item key="settings-tab-option-sets">
        <template #icon><icon-apps /></template>
        {{ t('menu.form_settings_group') }}
      </a-menu-item>

      <a-menu-item key="admin-logs">
        <template #icon><icon-history /></template>
        {{ t('menu.admin_logs') }}
      </a-menu-item>

      <a-menu-item key="admin-workflow-instances">
        <template #icon><icon-file /></template>
        {{ t('settings.tab_workflow_instances') }}
      </a-menu-item>
    </a-sub-menu>
  </a-menu>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import {
  IconSettings,
  IconStorage,
  IconHistory,
  IconExport,
  IconBarChart,
  IconApps,
  IconFile,
} from '@arco-design/web-vue/es/icon'
import NavBadge from '@/components/NavBadge.vue'
import { useNavMenu } from '@/composables/useNavMenu'

const FORM_SETTING_TAB_KEYS = [
  'option-sets',
  'record-sets',
  'exchange-rates',
  'llm',
  'print-templates',
] as const

const props = defineProps<{ collapsed?: boolean }>()

const emit = defineEmits<{ navigate: [] }>()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const openKeys = ref<string[]>([])

const {
  primaryItems,
  showStatsGroup,
  showSystemAdmin,
  showSectorMonitor,
  showFinanceExport,
} = useNavMenu()

const selectedKeys = computed(() => {
  const name = String(route.name || '')
  if (name === 'admin-settings') {
    const tab = String(route.query.tab || 'brand')
    if (tab === 'workflow-instances') return ['admin-workflow-instances']
    if ((FORM_SETTING_TAB_KEYS as readonly string[]).includes(tab)) {
      return ['settings-tab-option-sets']
    }
    return ['settings-tab-brand']
  }
  return [name]
})

function syncOpenKeys() {
  const keys: string[] = []
  const name = String(route.name || '')
  if (name === 'admin-sector-monitor' || name === 'admin-finance-export') {
    keys.push('group-stats')
  }
  if (name === 'admin-logs' || name === 'admin-workflow-instances' || name === 'admin-settings') {
    keys.push('group-system')
  }
  openKeys.value = keys
}

watch(() => route.fullPath, syncOpenKeys, { immediate: true })

function onMenuClick(key: string) {
  if (key.startsWith('settings-tab-')) {
    const tab = key.slice('settings-tab-'.length)
    router.push({ name: 'admin-settings', query: { tab } })
    emit('navigate')
    return
  }
  if (key === 'admin-workflow-instances') {
    router.push({ name: 'admin-settings', query: { tab: 'workflow-instances' } })
    emit('navigate')
    return
  }
  router.push({ name: key })
  emit('navigate')
}
</script>

<style scoped>
.side-menu {
  border: none !important;
  background: transparent !important;
  width: 100%;
}

.side-menu--collapsed {
  width: 100%;
}

.side-menu :deep(.arco-menu-inner) {
  padding: 0 0.25rem;
}

.side-menu :deep(.arco-menu-item),
.side-menu :deep(.arco-menu-inline-header) {
  border-radius: var(--radius-sm);
  margin-bottom: 2px;
  line-height: 1.35;
}

.side-menu :deep(.arco-menu-pop-header) {
  border-radius: var(--radius-sm);
}

.side-menu-badge {
  margin-left: auto;
}
</style>
