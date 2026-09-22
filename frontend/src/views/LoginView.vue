<template>
  <a-config-provider :locale="arcoLocale">
    <div class="login-page">
      <section class="login-panel">
        <div class="login-panel-inner">
          <div class="login-locale-wrap">
            <LoginLocaleSwitcher />
          </div>

          <div class="login-brand">
            <BrandLogo size="lg" />
            <div class="login-brand-text">
              <span class="login-app-name">{{ branding.headerTitle() }}</span>
              <span v-if="branding.companyName" class="login-company">{{ branding.companyName }}</span>
            </div>
          </div>

          <h1 class="login-heading">{{ t('auth.welcome') }}</h1>
          <p class="login-sub">{{ t('auth.login_hint') }}</p>

          <div class="login-mode">
            <button
              type="button"
              class="login-mode-btn"
              :class="{ active: mode === 'password' }"
              @click="mode = 'password'"
            >
              {{ t('auth.password') }}
            </button>
            <button
              type="button"
              class="login-mode-btn"
              :class="{ active: mode === 'email' }"
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

          <a-form v-else layout="vertical" class="login-form" @submit-success="loginEmail">
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

          <p v-if="branding.companyName" class="login-footer">{{ branding.companyName }}</p>
        </div>
      </section>

      <aside class="login-visual" aria-hidden="true">
        <div class="login-visual-bg" />
        <div class="login-visual-content">
          <p class="visual-tag">{{ t('login.visual_tag') }}</p>
          <h2 class="visual-title">
            {{ t('login.visual_title_1') }}<br />{{ t('login.visual_title_2') }}
          </h2>
          <p class="visual-desc">{{ t('login.visual_desc') }}</p>
          <div class="visual-cards">
            <div class="visual-card visual-card-1">
              <span class="visual-card-label">{{ t('login.card1_label') }}</span>
              <strong>{{ t('login.card1_strong') }}</strong>
            </div>
            <div class="visual-card visual-card-2">
              <span class="visual-card-label">{{ t('login.card2_label') }}</span>
              <strong>{{ t('login.card2_strong') }}</strong>
            </div>
            <div class="visual-card visual-card-3">
              <span class="visual-card-label">{{ t('login.card3_label') }}</span>
              <strong>{{ t('login.card3_strong') }}</strong>
            </div>
          </div>
        </div>
      </aside>
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
  min-height: 100dvh;
  display: flex;
  background: var(--surface);
}

.login-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1.5rem;
  min-width: 0;
}

.login-panel-inner {
  width: 100%;
  max-width: 400px;
  position: relative;
}

.login-locale-wrap {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 2;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
  padding-right: 140px;
}

.login-brand-text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.login-app-name {
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--text);
}

.login-company {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.login-heading {
  margin: 0 0 0.5rem;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text);
}

.login-sub {
  margin: 0 0 1.75rem;
  font-size: 0.9375rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.login-mode {
  display: flex;
  gap: 0.35rem;
  padding: 0.25rem;
  background: var(--surface-muted);
  border-radius: var(--radius-md);
  margin-bottom: 1.5rem;
}

.login-mode-btn {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0.55rem 0.75rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease,
    box-shadow 0.15s ease;
}

.login-mode-btn.active {
  background: var(--surface);
  color: var(--brand);
  box-shadow: var(--shadow-xs);
}

.login-form :deep(.arco-form-item) {
  margin-bottom: 1rem;
}

.login-field :deep(.arco-input-wrapper),
.login-field :deep(.arco-input-password) {
  border-radius: var(--radius-sm);
  background: var(--surface);
  border-color: var(--border);
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
  border-radius: var(--radius-sm) !important;
}

.login-submit {
  margin-top: 0.5rem;
  height: 48px !important;
  border-radius: var(--radius-sm) !important;
  font-weight: 600 !important;
  font-size: 1rem !important;
}

.login-divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 1.25rem 0;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}

.login-divider::before,
.login-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.login-sso {
  height: 48px !important;
  border-radius: var(--radius-sm) !important;
  border-color: var(--border) !important;
  background: var(--surface) !important;
  font-weight: 500 !important;
}

.login-error {
  margin: 1rem 0 0;
  padding: 0.65rem 0.85rem;
  font-size: 0.875rem;
  color: #c42b2b;
  background: #fff2f0;
  border-radius: var(--radius-sm);
  text-align: center;
}

.login-footer {
  margin: 2rem 0 0;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}

/* 右侧视觉区 — 桌面 */
.login-visual {
  display: none;
  width: 46%;
  max-width: 640px;
  position: relative;
  overflow: hidden;
}

.login-visual-bg {
  position: absolute;
  inset: 0;
  background: var(--brand-gradient);
  opacity: 0.95;
}

.login-visual-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 80%, rgba(255, 255, 255, 0.15) 0%, transparent 45%),
    radial-gradient(circle at 80% 20%, rgba(255, 107, 107, 0.25) 0%, transparent 40%);
}

.login-visual-content {
  position: relative;
  z-index: 1;
  height: 100%;
  padding: 3.5rem 3rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: #fff;
}

.visual-tag {
  display: inline-block;
  width: fit-content;
  padding: 0.35rem 0.85rem;
  font-size: 0.8125rem;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  backdrop-filter: blur(8px);
  margin-bottom: 1.25rem;
}

.visual-title {
  margin: 0 0 1rem;
  font-size: clamp(1.75rem, 3vw, 2.25rem);
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.02em;
}

.visual-desc {
  margin: 0 0 2.5rem;
  font-size: 1rem;
  line-height: 1.6;
  opacity: 0.92;
  max-width: 22rem;
}

.visual-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  max-width: 28rem;
}

.visual-card {
  padding: 1rem 0.85rem;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.visual-card-label {
  display: block;
  font-size: 0.75rem;
  opacity: 0.85;
  margin-bottom: 0.35rem;
}

.visual-card strong {
  font-size: 0.9375rem;
  font-weight: 700;
}

.visual-card-2 {
  transform: translateY(8px);
}

@media (min-width: 900px) {
  .login-visual {
    display: flex;
  }
}

@media (max-width: 899px) {
  .login-page {
    background: linear-gradient(180deg, var(--brand-soft) 0%, var(--surface) 28%);
  }

  .login-brand {
    padding-right: 0;
    margin-top: 2.5rem;
  }

  .login-locale-wrap {
    top: -0.5rem;
    right: 0;
  }
}
</style>
