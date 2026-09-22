<template>
  <svg
    class="field-type-icon"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <!-- 单行文本 -->
    <template v-if="type === 'input'">
      <path d="M7 6h10M7 12h7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
      <path d="M9 18h6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    </template>
    <!-- 多行文本 -->
    <template v-else-if="type === 'textarea'">
      <path d="M6 7h12M6 11h12M6 15h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    </template>
    <!-- 数字 -->
    <template v-else-if="type === 'number'">
      <text x="5" y="16" fill="currentColor" font-size="11" font-family="Arial, sans-serif" font-weight="600">123</text>
      <path d="M5 19h14" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
    </template>
    <!-- 单金额（无汇率） -->
    <template v-else-if="type === 'plain_amount'">
      <text x="5" y="16" fill="currentColor" font-size="10" font-family="Arial, sans-serif" font-weight="600">¥</text>
      <path d="M10 19h12" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
    </template>
    <!-- 金额 -->
    <template v-else-if="type === 'money'">
      <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.5" />
      <path d="M9 9.5c0-1.2 1.2-2 3-2s3 .8 3 2-1.2 2-3 2-3 .8-3 2 1.2 2 3 2 3 .8 3 2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    </template>
    <!-- 公式 -->
    <template v-else-if="type === 'formula'">
      <rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" stroke-width="1.5" />
      <path d="M8 15l2-4 2 4M14 11v4M16 11v4M14 11h4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" />
    </template>
    <!-- 日期 -->
    <template v-else-if="type === 'date'">
      <rect x="4" y="6" width="16" height="14" rx="2" stroke="currentColor" stroke-width="1.5" />
      <path d="M4 10h16M8 4v4M16 4v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    </template>
    <!-- 日期时间 -->
    <template v-else-if="type === 'datetime'">
      <rect x="4" y="6" width="16" height="14" rx="2" stroke="currentColor" stroke-width="1.5" />
      <path d="M4 10h16M8 4v4M16 4v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
      <circle cx="17" cy="17" r="4" stroke="currentColor" stroke-width="1.3" />
      <path d="M17 15v2l1.2 1" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
    </template>
    <!-- 时间 -->
    <template v-else-if="type === 'time'">
      <circle cx="12" cy="13" r="7" stroke="currentColor" stroke-width="1.5" />
      <path d="M12 13V9M12 13l2.5 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
      <path d="M9 4h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    </template>
    <!-- 日期区间 -->
    <template v-else-if="type === 'date_range'">
      <rect x="3" y="7" width="8" height="10" rx="1.5" stroke="currentColor" stroke-width="1.3" />
      <rect x="13" y="7" width="8" height="10" rx="1.5" stroke="currentColor" stroke-width="1.3" />
      <path d="M11 12h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    </template>
    <!-- 日历 -->
    <template v-else-if="type === 'leave_calendar'">
      <rect x="4" y="5" width="16" height="15" rx="2" stroke="currentColor" stroke-width="1.5" />
      <path d="M4 9h16M8 3.5v3M16 3.5v3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
      <rect x="6.5" y="11" width="5" height="2.2" rx="0.8" fill="currentColor" opacity="0.85" />
      <rect x="12.5" y="14.5" width="5.5" height="2.2" rx="0.8" fill="currentColor" opacity="0.55" />
    </template>
    <!-- 单选 -->
    <template v-else-if="type === 'radio'">
      <circle cx="8" cy="9" r="3.5" stroke="currentColor" stroke-width="1.5" />
      <path d="M7.2 9.2l1 1 2-2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" />
      <path d="M13 9h7M13 15h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    </template>
    <!-- 多选 -->
    <template v-else-if="type === 'checkbox_group' || type === 'multi_select'">
      <rect x="5" y="6" width="4.5" height="4.5" rx="1" stroke="currentColor" stroke-width="1.4" />
      <path d="M6.2 8.4l1 1 2.2-2.2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
      <rect x="5" y="13" width="4.5" height="4.5" rx="1" stroke="currentColor" stroke-width="1.4" />
      <path d="M13 8.5h7M13 15h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    </template>
    <!-- 控件配置表 -->
    <template v-else-if="type === 'record_set'">
      <rect x="4" y="5" width="16" height="14" rx="2" stroke="currentColor" stroke-width="1.5" />
      <path d="M7 9h10M7 12h8M7 15h6" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
      <path d="M16 15l2 2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" />
    </template>
    <!-- 下拉 -->
    <template v-else-if="type === 'select'">
      <rect x="5" y="7" width="14" height="10" rx="2" stroke="currentColor" stroke-width="1.5" />
      <path d="M11 12l2 2 2-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
    </template>
    <!-- 开关 -->
    <template v-else-if="type === 'switch'">
      <rect x="5" y="9" width="14" height="8" rx="4" stroke="currentColor" stroke-width="1.5" />
      <circle cx="15" cy="13" r="2.5" fill="currentColor" />
    </template>
    <!-- 成员 -->
    <template v-else-if="type === 'user_picker' || type === 'contact'">
      <circle cx="12" cy="9" r="3.5" stroke="currentColor" stroke-width="1.5" />
      <path d="M6 19c0-3.3 2.7-5 6-5s6 1.7 6 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    </template>
    <!-- 部门 -->
    <template v-else-if="type === 'dept_picker'">
      <circle cx="12" cy="6" r="2.5" stroke="currentColor" stroke-width="1.3" />
      <circle cx="7" cy="16" r="2.5" stroke="currentColor" stroke-width="1.3" />
      <circle cx="17" cy="16" r="2.5" stroke="currentColor" stroke-width="1.3" />
      <path d="M10.5 8.5L8 13.5M13.5 8.5L16 13.5" stroke="currentColor" stroke-width="1.3" />
    </template>
    <!-- 地点 -->
    <template v-else-if="type === 'location'">
      <path d="M12 21s6-5.2 6-10a6 6 0 10-12 0c0 4.8 6 10 6 10z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
      <circle cx="12" cy="11" r="2" stroke="currentColor" stroke-width="1.5" />
    </template>
    <!-- 附件 -->
    <template v-else-if="type === 'attachment'">
      <path d="M14 6l-4.5 4.5a3 3 0 104.2 4.2L18 8.5a4.5 4.5 0 10-6.4 6.4L7 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
    </template>
    <!-- 图片 -->
    <template v-else-if="type === 'image'">
      <rect x="4" y="6" width="16" height="12" rx="2" stroke="currentColor" stroke-width="1.5" />
      <circle cx="9" cy="11" r="1.5" fill="currentColor" />
      <path d="M4 16l5-4 4 3 3-2 4 3" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
    </template>
    <!-- 智能票据 -->
    <template v-else-if="type === 'smart_receipt'">
      <rect x="4" y="5" width="16" height="14" rx="2" stroke="currentColor" stroke-width="1.5" />
      <path d="M7 9h10M7 12h6M7 15h8" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
      <circle cx="18" cy="8" r="3" stroke="currentColor" stroke-width="1.2" />
      <path d="M17 8h2M18 7v2" stroke="currentColor" stroke-width="1" stroke-linecap="round" />
    </template>
    <!-- 关联申请单 -->
    <template v-else-if="type === 'related_form'">
      <rect x="4" y="6" width="10" height="13" rx="1.5" stroke="currentColor" stroke-width="1.4" />
      <rect x="10" y="4" width="10" height="13" rx="1.5" stroke="currentColor" stroke-width="1.4" />
      <path d="M7 10h4M7 13h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
    </template>
    <!-- 明细 -->
    <template v-else-if="type === 'detail'">
      <rect x="4" y="5" width="16" height="14" rx="2" stroke="currentColor" stroke-width="1.5" />
      <path d="M4 10h16M8 14h8M8 17h5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" />
    </template>
    <!-- 说明文字 -->
    <template v-else-if="type === 'text_block'">
      <rect x="5" y="5" width="14" height="14" rx="2" stroke="currentColor" stroke-width="1.5" />
      <path d="M8 9h8M8 12h8M8 15h5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" />
    </template>
    <!-- 小标题 -->
    <template v-else-if="type === 'section_title'">
      <path d="M4 8h16M4 12h10" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      <path d="M4 17h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    </template>
    <!-- 分割线 -->
    <template v-else-if="type === 'divider'">
      <path d="M4 12h16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="2 3" />
    </template>
    <!-- 流水号 -->
    <template v-else-if="type === 'serial_no'">
      <path d="M6 8h12M6 12h9M6 16h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
      <text x="15" y="17" fill="currentColor" font-size="7" font-family="monospace">#</text>
    </template>
    <!-- 邮箱 -->
    <template v-else-if="type === 'email'">
      <rect x="4" y="7" width="16" height="11" rx="2" stroke="currentColor" stroke-width="1.5" />
      <path d="M4 9l8 5 8-5" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" />
    </template>
    <!-- 手机 -->
    <template v-else-if="type === 'phone'">
      <rect x="8" y="4" width="8" height="16" rx="2" stroke="currentColor" stroke-width="1.5" />
      <circle cx="12" cy="17" r="1" fill="currentColor" />
    </template>
    <!-- 默认 -->
    <template v-else>
      <rect x="5" y="5" width="14" height="14" rx="2" stroke="currentColor" stroke-width="1.5" />
      <path d="M9 12h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    </template>
  </svg>
</template>

<script setup lang="ts">
defineProps<{ type: string }>()
</script>

<style scoped>
.field-type-icon {
  width: 22px;
  height: 22px;
  color: #4e5969;
  flex-shrink: 0;
}
</style>
