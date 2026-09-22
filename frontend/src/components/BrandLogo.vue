<template>
  <div class="brand-logo" :class="`brand-logo--${size}`" :title="title">
    <img
      v-if="src"
      :src="src"
      alt="组织 Logo"
      class="brand-logo-img"
    />
    <span v-else class="brand-logo-fallback">{{ fallbackLetter }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useBrandingStore } from '@/stores/branding'

const props = withDefaults(
  defineProps<{
    size?: 'sm' | 'md' | 'lg'
    /** 无 Logo 时显示的字母，默认取公司名称首字 */
    fallback?: string
    /** 覆盖品牌库中的 Logo 地址（设置页预览用） */
    imageUrl?: string
    title?: string
  }>(),
  { size: 'md', title: '组织 Logo' },
)

const branding = useBrandingStore()

const src = computed(() => props.imageUrl || branding.logoUrl || '')

const fallbackLetter = computed(() => {
  if (props.fallback) return props.fallback.slice(0, 1).toUpperCase()
  const name = branding.companyName || branding.appName || 'T'
  return name.slice(0, 1).toUpperCase()
})
</script>

<style scoped>
.brand-logo {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  overflow: hidden;
  background: var(--brand-gradient, linear-gradient(135deg, #5034ff, #7b61ff));
  box-shadow: 0 4px 14px rgba(80, 52, 255, 0.28);
}

.brand-logo--sm {
  width: 32px;
  height: 32px;
  border-radius: 8px;
}

.brand-logo--md {
  width: 40px;
  height: 40px;
  border-radius: 10px;
}

.brand-logo--lg {
  width: 48px;
  height: 48px;
  border-radius: 12px;
}

.brand-logo:has(.brand-logo-img) {
  background: var(--surface, #fff);
  box-shadow: none;
  border: 1px solid var(--border, #e6e9ef);
}

.brand-logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.brand-logo-fallback {
  color: #fff;
  font-weight: 800;
  line-height: 1;
}

.brand-logo--sm .brand-logo-fallback {
  font-size: 0.9rem;
}

.brand-logo--md .brand-logo-fallback {
  font-size: 1.05rem;
}

.brand-logo--lg .brand-logo-fallback {
  font-size: 1.25rem;
}
</style>
