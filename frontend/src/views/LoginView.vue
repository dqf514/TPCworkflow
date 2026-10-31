<template>
  <a-config-provider :locale="arcoLocale">
    <div class="login-page">
      <aside class="login-visual" aria-hidden="true">
        <div class="login-visual-grid" />
        <div class="login-visual-glow" />
        <div class="login-visual-inner">
          <div class="visual-brand">
            <BrandLogo size="md" />
            <span class="visual-brand-name">{{ branding.headerTitle() }}</span>
          </div>

          <div class="visual-copy">
            <span class="visual-eyebrow">{{ t('login.visual_tag') }}</span>
            <h2 class="visual-title">
              {{ t('login.visual_title_1') }}<br />{{ t('login.visual_title_2') }}
            </h2>
            <p class="visual-desc">{{ t('login.visual_desc') }}</p>
          </div>

          <ul class="visual-points">
            <li class="visual-point">
              <span class="visual-point-num">01</span>
              <div class="visual-point-body">
                <span class="visual-point-label">{{ t('login.card1_label') }}</span>
                <strong>{{ t('login.card1_strong') }}</strong>
              </div>
            </li>
            <li class="visual-point">
              <span class="visual-point-num">02</span>
              <div class="visual-point-body">
                <span class="visual-point-label">{{ t('login.card2_label') }}</span>
                <strong>{{ t('login.card2_strong') }}</strong>
              </div>
            </li>
            <li class="visual-point">
              <span class="visual-point-num">03</span>
              <div class="visual-point-body">
                <span class="visual-point-label">{{ t('login.card3_label') }}</span>
                <strong>{{ t('login.card3_strong') }}</strong>
              </div>
            </li>
          </ul>

          <p class="visual-foot">{{ branding.companyName || branding.appName }}</p>
        </div>
      </aside>

      <section class="login-panel">
        <div class="login-panel-inner">
          <div class="login-locale-wrap">
            <LoginLocaleSwitcher />
          </div>

          <div class="login-mobile-brand">
            <BrandLogo size="sm" />
            <span class="login-mobile-brand-name">{{ branding.headerTitle() }}</span>
          </div>

          <h1 class="login-heading">{{ t('auth.welcome') }}</h1>
          <p class="login-sub">{{ t('auth.login_hint') }}</p>

          <div class="login-mode" role="tablist">
            <button
              type="button"
              role="tab"
              class="login-mode-btn"
              :class="{ active: mode === 'password' }"
              :aria-selected="mode === 'password'"
              @click="mode = 'password'"
            >
              {{ t('auth.password') }}
            </button>
            <button
              type="button"
              role="tab"
              class="login-mode-btn"
              :class="{ active: mode === 'email' }"
              :aria-selected="mode === 'email'"
              @click="mode = 'email'"
            >
              {{ t('auth.email_code') }}
            </button>
          </div>

          <a-form
            v-if="mode === 'password'"
            :model="pwdForm"
            layout="vertical"
            class="login-form"
            @submit-success="loginPassword"
          >
            <a-form-item :label="t('auth.username')" hide-label class="login-field">
              <a-input
                v-model="pwdForm.identifier"
                size="large"
                :placeholder="t('auth.identifier_placeholder')"
                allow-clear
              />
            </a-form-item>
            <a-form-item :label="t('auth.password')" hide-label class="login-field">
              <a-input-password
                v-model="pwdForm.password"
                size="large"
                :placeholder="t('auth.password_placeholder')"
              />
            </a-form-item>
            <LoginCaptcha
              ref="pwdCaptchaRef"
              v-model="captchaCode"
              @update:captcha-id="captchaId = $event"
            />
            <a-button
              type="primary"
              html-type="submit"
              long
              size="large"
              class="login-submit"
              :loading="loading"
            >
              {{ t('auth.login') }}
            </a-button>
          </a-form>

          <a-form v-else :model="emailForm" layout="vertical" class="login-form" @submit-success="loginEmail">
            <a-form-item :label="t('auth.email')" hide-label class="login-field">
              <a-input
                v-model="emailForm.email"
                size="large"
                :placeholder="t('auth.work_email_placeholder')"
                allow-clear
              />
            </a-form-item>
            <a-form-item :label="t('auth.email_code')" hide-label class="login-field">
              <div class="login-code-row">
                <a-input
                  v-model="emailForm.code"
                  size="large"
                  :placeholder="t('auth.code_placeholder')"
                  class="login-code-input"
                />
                <a-button
                  size="large"
                  class="login-code-btn"
                  :loading="sendingCode"
                  @click="sendEmailCode"
                >
                  {{ t('auth.send_code') }}
                </a-button>
              </div>
            </a-form-item>
            <LoginCaptcha
              ref="emailCaptchaRef"
              v-model="captchaCode"
              @update:captcha-id="captchaId = $event"
            />
            <a-button
              type="primary"
              html-type="submit"
              long
              size="large"
              class="login-submit"
              :loading="loading"
            >
              {{ t('auth.login') }}
            </a-button>
          </a-form>

          <template v-if="methods.azure_sso">
            <div class="login-divider">
              <span>{{ t('auth.or') }}</span>
            </div>
            <a-button long size="large" class="login-sso" @click="loginAzure">
              {{ t('auth.azure_login') }}
            </a-button>
          </template>

          <p v-if="error" class="login-error" role="alert">{{ error }}</p>
        </div>
      </section>
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { useRoute, useRouter } from 'vue-router'
import { APP_DISPLAY_NAME } from '@/constants/branding'
import { useAuthStore } from '@/stores/auth'
import { useBrandingStore } from '@/stores/branding'
import { api, type ApiResponse } from '@/api/client'
import { resetSessionRedirectFlag } from '@/utils/sessionRedirect'
import { arcoLocaleMap } from '@/plugins/i18n'
import BrandLogo from '@/components/BrandLogo.vue'
import LoginCaptcha from '@/components/LoginCaptcha.vue'
import LoginLocaleSwitcher from '@/components/LoginLocaleSwitcher.vue'

const { t, locale } = useI18n()
const auth = useAuthStore()
const branding = useBrandingStore()
const router = useRouter()
const route = useRoute()

const arcoLocale = computed(() => arcoLocaleMap[locale.value] || arcoLocaleMap['zh-CN'])

const mode = ref<'password' | 'email'>('password')
const loading = ref(false)
const sendingCode = ref(false)
const error = ref('')
const methods = ref({ azure_sso: false })

const pwdForm = reactive({ identifier: '', password: '' })
const emailForm = reactive({ email: '', code: '' })
const captchaCode = ref('')
const captchaId = ref('')
const pwdCaptchaRef = ref<InstanceType<typeof LoginCaptcha> | null>(null)
const emailCaptchaRef = ref<InstanceType<typeof LoginCaptcha> | null>(null)

function activeCaptchaRef() {
  return mode.value === 'password' ? pwdCaptchaRef.value : emailCaptchaRef.value
}

function refreshCaptcha() {
  captchaCode.value = ''
  activeCaptchaRef()?.refresh()
}

watch(mode, async () => {
  captchaCode.value = ''
  captchaId.value = ''
  await nextTick()
  activeCaptchaRef()?.refresh()
})

async function loginPassword() {
  if (!captchaCode.value.trim()) {
    error.value = t('auth.captcha_required')
    return
  }
  loading.value = true
  error.value = ''
  try {
    await auth.login(pwdForm.identifier, pwdForm.password, false, {
      captcha_id: captchaId.value,
      captcha_code: captchaCode.value.trim(),
    })
    router.push((route.query.redirect as string) || '/')
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('auth.login_failed')
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

async function sendEmailCode() {
  if (!emailForm.email.trim()) {
    Message.warning(t('auth.fill_email_first'))
    return
  }
  if (!captchaCode.value.trim()) {
    Message.warning(t('auth.captcha_required'))
    return
  }
  sendingCode.value = true
  try {
    await api.post('/auth/email-code/send', {
      email: emailForm.email,
      captcha_id: captchaId.value,
      captcha_code: captchaCode.value.trim(),
    })
    Message.success(t('auth.code_sent'))
    refreshCaptcha()
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('auth.send_failed'))
    refreshCaptcha()
  } finally {
    sendingCode.value = false
  }
}

async function loginEmail() {
  if (!captchaCode.value.trim()) {
    error.value = t('auth.captcha_required')
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await api.post('/auth/login', {
      mode: 'email_code',
      email: emailForm.email,
      code: emailForm.code,
      captcha_id: captchaId.value,
      captcha_code: captchaCode.value.trim(),
    })
    if (res.data.ok) {
      auth.user = res.data.data
      if (res.data.data.need_set_password) {
        Message.warning(res.data.message || t('auth.set_password_hint'))
      }
      router.push((route.query.redirect as string) || '/')
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('auth.email_login_failed')
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

async function loginAzure() {
  const res = await api.get<ApiResponse<{ url: string }>>('/auth/azure/login-url')
  if (res.data.ok && res.data.data.url) window.location.href = res.data.data.url
}

onMounted(async () => {
  resetSessionRedirectFlag()
  if (route.query.reason === 'session_expired') {
    Message.warning('登录已过期，请重新登录')
  }
  const res = await api.get<
    ApiResponse<{
      azure_sso?: boolean
      company_name?: string
      company_logo_url?: string | null
      app_name?: string
    }>
  >('/auth/login-methods')
  if (res.data.ok) {
    methods.value = { azure_sso: !!res.data.data.azure_sso }
    branding.companyName = res.data.data.company_name || ''
    branding.appName = res.data.data.app_name || APP_DISPLAY_NAME
    branding.setLogoUrl(res.data.data.company_logo_url)
    branding.loaded = true
  }
  if (route.query.azure === 'ok') {
    await auth.fetchMe()
    router.replace('/')
  }
})
</script>

<style scoped>
.login-page {
  display: flex;
  min-height: 100dvh;
  background: var(--surface);
}

/* —— 品牌侧 —— */
.login-visual {
  position: relative;
  display: none;
  width: 46%;
  max-width: 660px;
  overflow: hidden;
  background: #131418;
  color: #fff;
}

.login-visual-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 52px 52px;
  mask-image: radial-gradient(ellipse at 30% 15%, #000 10%, transparent 72%);
}

.login-visual-glow {
  position: absolute;
  top: -220px;
  right: -180px;
  width: 560px;
  height: 560px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(80, 52, 255, 0.5) 0%, transparent 66%);
  filter: blur(4px);
}

.login-visual-inner {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 3rem 3.25rem;
  gap: 3rem;
}

.visual-brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}

.visual-brand .brand-logo {
  border-color: rgba(255, 255, 255, 0.16);
}

.visual-brand-name {
  font-size: 0.9375rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: rgba(255, 255, 255, 0.92);
}

.visual-copy {
  margin-top: auto;
}

.visual-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.1rem;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.55);
}

.visual-eyebrow::before {
  content: '';
  width: 18px;
  height: 1px;
  background: var(--brand);
}

.visual-title {
  margin: 0 0 1rem;
  font-size: clamp(2rem, 2.8vw, 2.6rem);
  font-weight: 650;
  line-height: 1.24;
  letter-spacing: -0.03em;
  color: #fff;
}

.visual-desc {
  max-width: 24rem;
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.62);
}

.visual-points {
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.visual-point {
  display: flex;
  align-items: baseline;
  gap: 1.1rem;
  padding: 1rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.visual-point-num {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.38);
  font-variant-numeric: tabular-nums;
}

.visual-point-body {
  display: flex;
  flex: 1;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
}

.visual-point-label {
  font-size: 0.8125rem;
  color: rgba(255, 255, 255, 0.5);
}

.visual-point-body strong {
  font-size: 0.9375rem;
  font-weight: 550;
  color: rgba(255, 255, 255, 0.94);
}

.visual-foot {
  margin: 0;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.36);
}

/* —— 表单侧 —— */
.login-panel {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-width: 0;
  padding: 2.5rem 1.5rem;
  background: var(--surface);
}

.login-panel-inner {
  width: 100%;
  max-width: 376px;
}

.login-locale-wrap {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 2.5rem;
}

.login-mobile-brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 2rem;
}

.login-mobile-brand-name {
  font-size: 0.9375rem;
  font-weight: 650;
  color: var(--text);
}

.login-heading {
  margin: 0 0 0.5rem;
  font-size: 1.875rem;
  font-weight: 650;
  letter-spacing: -0.035em;
  color: var(--text);
  line-height: 1.25;
}

.login-sub {
  margin: 0 0 2rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.login-mode {
  display: flex;
  gap: 0.25rem;
  padding: 0.25rem;
  margin-bottom: 1.5rem;
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.login-mode-btn {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: 0.8125rem;
  font-weight: 550;
  color: var(--text-secondary);
  cursor: pointer;
  transition:
    background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out),
    box-shadow var(--dur-fast) var(--ease-out);
}

.login-mode-btn:hover {
  color: var(--text);
}

.login-mode-btn.active {
  background: var(--surface);
  border-color: var(--border);
  color: var(--text);
  box-shadow: var(--shadow-xs);
}

.login-form :deep(.arco-form-item) {
  margin-bottom: 0.85rem;
}

.login-field :deep(.arco-input-wrapper),
.login-field :deep(.arco-input-password) {
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--surface);
  border-color: var(--border-strong);
}

.login-field :deep(.arco-input-wrapper:hover),
.login-field :deep(.arco-input-password:hover) {
  border-color: var(--border-input);
}

.login-field :deep(.arco-input-wrapper.arco-input-focus),
.login-field :deep(.arco-input-password.arco-input-focus) {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(80, 52, 255, 0.14);
}

.login-code-row {
  display: flex;
  gap: 0.5rem;
  width: 100%;
}

.login-code-input {
  flex: 1;
  min-width: 0;
}

.login-code-btn {
  flex-shrink: 0;
  height: 44px !important;
  border-radius: var(--radius-md) !important;
}

.login-submit {
  height: 46px !important;
  margin-top: 0.35rem;
  border-radius: var(--radius-md) !important;
  font-weight: 600 !important;
  font-size: 0.9375rem !important;
}

.login-divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 1.35rem 0;
  color: var(--text-tertiary);
  font-size: 0.75rem;
}

.login-divider::before,
.login-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.login-sso {
  height: 46px !important;
  border-radius: var(--radius-md) !important;
  border-color: var(--border-strong) !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  font-weight: 500 !important;
}

.login-sso:hover {
  border-color: var(--border-input) !important;
  background: var(--surface-muted) !important;
}

.login-error {
  margin: 1rem 0 0;
  padding: 0.65rem 0.85rem;
  border: 1px solid #f4d3cd;
  border-radius: var(--radius-md);
  background: var(--danger-soft);
  color: var(--danger);
  font-size: 0.8125rem;
  line-height: 1.5;
  text-align: center;
}

@media (min-width: 900px) {
  .login-visual {
    display: flex;
  }

  .login-mobile-brand {
    display: none;
  }

  .login-locale-wrap {
    margin-bottom: 3rem;
  }
}

@media (max-width: 899px) {
  .login-page {
    background: var(--surface);
  }

  .login-panel {
    align-items: flex-start;
    padding: 1.25rem 1.25rem 2.5rem;
  }

  .login-panel-inner {
    max-width: 420px;
    margin: 0 auto;
  }

  .login-locale-wrap {
    margin-bottom: 1.5rem;
  }

  .login-heading {
    font-size: 1.625rem;
  }
}
</style>
