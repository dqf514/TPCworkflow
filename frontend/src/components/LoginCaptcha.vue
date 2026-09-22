<template>
  <a-form-item hide-label class="login-captcha-field">
    <div class="login-captcha">
      <a-input
        :model-value="modelValue"
        size="large"
        :placeholder="t('auth.captcha_label')"
        :max-length="4"
        allow-clear
        autocomplete="off"
        class="login-captcha-input"
        @update:model-value="emit('update:modelValue', $event)"
      />
      <button
        type="button"
        class="login-captcha-img"
        :title="loading ? t('auth.captcha_loading') : t('auth.captcha_refresh')"
        :disabled="loading"
        @click="refresh"
      >
        <img v-if="image" :src="image" :alt="t('auth.captcha_alt')" width="148" height="52" />
        <span v-else class="login-captcha-placeholder">{{ t('auth.captcha_loading') }}</span>
      </button>
    </div>
    <p class="login-captcha-tip">{{ t('auth.captcha_tip') }}</p>
  </a-form-item>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api, type ApiResponse } from '@/api/client'

const { t } = useI18n()

defineProps<{ modelValue: string }>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:captchaId': [id: string]
}>()

const captchaId = ref('')
const image = ref('')
const loading = ref(false)

async function refresh() {
  loading.value = true
  emit('update:modelValue', '')
  try {
    const res = await api.get<ApiResponse<{ captcha_id: string; image: string }>>('/auth/captcha')
    if (res.data.ok) {
      captchaId.value = res.data.data.captcha_id
      image.value = res.data.data.image
      emit('update:captchaId', captchaId.value)
    }
  } finally {
    loading.value = false
  }
}

defineExpose({ refresh, captchaId })

onMounted(refresh)
</script>

<style scoped>
.login-captcha {
  display: flex;
  gap: 0.5rem;
  width: 100%;
  align-items: stretch;
}

.login-captcha-input {
  flex: 1;
  min-width: 0;
}

.login-captcha-img {
  flex-shrink: 0;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  cursor: pointer;
  overflow: hidden;
  line-height: 0;
  transition: border-color 0.15s ease;
}

.login-captcha-img:hover:not(:disabled) {
  border-color: var(--brand);
}

.login-captcha-img:disabled {
  opacity: 0.7;
  cursor: wait;
}

.login-captcha-img img {
  display: block;
  width: 118px;
  height: 44px;
  object-fit: cover;
}

.login-captcha-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 118px;
  height: 44px;
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.login-captcha-tip {
  margin: 0.35rem 0 0;
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.login-captcha-field :deep(.arco-form-item-content) {
  flex-direction: column;
  align-items: stretch;
}
</style>
