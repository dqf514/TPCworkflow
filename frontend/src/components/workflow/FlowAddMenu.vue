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
  border: 1px solid #c9cdd4;
  background: #fff;
  color: #4e5969;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
  transition: all 0.15s;
}

.flow-add-btn:hover {
  border-color: #165dff;
  color: #165dff;
  transform: scale(1.05);
}

.add-menu {
  display: flex;
  gap: 8px;
  padding: 4px;
}

.add-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 72px;
  padding: 10px 8px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
  color: #1d2129;
}

.add-item:hover {
  border-color: #165dff;
  background: #f7f8fa;
}

.add-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
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
  background: #86909c;
}
</style>
