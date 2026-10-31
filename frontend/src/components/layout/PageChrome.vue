<template>
  <div class="page-chrome">
    <header v-if="$slots.title || $slots.actions || description" class="page-chrome-head">
      <div class="page-chrome-head-main">
        <slot name="title" />
        <p v-if="description" class="page-chrome-desc">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="page-chrome-actions">
        <slot name="actions" />
      </div>
    </header>

    <div class="page-chrome-body" :class="{ 'page-chrome-body--flush': flush }">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import { setPageHeaderTitle } from '@/composables/usePageHeader'

const props = defineProps<{
  title?: string
  description?: string
  /** 内容区无内边距（表格全宽等） */
  flush?: boolean
}>()

watch(
  () => props.title,
  (value) => {
    if (value) setPageHeaderTitle(value)
  },
  { immediate: true },
)

onBeforeUnmount(() => setPageHeaderTitle(''))
</script>

<style scoped>
.page-chrome {
  width: 100%;
  min-width: 0;
}

.page-chrome-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.page-chrome-desc {
  margin: 0;
  font-size: var(--app-font-sm, 14px);
  color: var(--text-secondary);
  line-height: 1.45;
  max-width: 48rem;
}

.page-chrome-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.page-chrome-body {
  min-width: 0;
}

.page-chrome-body--flush :deep(.arco-table) {
  border-radius: var(--radius-lg);
  overflow: hidden;
}
</style>
