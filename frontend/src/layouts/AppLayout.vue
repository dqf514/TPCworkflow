<template>
  <a-config-provider :locale="arcoLocale">
    <a-layout class="app-shell" :class="{ 'app-shell--embed': isEmbedDesktop }">
      <a-layout-header v-if="!isEmbedDesktop" class="app-header">
        <div class="app-header-left">
          <button
            v-if="isMobile"
            type="button"
            class="app-icon-btn"
            aria-label="打开导航"
            @click="drawerVisible = true"
          >
            <icon-menu />
          </button>
          <button
            v-else-if="isDesktop"
            type="button"
            class="app-icon-btn app-sider-toggle"
            :aria-label="sidebarCollapsed ? '展开导航' : '收起导航'"
            :title="sidebarCollapsed ? '展开导航' : '收起导航'"
            @click="toggleSidebar"
          >
            <icon-right v-if="sidebarCollapsed" />
            <icon-left v-else />
          </button>
          <div class="app-header-brand">
            <BrandLogo size="sm" />
            <span class="app-header-title">{{ branding.headerTitle() }}</span>
            <span v-if="branding.appName && branding.appName !== branding.headerTitle()" class="app-header-app">
              {{ branding.appName }}
            </span>
          </div>
        </div>
        <div class="app-header-right">
          <a-select
            v-model="currentLocale"
            :options="localeOptions"
            size="small"
            class="app-locale-select"
            @change="onLocaleChange"
            @update:model-value="onLocaleChange"
          />
          <a-dropdown v-if="auth.user" trigger="click">
            <button type="button" class="app-user-chip" aria-label="用户菜单">
              <a-avatar :size="30" :image-url="auth.user.avatar_url || undefined">
                {{ auth.user.display_name?.[0] || 'U' }}
              </a-avatar>
              <span class="app-user-name">{{ auth.user.display_name }}</span>
              <icon-down class="app-user-caret" />
            </button>
            <template #content>
              <a-doption @click="openProfile('profile')">{{ t('auth.profile') }}</a-doption>
              <a-doption @click="openProfile('password')">{{ t('auth.password_settings') }}</a-doption>
              <a-doption v-if="clientDownloadAvailable" @click="openClientDownloadModal">
                {{ t('auth.download_client') }}
              </a-doption>
              <a-doption @click="handleLogout">{{ t('auth.logout') }}</a-doption>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <a-layout class="app-body">
        <a-layout-sider
          v-if="!isMobile && !isEmbedDesktop"
          :width="244"
          :collapsed-width="72"
          :collapsed="sidebarCollapsed"
          class="app-sider"
          :collapsible="isDesktop"
          hide-trigger
          @collapse="onSiderCollapse"
        >
          <SideMenu :collapsed="sidebarCollapsed" />
        </a-layout-sider>

        <a-layout-content class="app-content" :class="{ 'has-mobile-tab': isMobile && !isEmbedDesktop, 'app-content--embed': isEmbedDesktop }">
          <a-alert
            v-if="!isEmbedDesktop && auth.user?.need_set_password"
            type="warning"
            closable
            class="app-password-alert"
            title="您尚未设置登录密码"
            description="请点击右上角头像 →「密码设置」，设置后可使用账号密码登录。"
          />
          <div class="app-content-inner">
            <router-view />
          </div>
        </a-layout-content>
      </a-layout>

      <MobileTabBar v-if="isMobile && !isEmbedDesktop" />

      <a-drawer
        v-if="!isEmbedDesktop"
        v-model:visible="drawerVisible"
        :width="280"
        placement="left"
        :footer="false"
        :title="branding.headerTitle()"
        class="app-nav-drawer"
      >
        <SideMenu :collapsed="false" @navigate="drawerVisible = false" />
      </a-drawer>
    </a-layout>
    <ProfileModal v-model:visible="profileVisible" :default-tab="profileTab" />

    <a-modal
      v-model:visible="clientDownloadModalVisible"
      :title="t('client.download_title')"
      :footer="false"
      :mask-closable="true"
      class="client-download-modal"
      @close="clientDownloadModalVisible = false"
    >
      <p class="client-download-desc">{{ t('client.download_desc') }}</p>
      <a-alert type="info" class="client-download-edge-tip">
        <template #title>{{ t('client.download_edge_title') }}</template>
        {{ t('client.download_edge_tip') }}
      </a-alert>
      <div class="client-download-actions">
        <a
          v-if="clientDownloadSetup.available"
          class="client-download-btn client-download-btn--primary"
          :href="clientDownloadSetup.download_url"
          rel="noopener"
        >
          {{ t('client.download_setup') }}
          <span v-if="clientDownloadSetup.size_label" class="client-download-btn-size">
            {{ clientDownloadSetup.size_label }}
          </span>
        </a>
        <a
          v-if="clientDownloadZip.available"
          class="client-download-btn client-download-btn--secondary"
          :href="clientDownloadZip.download_url"
          rel="noopener"
        >
          {{ t('client.download_zip') }}
          <span v-if="clientDownloadZip.size_label" class="client-download-btn-size">
            {{ clientDownloadZip.size_label }}
          </span>
        </a>
        <a
          v-if="clientDownloadExe.available"
          class="client-download-btn client-download-btn--secondary"
          :href="clientDownloadExe.download_url"
          rel="noopener"
        >
          {{ t('client.download_exe') }}
          <span v-if="clientDownloadExe.size_label" class="client-download-btn-size">
            {{ clientDownloadExe.size_label }}
          </span>
        </a>
      </div>
      <p v-if="clientDownloadSetup.available" class="client-download-hint">{{ t('client.download_setup_hint') }}</p>
    </a-modal>
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { IconMenu, IconLeft, IconRight, IconDown } from '@arco-design/web-vue/es/icon'
import { arcoLocaleMap, loadLocaleMessages } from '@/plugins/i18n'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowBadgesStore } from '@/stores/workflowBadges'
import { useBrandingStore } from '@/stores/branding'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { useEmbedDesktop } from '@/composables/useEmbedDesktop'
import { api, type ApiResponse } from '@/api/client'
import { resetSessionRedirectFlag } from '@/utils/sessionRedirect'
import SideMenu from '@/components/SideMenu.vue'
import MobileTabBar from '@/components/MobileTabBar.vue'
import ProfileModal from '@/components/ProfileModal.vue'
import BrandLogo from '@/components/BrandLogo.vue'
import { useRouter } from 'vue-router'

const { t, locale } = useI18n()
const auth = useAuthStore()
const badges = useWorkflowBadgesStore()
const branding = useBrandingStore()
const router = useRouter()
const { isMobile, isDesktop } = useBreakpoint()
const { isEmbedDesktop } = useEmbedDesktop()
const drawerVisible = ref(false)
const profileVisible = ref(false)
const profileTab = ref('profile')
const currentLocale = ref(locale.value)
const localeOptions = ref<{ label: string; value: string }[]>([])
const siderCollapsedManual = ref(false)
const clientDownloadAvailable = ref(false)
const clientDownloadModalVisible = ref(false)

type ClientPkgInfo = {
  available: boolean
  download_url: string
  size_label: string
}

const emptyPkg = (): ClientPkgInfo => ({
  available: false,
  download_url: '',
  size_label: '',
})

const clientDownloadSetup = ref<ClientPkgInfo>(emptyPkg())
const clientDownloadZip = ref<ClientPkgInfo>(emptyPkg())
const clientDownloadExe = ref<ClientPkgInfo>(emptyPkg())

function formatPkgSize(bytes?: number): string {
  if (!bytes || bytes <= 0) return ''
  return `约 ${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const arcoLocale = computed(() => arcoLocaleMap[locale.value] || arcoLocaleMap['zh-CN'])

const sidebarCollapsed = computed(() => {
  if (isMobile.value) return false
  return siderCollapsedManual.value
})

function onSiderCollapse(collapsed: boolean) {
  if (isDesktop.value) siderCollapsedManual.value = collapsed
}

function toggleSidebar() {
  if (isDesktop.value) siderCollapsedManual.value = !siderCollapsedManual.value
}

async function loadLocales() {
  const res = await api.get<ApiResponse<{ code: string; native_name: string }[]>>('/i18n/locales')
  if (res.data.ok) {
    localeOptions.value = res.data.data.map((x) => ({
      label: x.native_name,
      value: x.code,
    }))
  }
}

async function onLocaleChange(code: string | number | boolean | Record<string, unknown>) {
  const loc = String(code || 'zh-CN')
  if (loc === locale.value) return
  await loadLocaleMessages(loc, true)
  currentLocale.value = loc
  try {
    await api.patch('/auth/me', { locale: loc })
  } catch {
    /* ignore */
  }
}

watch(locale, (v) => {
  currentLocale.value = v
})

function openProfile(tab: string) {
  profileTab.value = tab
  profileVisible.value = true
}

async function loadClientDownloadInfo() {
  if (!auth.user || isEmbedDesktop.value) {
    clientDownloadAvailable.value = false
    clientDownloadSetup.value = emptyPkg()
    clientDownloadZip.value = emptyPkg()
    clientDownloadExe.value = emptyPkg()
    return
  }
  try {
    const res = await api.get<
      ApiResponse<{
        available: boolean
        setup?: { available: boolean; download_url?: string; size_bytes?: number }
        zip?: { available: boolean; download_url?: string; size_bytes?: number }
        exe?: { available: boolean; download_url?: string; size_bytes?: number }
      }>
    >('/client/download-info')
    const data = res.data.data
    clientDownloadAvailable.value = !!data?.available
    clientDownloadSetup.value = {
      available: !!data?.setup?.available,
      download_url: data?.setup?.download_url || '/api/v1/client/download/setup',
      size_label: formatPkgSize(data?.setup?.size_bytes),
    }
    clientDownloadZip.value = {
      available: !!data?.zip?.available,
      download_url: data?.zip?.download_url || '/api/v1/client/download/zip',
      size_label: formatPkgSize(data?.zip?.size_bytes),
    }
    clientDownloadExe.value = {
      available: !!data?.exe?.available,
      download_url: data?.exe?.download_url || '/api/v1/client/download/exe',
      size_label: formatPkgSize(data?.exe?.size_bytes),
    }
  } catch {
    clientDownloadAvailable.value = false
    clientDownloadSetup.value = emptyPkg()
    clientDownloadZip.value = emptyPkg()
    clientDownloadExe.value = emptyPkg()
  }
}

function openClientDownloadModal() {
  if (!clientDownloadAvailable.value) {
    Message.warning('客户端安装包暂未发布，请联系管理员')
    return
  }
  clientDownloadModalVisible.value = true
}

async function handleLogout() {
  await auth.logout()
  badges.reset()
  router.push({ name: 'login' })
}

function onVisibilityChange() {
  if (document.visibilityState === 'visible' && auth.user) {
    void badges.refresh()
  }
}

watch(
  () => auth.user?.id,
  (uid) => {
    if (uid) {
      void badges.refresh(true)
      void loadClientDownloadInfo()
    } else {
      badges.reset()
      clientDownloadAvailable.value = false
    }
  },
  { immediate: true },
)

router.afterEach(() => {
  if (auth.user) void badges.refresh()
})

onMounted(() => {
  document.addEventListener('visibilitychange', onVisibilityChange)
  resetSessionRedirectFlag()
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

loadLocales()
branding.load()
</script>

<style scoped>
.app-shell {
  height: 100dvh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--surface-muted);
}

.app-shell :deep(> .arco-layout-header) {
  flex-shrink: 0;
}

.app-shell :deep(> .arco-layout.app-body) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-h) !important;
  padding: 0 1.25rem !important;
  background: var(--surface) !important;
  border-bottom: 1px solid var(--border);
  box-shadow: none;
  flex-shrink: 0;
}

.app-header-left,
.app-header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.app-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  transition:
    background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out),
    border-color var(--dur-fast) var(--ease-out);
}

.app-icon-btn:hover {
  background: var(--surface-muted);
  color: var(--text);
}

.app-sider-toggle {
  margin-right: 0.15rem;
}

.app-header-brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
}

.app-header-title {
  font-size: 0.9375rem;
  font-weight: 650;
  color: var(--text);
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.app-header-app {
  padding-left: 0.6rem;
  border-left: 1px solid var(--border);
  font-size: 0.75rem;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.app-locale-select {
  width: 6.25rem;
}

.app-user-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  height: 36px;
  padding: 0 0.5rem 0 0.25rem;
  border: 1px solid transparent;
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--text);
  cursor: pointer;
  transition:
    background-color var(--dur-fast) var(--ease-out),
    border-color var(--dur-fast) var(--ease-out);
}

.app-user-chip:hover {
  background: var(--surface-muted);
  border-color: var(--border);
}

.app-user-name {
  max-width: 9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.8125rem;
  font-weight: 500;
}

.app-user-caret {
  font-size: 12px;
  color: var(--text-tertiary);
}

.app-body {
  position: relative;
  min-height: 0;
  flex: 1;
  display: flex;
  overflow: hidden;
}

.app-sider {
  flex-shrink: 0;
  height: 100%;
  overflow: hidden;
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
  box-shadow: none !important;
}

.app-sider :deep(.arco-layout-sider) {
  height: 100% !important;
}

.app-sider :deep(.arco-layout-sider-children) {
  overflow-x: hidden;
  overflow-y: auto;
  padding: 0.5rem 0;
  height: 100%;
  max-height: 100%;
  overscroll-behavior: contain;
}

.app-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--bg);
  padding: 0 !important;
  overscroll-behavior: contain;
}

.app-content-inner {
  padding: 0.875rem 1.25rem 1.25rem;
  width: 100%;
  box-sizing: border-box;
}

@media (min-width: 1024px) {
  .app-content-inner {
    padding: 1rem 1.5rem 1.5rem;
  }
}

@media (max-width: 767px) {
  .app-header {
    padding: 0 0.75rem !important;
  }

  .app-user-name,
  .app-user-caret {
    display: none;
  }

  .app-user-chip {
    padding: 0;
  }

  .app-header-app {
    display: none;
  }
}

.app-password-alert {
  margin: 0 0 1rem;
  border-radius: var(--radius-md);
}

.app-content.has-mobile-tab .app-content-inner {
  padding-bottom: calc(3.5rem + env(safe-area-inset-bottom, 0px));
}

.app-shell--embed {
  background: var(--surface);
}

.app-shell--embed .app-body {
  margin: 0 !important;
}

.app-content--embed {
  height: 100%;
}

.app-content--embed .app-content-inner {
  padding: 0.75rem 1rem 1rem;
  min-height: 100%;
  box-sizing: border-box;
}

.client-download-desc {
  margin: 0 0 0.75rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.client-download-edge-tip {
  margin-bottom: 1rem;
}

.client-download-actions {
  display: flex;
  align-items: stretch;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.client-download-btn {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  min-width: 140px;
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-md);
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.15s ease, background 0.15s ease;
}

.client-download-btn--primary {
  background: var(--brand);
  color: #fff;
}

.client-download-btn--primary:hover {
  opacity: 0.92;
  color: #fff;
}

.client-download-btn--secondary {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border-strong);
}

.client-download-btn--secondary:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.client-download-btn-size {
  margin-top: 2px;
  font-size: 0.75rem;
  font-weight: 400;
  opacity: 0.85;
}

.client-download-hint {
  margin: 0.75rem 0 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
  line-height: 1.5;
}
</style>
