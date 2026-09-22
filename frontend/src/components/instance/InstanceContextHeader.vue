<template>
  <div class="instance-context-header">
    <h2 v-if="title" class="ctx-title">{{ title }}</h2>
    <table class="ctx-table">
      <tbody>
        <tr>
          <th class="ctx-th">{{ t('print.org') }}</th>
          <td class="ctx-td">{{ meta.companyName || '—' }}</td>
          <th class="ctx-th">{{ t('print.approval_no') }}</th>
          <td class="ctx-td ctx-mono">{{ meta.displayNo || meta.id || '—' }}</td>
        </tr>
        <tr>
          <th class="ctx-th">{{ t('print.applicant') }}</th>
          <td class="ctx-td">{{ meta.initiatorName || '—' }}</td>
          <th class="ctx-th">{{ t('print.department') }}</th>
          <td class="ctx-td">{{ meta.departmentPath || meta.departmentName || '—' }}</td>
        </tr>
        <tr>
          <th class="ctx-th">{{ t('print.submitted_at') }}</th>
          <td class="ctx-td">{{ formatPrintDateTime(meta.startedAt) }}</td>
          <th class="ctx-th">{{ t('print.status') }}</th>
          <td class="ctx-td">{{ instanceStatusLabel(meta.status || '') }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { formatPrintDateTime, instanceStatusLabel } from '@/utils/printFormat'

export interface InstanceContextMeta {
  id?: number
  displayNo?: string
  status?: string
  definitionName?: string
  initiatorName?: string
  companyName?: string
  departmentName?: string
  departmentPath?: string
  startedAt?: string | null
}

defineProps<{
  title?: string
  meta: InstanceContextMeta
}>()

const { t } = useI18n()
</script>

<style scoped>
.instance-context-header {
  margin-bottom: 16px;
}

.ctx-title {
  margin: 0 0 12px;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1d2129;
}

.ctx-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  overflow: hidden;
}

.ctx-th {
  width: 88px;
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  color: #4e5969;
  background: #f7f8fa;
  border: 1px solid #e5e6eb;
  white-space: nowrap;
}

.ctx-td {
  padding: 10px 12px;
  color: #1d2129;
  border: 1px solid #e5e6eb;
  background: #fff;
}

.ctx-mono {
  font-family: ui-monospace, 'Cascadia Code', 'Segoe UI Mono', monospace;
  font-size: 13px;
}

@media (max-width: 640px) {
  .ctx-table,
  .ctx-table tbody,
  .ctx-table tr,
  .ctx-table th,
  .ctx-table td {
    display: block;
    width: 100%;
  }

  .ctx-th {
    border-bottom: none;
    padding-bottom: 4px;
  }

  .ctx-td {
    border-top: none;
    padding-top: 0;
    padding-bottom: 12px;
  }
}
</style>
