<template>
  <a-timeline :class="{ 'approval-timeline--compact': compact }">
    <a-timeline-item v-for="item in items" :key="item.id">
      <div class="approval-timeline-item">
        <div class="approval-timeline-main">
          <div class="approval-timeline-text">
            <span v-if="showActor" class="approval-timeline-actor">{{ item.actor_name || '—' }}</span>
            {{ timelineActionLabel(item.action) }}
            <span v-if="item.comment"> — {{ item.comment }}</span>
            <span v-else-if="!showActor"> — 无</span>
          </div>
          <div class="approval-timeline-time">{{ formatPrintDateTime(item.created_at) }}</div>
        </div>
        <img
          v-if="signSrc(item)"
          :src="signSrc(item)!"
          alt="手写签名"
          class="approval-timeline-sign"
        />
      </div>
    </a-timeline-item>
  </a-timeline>
</template>

<script setup lang="ts">
import { formatPrintDateTime, signatureImageSrc, timelineActionLabel } from '@/utils/printFormat'

export interface ApprovalTimelineItem {
  id: number
  action: string
  comment?: string | null
  created_at?: string | null
  actor_name?: string
  signature_path?: string
  signature_data?: string
}

withDefaults(
  defineProps<{
    items: ApprovalTimelineItem[]
    /** 是否显示操作人姓名（申请详情页） */
    showActor?: boolean
    /** 紧凑模式：减少环节间距 */
    compact?: boolean
  }>(),
  { showActor: true, compact: false },
)

function signSrc(item: ApprovalTimelineItem) {
  return signatureImageSrc(item)
}
</script>

<style scoped>
.approval-timeline-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.approval-timeline-main {
  flex: 1;
  min-width: 0;
}

.approval-timeline-text {
  line-height: 1.5;
  word-break: break-word;
}

.approval-timeline-actor {
  font-weight: 600;
  margin-right: 4px;
}

.approval-timeline-time {
  margin-top: 2px;
  font-size: 0.75rem;
  color: var(--text-tertiary, #9699a6);
}

.approval-timeline--compact :deep(.arco-timeline-item) {
  min-height: 0;
}

.approval-timeline--compact :deep(.arco-timeline-item-content) {
  margin-bottom: 0;
  padding-bottom: 4px;
}

.approval-timeline--compact :deep(.arco-timeline-item:last-child .arco-timeline-item-content) {
  padding-bottom: 0;
}

.approval-timeline--compact .approval-timeline-text {
  line-height: 1.4;
}

.approval-timeline--compact .approval-timeline-time {
  margin-top: 1px;
}

.approval-timeline-sign {
  flex-shrink: 0;
  display: block;
  max-height: 48px;
  max-width: 120px;
  object-fit: contain;
}
</style>
