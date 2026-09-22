<template>
  <a-select
    :model-value="currentLocale"
    :options="localeOptions"
    size="small"
    class="login-locale-select"
    :placeholder="t('common.language')"
    @change="onChange"
  >
    <template #prefix>
      <icon-language />
    </template>
  </a-select>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { IconLanguage } from '@arco-design/web-vue/es/icon'
import { api, type ApiResponse } from '@/api/client'
import { loadLocaleMessages } from '@/plugins/i18n'

const { t, locale } = useI18n()
const currentLocale = ref(locale.value)
const localeOptions = ref<{ label: string; value: string }[]>([])

async function loadLocales() {
  const res = await api.get<ApiResponse<{ code: string; native_name: string }[]>>('/i18n/locales')
  if (res.data.ok) {
    localeOptions.value = res.data.data.map((x) => ({
      label: x.native_name,
      value: x.code,
    }))
  } else {
    localeOptions.value = [
      { label: '简体中文', value: 'zh-CN' },
      { label: 'English', value: 'en-US' },
    ]
  }
}

async function onChange(code: string | number | boolean | Record<string, unknown>) {
  const loc = String(code || 'zh-CN')
  if (loc === locale.value) return
  await loadLocaleMessages(loc, true)
  currentLocale.value = loc
}

watch(locale, (v) => {
  currentLocale.value = v
})

onMounted(loadLocales)
</script>

<style scoped>
.login-locale-select {
  width: 132px;
}

.login-locale-select :deep(.arco-select-view) {
  border-radius: var(--radius-sm);
  background: var(--surface);
}
</style>
