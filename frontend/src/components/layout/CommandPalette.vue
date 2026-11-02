<template>
  <Teleport to="body">
    <Transition name="cmdk-fade">
      <div v-if="visible" class="cmdk-mask" @mousedown.self="close">
        <div
          ref="paletteEl"
          class="cmdk"
          role="dialog"
          aria-modal="true"
          :aria-label="t('palette.trigger')"
          @keydown="onPaletteKeydown"
        >
          <div class="cmdk-input-row">
            <icon-search class="cmdk-search-icon" />
            <input
              ref="inputEl"
              v-model="query"
              type="text"
              class="cmdk-input"
              role="combobox"
              aria-expanded="true"
              aria-autocomplete="list"
              aria-controls="cmdk-listbox"
              :aria-activedescendant="activeDescendantId"
              :aria-label="t('palette.placeholder')"
              :placeholder="t('palette.placeholder')"
              autocomplete="off"
              spellcheck="false"
              @keydown.down.prevent="move(1)"
              @keydown.up.prevent="move(-1)"
              @keydown.enter.prevent="runActive()"
              @keydown.esc.prevent="close"
            />
            <kbd class="cmdk-kbd">ESC</kbd>
          </div>

          <div ref="listEl" class="cmdk-list">
            <div id="cmdk-listbox" role="listbox" :aria-label="t('palette.trigger')">
              <button
                v-for="(item, index) in filtered"
                :id="optionId(index)"
                :key="item.key"
                type="button"
                role="option"
                class="cmdk-item"
                :class="{ 'is-active': index === active }"
                :aria-selected="index === active"
                @mouseenter="active = index"
                @click="run(item)"
              >
                <component :is="item.icon" v-if="item.icon" class="cmdk-item-icon" />
                <span class="cmdk-item-label">{{ item.label }}</span>
                <span class="cmdk-item-group">{{ item.group }}</span>
              </button>
            </div>
            <div v-if="!filtered.length" class="cmdk-empty" role="status">
              {{ t('palette.empty') }}
            </div>
          </div>

          <div class="cmdk-foot">{{ t('palette.hint') }}</div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  IconBarChart,
  IconExport,
  IconFile,
  IconHistory,
  IconMoon,
  IconSearch,
  IconSun,
} from '@arco-design/web-vue/es/icon'
import { useNavMenu } from '@/composables/useNavMenu'
import { useCommandPalette } from '@/composables/useCommandPalette'
import { useTheme } from '@/composables/useTheme'
import {
  FORM_SETTING_TAB_KEYS,
  SETTINGS_TAB_LABEL_KEYS,
  SYSTEM_SETTING_TAB_KEYS,
} from '@/constants/settingsTabs'

interface PaletteItem {
  key: string
  label: string
  group: string
  icon?: object
  run: () => void
}

const { t } = useI18n()
const router = useRouter()
const { visible, close } = useCommandPalette()
const { isDark, toggleTheme } = useTheme()
const {
  primaryItems,
  showSectorMonitor,
  showFinanceExport,
  showSystemAdmin,
} = useNavMenu()

const query = ref('')
const active = ref(0)
const inputEl = ref<HTMLInputElement | null>(null)
const listEl = ref<HTMLElement | null>(null)
const paletteEl = ref<HTMLElement | null>(null)

/** 选项 id，供 input 的 aria-activedescendant 引用 */
function optionId(index: number) {
  return `cmdk-option-${index}`
}

const activeDescendantId = computed(() =>
  filtered.value.length && active.value >= 0 ? optionId(active.value) : undefined,
)

const items = computed<PaletteItem[]>(() => {
  const list: PaletteItem[] = primaryItems.value.map((item) => ({
    key: item.key,
    label: item.label,
    group: t('palette.group_nav'),
    icon: item.icon,
    run: () => router.push({ name: item.key }),
  }))

  if (showSectorMonitor.value) {
    list.push({
      key: 'admin-sector-monitor',
      label: t('menu.sector_monitor'),
      group: t('menu.stats_group'),
      icon: IconBarChart,
      run: () => router.push({ name: 'admin-sector-monitor' }),
    })
  }
  if (showFinanceExport.value) {
    list.push({
      key: 'admin-finance-export',
      label: t('menu.finance_export'),
      group: t('menu.stats_group'),
      icon: IconExport,
      run: () => router.push({ name: 'admin-finance-export' }),
    })
  }

  list.push({
    key: 'toggle-theme',
    label: isDark.value ? t('palette.theme_light') : t('palette.theme_dark'),
    group: t('palette.group_action'),
    icon: isDark.value ? IconSun : IconMoon,
    run: toggleTheme,
  })

  if (showSystemAdmin.value) {
    for (const tab of SYSTEM_SETTING_TAB_KEYS) {
      list.push({
        key: `settings-${tab}`,
        label: t(SETTINGS_TAB_LABEL_KEYS[tab] || tab),
        group: t('menu.system_settings_group'),
        run: () => router.push({ name: 'admin-settings', query: { tab } }),
      })
    }
    for (const tab of FORM_SETTING_TAB_KEYS) {
      list.push({
        key: `settings-${tab}`,
        label: t(SETTINGS_TAB_LABEL_KEYS[tab] || tab),
        group: t('menu.form_settings_group'),
        run: () => router.push({ name: 'admin-settings', query: { tab } }),
      })
    }
    list.push({
      key: 'admin-logs',
      label: t('menu.admin_logs'),
      group: t('menu.system_admin'),
      icon: IconHistory,
      run: () => router.push({ name: 'admin-logs' }),
    })
    list.push({
      key: 'admin-workflow-instances',
      label: t('settings.tab_workflow_instances'),
      group: t('menu.system_admin'),
      icon: IconFile,
      run: () => router.push({ name: 'admin-settings', query: { tab: 'workflow-instances' } }),
    })
  }

  return list
})

const filtered = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  if (!keyword) return items.value
  return items.value.filter(
    (item) =>
      item.label.toLowerCase().includes(keyword) ||
      item.group.toLowerCase().includes(keyword) ||
      item.key.toLowerCase().includes(keyword),
  )
})

watch(filtered, () => {
  active.value = 0
})

watch(visible, async (open) => {
  if (!open) {
    releaseBackgroundInert()
    return
  }
  query.value = ''
  active.value = 0
  // 背景内容设为 inert，键盘与读屏都不会跑到遮罩后面的元素上
  applyBackgroundInert()
  await nextTick()
  inputEl.value?.focus()
})

/** 打开时把应用根节点设为 inert（命令面板被 Teleport 到 body，不受影响） */
function applyBackgroundInert() {
  const app = document.getElementById('app')
  if (app) app.setAttribute('inert', '')
}

function releaseBackgroundInert() {
  const app = document.getElementById('app')
  if (app) app.removeAttribute('inert')
}

/** 焦点陷阱：Tab / Shift+Tab 在命令面板内循环 */
function onPaletteKeydown(event: KeyboardEvent) {
  if (event.key !== 'Tab') return
  const root = paletteEl.value
  if (!root) return
  const focusables = Array.from(
    root.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((el) => el.offsetParent !== null || el === document.activeElement)
  if (!focusables.length) {
    event.preventDefault()
    return
  }
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  const current = document.activeElement as HTMLElement | null
  if (event.shiftKey) {
    if (current === first || !root.contains(current)) {
      event.preventDefault()
      last.focus()
    }
  } else if (current === last || !root.contains(current)) {
    event.preventDefault()
    first.focus()
  }
}

function move(delta: number) {
  if (!filtered.value.length) return
  active.value = (active.value + delta + filtered.value.length) % filtered.value.length
  const node = listEl.value?.querySelectorAll('.cmdk-item')[active.value] as HTMLElement | undefined
  node?.scrollIntoView({ block: 'nearest' })
}

function run(item: PaletteItem) {
  close()
  item.run()
}

function runActive() {
  const item = filtered.value[active.value]
  if (item) run(item)
}

function onKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    visible.value = !visible.value
    return
  }
  if (event.key === 'Escape' && visible.value) close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  releaseBackgroundInert()
})
</script>

<style scoped>
.cmdk-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 12vh var(--app-space-16) var(--app-space-16);
  background: rgb(15 17 19 / 46%);
  backdrop-filter: blur(3px);
}

.cmdk {
  width: min(560px, 100%);
  max-height: min(560px, 72vh);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--surface-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-pop);
}

.cmdk-input-row {
  display: flex;
  align-items: center;
  gap: var(--app-space-10);
  padding: 13px var(--app-space-16);
  border-bottom: 1px solid var(--border);
}

.cmdk-search-icon {
  flex-shrink: 0;
  font-size: var(--app-font-16);
  color: var(--text-tertiary);
}

.cmdk-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--app-font-md);
  color: var(--text);
}

.cmdk-input::placeholder {
  color: var(--text-disabled);
}

.cmdk-kbd {
  padding: 1px var(--app-space-6);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-muted);
  font-size: var(--app-font-10);
  font-family: ui-monospace, 'Cascadia Code', monospace;
  color: var(--text-tertiary);
}

.cmdk-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--app-space-6);
}

.cmdk-item {
  display: flex;
  align-items: center;
  gap: var(--app-space-10);
  width: 100%;
  padding: var(--app-space-8) var(--app-space-12);
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  text-align: left;
  color: var(--text);
  font-size: var(--app-font-md);
  cursor: pointer;
  transition: background-color var(--dur-fast) var(--ease-out);
}

.cmdk-item.is-active {
  background: var(--brand-soft);
  color: var(--brand-text);
}

.cmdk-item-icon {
  flex-shrink: 0;
  font-size: var(--app-font-lg);
  color: var(--text-tertiary);
}

.cmdk-item.is-active .cmdk-item-icon {
  color: var(--brand-text);
}

.cmdk-item-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cmdk-item-group {
  flex-shrink: 0;
  font-size: var(--app-font-2xs);
  color: var(--text-tertiary);
}

.cmdk-empty {
  padding: 28px var(--app-space-16);
  text-align: center;
  font-size: var(--app-font-sm);
  color: var(--text-tertiary);
}

.cmdk-foot {
  padding: var(--app-space-8) var(--app-space-16);
  border-top: 1px solid var(--border);
  font-size: var(--app-font-10);
  color: var(--text-tertiary);
}

.cmdk-fade-enter-active,
.cmdk-fade-leave-active {
  transition: opacity var(--dur-fast) var(--ease-out);
}

.cmdk-fade-enter-active .cmdk,
.cmdk-fade-leave-active .cmdk {
  transition: transform var(--dur-fast) var(--ease-out);
}

.cmdk-fade-enter-from,
.cmdk-fade-leave-to {
  opacity: 0;
}

.cmdk-fade-enter-from .cmdk,
.cmdk-fade-leave-to .cmdk {
  transform: translateY(-6px) scale(0.985);
}
</style>
