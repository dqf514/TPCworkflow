<template>
  <a-space wrap size="mini" @click.stop>
    <a-button size="mini" @click="emit('view', record)">{{ t('workflow.tasks_view') }}</a-button>
    <a-tooltip
      v-if="approveBlocked"
      :content="approveBlockedHint"
      position="top"
      mini
    >
      <span class="task-row-actions-disabled-wrap">
        <a-button type="primary" size="mini" disabled>
          {{ record.is_handler ? t('workflow.handle_done') : t('workflow.approve') }}
        </a-button>
      </span>
    </a-tooltip>
    <a-popconfirm
      v-else-if="record.can_quick_approve"
      :content="t('workflow.quick_approve_confirm')"
      @ok="emit('approve', record)"
    >
      <a-button
        type="primary"
        size="mini"
        :loading="actingId === record.task_id"
      >
        {{ record.is_handler ? t('workflow.handle_done') : t('workflow.approve') }}
      </a-button>
    </a-popconfirm>
    <a-button
      v-else
      type="primary"
      size="mini"
      :loading="actingId === record.task_id"
      @click="emit('approve', record)"
    >
      {{ record.is_handler ? t('workflow.handle_done') : t('workflow.approve') }}
    </a-button>
    <a-button
      v-if="record.can_reject"
      size="mini"
      status="danger"
      :loading="actingId === record.task_id"
      @click="emit('reject', record)"
    >
      {{ t('workflow.reject') }}
    </a-button>
  </a-space>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { WorkflowTaskListRow } from '@/types/workflowTaskList'

const props = defineProps<{
  record: WorkflowTaskListRow
  actingId?: number | null
}>()

const emit = defineEmits<{
  approve: [WorkflowTaskListRow]
  reject: [WorkflowTaskListRow]
  view: [WorkflowTaskListRow]
}>()

const { t } = useI18n()

const approveBlocked = computed(
  () => (props.record.field_requirement_errors?.length ?? 0) > 0,
)

const approveBlockedHint = computed(() => {
  const errs = props.record.field_requirement_errors
  if (errs?.length) return errs.join('；')
  return t('workflow.approve_blocked_field_requirements')
})
</script>

<style scoped>
.task-row-actions-disabled-wrap {
  display: inline-block;
}
</style>
