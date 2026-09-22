<template>
  <PageChrome
    :title="t('menu.leave_calendar')"
    :description="t('leave_calendar.page_desc')"
  >
    <div class="leave-calendar-page app-card">
      <div class="toolbar">
        <a-form :model="filters" layout="inline" class="toolbar-form">
          <a-form-item v-if="companyOpts.length > 1" :label="t('leave_calendar.company')">
            <a-select
              v-model="filters.companyId"
              :options="companyOpts"
              style="width: 200px"
              allow-search
            />
          </a-form-item>
          <a-form-item v-else-if="companyOpts.length === 1" :label="t('leave_calendar.company')">
            <span class="company-static">{{ companyOpts[0].label }}</span>
          </a-form-item>
          <a-form-item :label="t('leave_calendar.department')">
            <a-select
              v-model="filters.departmentId"
              :options="deptOpts"
              allow-clear
              allow-search
              :placeholder="t('leave_calendar.department_all')"
              style="width: 200px"
            />
          </a-form-item>
          <a-form-item>
            <a-checkbox v-model="filters.includeRunning">
              {{ t('leave_calendar.include_running') }}
            </a-checkbox>
          </a-form-item>
        </a-form>
      </div>

      <LeaveCalendarField
        v-if="filters.companyId"
        :company-id="filters.companyId"
        :department-id="filters.departmentId || undefined"
        :include-running="filters.includeRunning"
        :height="640"
      />
      <a-empty v-else :description="t('leave_calendar.no_company')" />
    </div>
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import PageChrome from '@/components/layout/PageChrome.vue'
import LeaveCalendarField from '@/components/form/LeaveCalendarField.vue'
import { useAuthStore } from '@/stores/auth'
import { loadCompanyDeptOptions } from '@/composables/useOrgDeptOptions'

const { t } = useI18n()
const auth = useAuthStore()

const filters = reactive({
  companyId: 0 as number,
  departmentId: undefined as number | undefined,
  includeRunning: true,
})

const deptOpts = ref<{ label: string; value: number }[]>([])

const companyOpts = computed(() => {
  const map = new Map<number, string>()
  for (const m of auth.user?.memberships || []) {
    if (!map.has(m.company_id)) {
      map.set(m.company_id, m.company_name || t('leave_calendar.company_fallback', { id: m.company_id }))
    }
  }
  return [...map.entries()].map(([value, label]) => ({ value, label }))
})

function resolveDefaultCompanyId() {
  const memberships = auth.user?.memberships || []
  const primary = memberships.find((m) => m.is_primary)
  if (primary) return primary.company_id
  return memberships[0]?.company_id || companyOpts.value[0]?.value || 0
}

async function refreshDepartments() {
  if (!filters.companyId) {
    deptOpts.value = []
    return
  }
  deptOpts.value = await loadCompanyDeptOptions(filters.companyId)
}

watch(
  () => filters.companyId,
  () => {
    filters.departmentId = undefined
    void refreshDepartments()
  },
)

onMounted(async () => {
  filters.companyId = resolveDefaultCompanyId()
  await refreshDepartments()
})
</script>

<style scoped>
.leave-calendar-page {
  padding: 16px 18px 20px;
}

.toolbar {
  margin-bottom: 12px;
}

.toolbar-form {
  row-gap: 8px;
}

.company-static {
  color: var(--color-text-1, #1d2129);
  font-weight: 500;
}
</style>
