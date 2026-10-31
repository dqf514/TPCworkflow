<template>
  <ol v-if="items.length" class="approval-timeline" :class="{ 'approval-timeline--compact': compact }">
    <li
      v-for="item in items"
      :key="item.id"
      class="approval-timeline-item"
      :class="`is-${actionTone(item.action)}`"
    >
      <span class="approval-timeline-dot" aria-hidden="true" />
      <div class="approval-timeline-body">
        <div class="approval-timeline-head">
          <span v-if="showActor" class="approval-timeline-actor">
            {{ item.actor_name || '—' }}
          </span>
          <span class="approval-timeline-action">{{ timelineActionLabel(item.action) }}</span>
          <span class="approval-timeline-time">{{ formatPrintDateTime(item.created_at) }}</span>
        </div>
        <p v-if="item.comment" class="approval-timeline-comment">{{ item.comment }}</p>
        <p v-else-if="!showActor" class="approval-timeline-comment is-empty">无</p>
        <img
          v-if="signSrc(item)"
          :src="signSrc(item)!"
          alt="手写签名"
          class="approval-timeline-sign"
        />
      </div>
    </li>
  </ol>
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

type Tone = 'success' | 'danger' | 'warning' | 'info' | 'neutral'

function actionTone(action: string): Tone {
  const a = (action || '').toLowerCase()
  if (['approved', 'agree', 'complete', 'completed'].includes(a)) return 'success'
  if (['rejected', 'reject', 'refuse'].includes(a)) return 'danger'
  if (['transfer', 'withdraw', 'return'].includes(a)) return 'warning'
  if (['submit', 'start', 'running', 'pending'].includes(a)) return 'info'
  return 'neutral'
}

function signSrc(item: ApprovalTimelineItem) {
  return signatureImageSrc(item)
}
</script>

<style scoped>
.approval-timeline {
  margin: 0;
  padding: 0;
  list-style: none;
}

.approval-timeline-item {
  position: relative;
  display: flex;
  gap: 12px;
  padding-bottom: 14px;
}

.approval-timeline-item:last-child {
  padding-bottom: 0;
}

.approval-timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  top: 14px;
  bottom: 0;
  left: 3.5px;
  width: 1px;
  background: var(--divider);
}

.approval-timeline-dot {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 50%;
  background: var(--text-disabled);
  box-shadow: 0 0 0 3px var(--surface);
}

.approval-timeline-item.is-success .approval-timeline-dot {
  background: var(--success);
}

.approval-timeline-item.is-danger .approval-timeline-dot {
  background: var(--danger);
}

.approval-timeline-item.is-warning .approval-timeline-dot {
  background: var(--warning);
}

.approval-timeline-item.is-info .approval-timeline-dot {
  background: var(--info);
}

.approval-timeline-body {
  flex: 1;
  min-width: 0;
}

.approval-timeline-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 8px;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.approval-timeline-actor {
  font-weight: 600;
  color: var(--text);
}

.approval-timeline-action {
  color: var(--text-secondary);
}

.approval-timeline-time {
  margin-left: auto;
  font-size: 0.6875rem;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.approval-timeline-comment {
  margin: 5px 0 0;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  background: var(--surface-muted);
  font-size: 0.8125rem;
  line-height: 1.55;
  color: var(--text-secondary);
  word-break: break-word;
}

.approval-timeline-comment.is-empty {
  padding: 0;
  background: transparent;
  color: var(--text-tertiary);
}

.approval-timeline-sign {
  display: block;
  max-width: 110px;
  max-height: 40px;
  margin-top: 6px;
  object-fit: contain;
}

.approval-timeline--compact .approval-timeline-item {
  padding-bottom: 10px;
}

.approval-timeline--compact .approval-timeline-head {
  line-height: 1.4;
}

.approval-timeline--compact .approval-timeline-time {
  font-size: 0.65625rem;
}
</style>
