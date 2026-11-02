<template>
  <a-popover
    v-model:popup-visible="menuOpen"
    trigger="click"
    position="right"
    content-class="flow-add-popover"
    :popup-container="popupContainer"
  >
    <button type="button" class="flow-add-btn" :title="t('flowDesign.insert_node')">+</button>
    <template #content>
      <div class="add-menu">
        <button type="button" class="add-item add-approver" @click="pick('approver')">
          <span class="add-icon">审</span>
          <span>{{ t('flowDesign.node_approver') }}</span>
        </button>
        <button type="button" class="add-item add-cc" @click="pick('cc')">
          <span class="add-icon">抄</span>
          <span>{{ t('flowDesign.node_cc') }}</span>
        </button>
        <button type="button" class="add-item add-handler" @click="pick('handler')">
          <span class="add-icon">办</span>
          <span>{{ t('flowDesign.node_handler') }}</span>
        </button>
        <button type="button" class="add-item add-condition" @click="pick('condition')">
          <span class="add-icon">条</span>
          <span>{{ t('flowDesign.node_condition') }}</span>
        </button>
      </div>
    </template>
  </a-popover>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFlowDesignerPopup } from '@/composables/useFlowDesignerPopup'

const { t } = useI18n()
const emit = defineEmits<{ select: [type: string] }>()
const menuOpen = ref(false)
const popupContainer = useFlowDesignerPopup()

function pick(type: string) {
  emit('select', type)
  menuOpen.value = false
}
</script>

<style scoped>
.flow-add-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid var(--border-input);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: var(--app-font-18);
  line-height: 1;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: all 0.15s;
}

.flow-add-btn:hover {
  border-color: var(--brand);
  color: var(--brand-text);
  transform: scale(1.05);
}

.add-menu {
  display: flex;
  gap: var(--app-space-8);
  padding: var(--app-space-4);
}

.add-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--app-space-6);
  min-width: 72px;
  padding: var(--app-space-10) var(--app-space-8);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  cursor: pointer;
  font-size: var(--app-font-xs);
  color: var(--text);
}

.add-item:hover {
  border-color: var(--brand);
  background: var(--surface-muted);
}

.add-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--app-font-sm);
  font-weight: 600;
  color: #fff;
}

.add-approver .add-icon {
  background: #ff7d00;
}

.add-cc .add-icon {
  background: #00b42a;
}

.add-handler .add-icon {
  background: #0fc6c2;
}

.add-condition .add-icon {
  background: var(--text-tertiary);
}
</style>
