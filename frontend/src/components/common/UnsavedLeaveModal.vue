<template>
  <a-modal
    :visible="visible"
    :title="t('unsaved.title')"
    :mask-closable="false"
    :esc-to-close="false"
    :closable="false"
    :width="420"
    unmount-on-close
    @update:visible="emit('update:visible', $event)"
  >
    <p class="unsaved-message">{{ t('unsaved.message') }}</p>
    <template #footer>
      <a-space wrap>
        <a-button @click="emit('cancel')">{{ t('unsaved.cancel') }}</a-button>
        <a-button status="warning" @click="emit('discard')">{{ t('unsaved.leave_without_save') }}</a-button>
        <a-button type="primary" :loading="saving" @click="emit('save-and-leave')">
          {{ t('unsaved.save_and_leave') }}
        </a-button>
      </a-space>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  visible: boolean
  saving?: boolean
}>()

const emit = defineEmits<{
  'update:visible': [boolean]
  cancel: []
  discard: []
  'save-and-leave': []
}>()

const { t } = useI18n()
</script>

<style scoped>
.unsaved-message {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--text-secondary, #4e5969);
}
</style>
