<template>
  <div class="brand-logo" :class="`brand-logo--${size}`" :title="title">
    <img
      v-if="showImage"
      :src="src"
      alt=""
      class="brand-logo-img"
      @error="onImageError"
    />
    <span v-else class="brand-logo-fallback">{{ fallbackLetter }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
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
const failed = ref(false)

const src = computed(() => props.imageUrl || branding.logoUrl || '')
const showImage = computed(() => Boolean(src.value) && !failed.value)

watch(src, () => {
  failed.value = false
})

function onImageError() {
  failed.value = true
}

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
  border-radius: 10px;
  overflow: hidden;
  background: var(--brand, #5034ff);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
}

.brand-logo--sm {
  width: 30px;
  height: 30px;
  border-radius: 8px;
}

.brand-logo--md {
  width: 38px;
  height: 38px;
  border-radius: 10px;
}

.brand-logo--lg {
  width: 44px;
  height: 44px;
  border-radius: 12px;
}

.brand-logo:has(.brand-logo-img) {
  background: var(--surface, #fff);
  box-shadow: none;
  border: 1px solid var(--border, #e8e7e2);
}

.brand-logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.brand-logo-fallback {
  color: #fff;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
}

.brand-logo--sm .brand-logo-fallback {
  font-size: 0.85rem;
}

.brand-logo--md .brand-logo-fallback {
  font-size: 1rem;
}

.brand-logo--lg .brand-logo-fallback {
  font-size: 1.15rem;
}
</style>
