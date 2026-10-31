<template>
  <div class="side-menu-wrap" :class="{ 'side-menu-wrap--collapsed': collapsed }">
    <a-menu
      class="side-menu"
      :class="{ 'side-menu--collapsed': collapsed }"
      :collapsed="collapsed"
      :selected-keys="menuSelectedKeys"
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
    </a-menu>

    <div v-if="showSystemAdmin" class="side-menu-footer">
      <a-dropdown
        trigger="click"
        :position="collapsed ? 'right' : 'tl'"
        :popup-visible="systemMenuOpen"
        content-class="side-menu-admin-dropdown"
        @popup-visible-change="onSystemMenuVisibleChange"
      >
        <button
          type="button"
          class="side-menu-admin-trigger"
          :class="{ 'is-active': isAdminSection }"
          :title="collapsed ? t('menu.system_admin') : undefined"
          :aria-label="t('menu.system_admin')"
          :aria-expanded="systemMenuOpen"
        >
          <icon-settings class="side-menu-admin-icon" />
          <span v-if="!collapsed" class="side-menu-admin-label">{{ t('menu.system_admin') }}</span>
          <icon-up v-if="!collapsed" class="side-menu-admin-caret" />
        </button>
        <template #content>
          <div class="side-menu-admin-pop">
            <div class="side-menu-admin-group">{{ t('menu.system_settings_group') }}</div>
            <button
              v-for="tab in systemSettingTabs"
              :key="tab.key"
              type="button"
              class="side-menu-admin-item"
              :class="{ 'is-active': selectedKeys.includes(tab.key) }"
              @click="onAdminItemClick(tab.key)"
            >
              {{ tab.label }}
            </button>

            <div class="side-menu-admin-group">{{ t('menu.form_settings_group') }}</div>
            <button
              v-for="tab in formSettingTabs"
              :key="tab.key"
              type="button"
              class="side-menu-admin-item"
              :class="{ 'is-active': selectedKeys.includes(tab.key) }"
              @click="onAdminItemClick(tab.key)"
            >
              {{ tab.label }}
            </button>

            <div class="side-menu-admin-divider" />
            <button
              type="button"
              class="side-menu-admin-item"
              :class="{ 'is-active': selectedKeys.includes('admin-logs') }"
              @click="onAdminItemClick('admin-logs')"
            >
              {{ t('menu.admin_logs') }}
            </button>
            <button
              type="button"
              class="side-menu-admin-item"
              :class="{ 'is-active': selectedKeys.includes('admin-workflow-instances') }"
              @click="onAdminItemClick('admin-workflow-instances')"
            >
              {{ t('settings.tab_workflow_instances') }}
            </button>
          </div>
        </template>
      </a-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import {
  IconSettings,
  IconStorage,
  IconExport,
  IconBarChart,
  IconUp,
} from '@arco-design/web-vue/es/icon'
import NavBadge from '@/components/NavBadge.vue'
import { useNavMenu } from '@/composables/useNavMenu'
import {
  FORM_SETTING_TAB_KEYS,
  SETTINGS_TAB_LABEL_KEYS,
  SYSTEM_SETTING_TAB_KEYS,
} from '@/constants/settingsTabs'

const props = defineProps<{ collapsed?: boolean }>()

const emit = defineEmits<{ navigate: [] }>()
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const openKeys = ref<string[]>([])
const systemMenuOpen = ref(false)

const {
  primaryItems,
  showStatsGroup,
  showSystemAdmin,
  showSectorMonitor,
  showFinanceExport,
} = useNavMenu()

function settingMenuKey(tab: string) {
  return `settings-tab-${tab}`
}

const systemSettingTabs = computed(() =>
  SYSTEM_SETTING_TAB_KEYS.map((tab) => ({
    key: settingMenuKey(tab),
    label: t(SETTINGS_TAB_LABEL_KEYS[tab] || tab),
  })),
)

const formSettingTabs = computed(() =>
  FORM_SETTING_TAB_KEYS.map((tab) => ({
    key: settingMenuKey(tab),
    label: t(SETTINGS_TAB_LABEL_KEYS[tab] || tab),
  })),
)

const selectedKeys = computed(() => {
  const name = String(route.name || '')
  if (name === 'admin-settings') {
    const tab = String(route.query.tab || 'brand')
    if (tab === 'workflow-instances') return ['admin-workflow-instances']
    if ((SYSTEM_SETTING_TAB_KEYS as readonly string[]).includes(tab)) {
      return [settingMenuKey(tab)]
    }
    if ((FORM_SETTING_TAB_KEYS as readonly string[]).includes(tab)) {
      return [settingMenuKey(tab)]
    }
    return [settingMenuKey('brand')]
  }
  return [name]
})

const ADMIN_ONLY_KEYS = new Set(['admin-logs', 'admin-workflow-instances'])

const menuSelectedKeys = computed(() =>
  selectedKeys.value.filter(
    (key) => !key.startsWith('settings-tab-') && !ADMIN_ONLY_KEYS.has(key),
  ),
)

const isAdminSection = computed(
  () => route.name === 'admin-settings' || route.name === 'admin-logs',
)

function syncOpenKeys() {
  const keys: string[] = []
  const name = String(route.name || '')
  if (name === 'admin-sector-monitor' || name === 'admin-finance-export') {
    keys.push('group-stats')
  }
  openKeys.value = keys
}

watch(() => route.fullPath, syncOpenKeys, { immediate: true })
watch(() => route.fullPath, () => {
  systemMenuOpen.value = false
})

function onSystemMenuVisibleChange(visible: boolean) {
  systemMenuOpen.value = visible
}

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

function onAdminItemClick(key: string) {
  systemMenuOpen.value = false
  onMenuClick(key)
}
</script>

<style scoped>
.side-menu-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.side-menu {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
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

.side-menu-footer {
  flex-shrink: 0;
  padding: 6px 4px 2px;
  border-top: 1px solid var(--divider);
}

.side-menu-admin-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 36px;
  padding: 0 10px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  text-align: left;
  cursor: pointer;
  transition:
    background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out);
}

.side-menu-admin-trigger:hover,
.side-menu-admin-trigger[aria-expanded='true'] {
  background: var(--surface-muted);
  color: var(--text);
}

.side-menu-admin-trigger.is-active {
  background: var(--brand-soft);
  color: var(--brand);
}

.side-menu-admin-icon {
  flex-shrink: 0;
  font-size: 16px;
}

.side-menu-admin-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.side-menu-admin-caret {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--text-tertiary);
}

.side-menu-wrap--collapsed .side-menu-footer {
  padding: 6px 4px 2px;
}

.side-menu-wrap--collapsed .side-menu-admin-trigger {
  justify-content: center;
  gap: 0;
  padding: 0;
}

.side-menu-admin-pop {
  width: 210px;
  max-height: min(62vh, 520px);
  padding: 4px;
  overflow-y: auto;
}

.side-menu-admin-group {
  padding: 8px 8px 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-tertiary);
}

.side-menu-admin-item {
  display: block;
  width: 100%;
  padding: 7px 8px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text);
  font-size: 13.5px;
  line-height: 1.35;
  text-align: left;
  cursor: pointer;
  transition:
    background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out);
}

.side-menu-admin-item:hover {
  background: var(--surface-muted);
}

.side-menu-admin-item.is-active {
  background: var(--brand-soft);
  color: var(--brand);
}

.side-menu-admin-divider {
  height: 1px;
  margin: 6px 4px;
  background: var(--divider);
}

.side-menu-badge {
  margin-left: auto;
}

:global(.side-menu-admin-dropdown .arco-dropdown-list-wrapper) {
  max-height: min(62vh, 520px);
}
</style>
