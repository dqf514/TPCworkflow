<template>
  <button
    type="button"
    class="att-file-link"
    :title="name"
    @click="onClick"
  >
    <slot>{{ displayName }}</slot>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AttachmentFileItem } from '@/components/form/AttachmentField.vue'
import { openAttachmentPreview } from '@/composables/useAttachmentPreview'

const props = withDefaults(
  defineProps<{
    file: AttachmentFileItem | { name?: string; url?: string; path?: string; size?: number }
    fieldLabel?: string
    truncate?: boolean
  }>(),
  { truncate: false },
)

const name = computed(() => String(props.file.name || '未命名附件'))

const displayName = computed(() => {
  const n = name.value
  if (!props.truncate || n.length <= 14) return n
  return `${n.slice(0, 6)}…${n.slice(-5)}`
})

function onClick() {
  openAttachmentPreview(props.file, props.fieldLabel)
}
</script>

<style scoped>
.att-file-link {
  padding: 0;
  border: none;
  background: none;
  color: rgb(var(--primary-6, 22 93 255));
  font: inherit;
  font-size: inherit;
  line-height: inherit;
  cursor: pointer;
  text-align: left;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.att-file-link:hover {
  text-decoration: underline;
}
</style>
