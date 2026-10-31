<template>
  <PageChrome class="apply-page">
    <template #title>
      <a-space>
        <a-button type="text" size="small" @click="goBack">
          <icon-left /> {{ t('apply.back_catalog') }}
        </a-button>
      </a-space>
    </template>
    <template v-if="formSchema" #actions>
      <a-space wrap class="apply-header-actions">
        <a-button
          size="small"
          type="outline"
          :loading="printPreviewLoading"
          @click="openPrintPreview"
        >
          {{ t('apply.print_preview') }}
        </a-button>
        <a-button :loading="savingDraft" @click="saveDraft()">{{ t('apply.save_draft') }}</a-button>
        <a-button type="primary" :loading="submitting" @click="submit">
          {{ t('apply.submit_application') }}
        </a-button>
      </a-space>
    </template>

    <a-spin :loading="pageLoading">
      <header class="apply-process-header">
        <ProcessIcon :icon="processIcon" :size="48" />
        <div class="apply-process-head-text">
          <h1 class="apply-process-title">{{ processTitle }}</h1>
          <p v-if="resubmitFromId" class="apply-resubmit-hint">{{ t('apply.resubmit_hint', { id: resubmitFromId }) }}</p>
        </div>
      </header>

      <a-card class="apply-card mb-4" :bordered="false">
        <a-form layout="vertical" class="apply-org-form" :model="orgFormModel">
          <div
            class="apply-org-grid"
            :class="{ 'apply-org-grid--with-org': showOrgUnitPicker && showCompanyPicker }"
          >
            <div class="apply-org-item apply-org-item--company">
              <a-form-item v-if="showCompanyPicker" :label="t('apply.company_label')" required>
                <a-select
                  v-model="companyId"
                  :options="userCompanyOpts"
                  :placeholder="t('apply.company_placeholder')"
                  allow-search
                />
              </a-form-item>
              <a-form-item
                v-else-if="showOrgUnitPicker"
                :label="t('apply.company_label')"
                required
              >
                <a-select
                  v-model="orgUnitId"
                  :options="orgUnitOpts"
                  :placeholder="t('apply.company_placeholder')"
                  allow-search
                />
              </a-form-item>
              <a-form-item v-else :label="t('apply.company_label')">
                <a-input :model-value="companyDisplayName" readonly />
              </a-form-item>
            </div>

            <div
              v-if="showOrgUnitPicker && showCompanyPicker"
              class="apply-org-item apply-org-item--org"
            >
              <a-form-item :label="t('apply.org_unit_label')" required>
                <a-select
                  v-model="orgUnitId"
                  :options="orgUnitOpts"
                  :placeholder="t('apply.org_unit_ph')"
                  allow-search
                />
              </a-form-item>
            </div>

            <div class="apply-org-item apply-org-item--dept">
              <a-form-item :label="t('apply.dept_label')" required>
                <a-select
                  v-model="departmentId"
                  :options="filteredDeptOpts"
                  :placeholder="t('apply.dept_placeholder')"
                  allow-search
                />
                <template #extra>
                  <span class="text-xs text-gray-500">{{ t('apply.dept_hint') }}</span>
                </template>
              </a-form-item>
            </div>
          </div>
        </a-form>
      </a-card>

      <a-card v-if="formSchema" class="apply-card" :bordered="false">
        <p v-if="formSchema.description" class="text-sm text-gray-500 mb-4">{{ formSchema.description }}</p>
        <div :class="`device-frame frame-${previewDevice}`">
          <FormRenderer
            v-model="formData"
            :schema="formSchema"
            :device="previewDevice"
            :company-id="companyId"
            :holiday-user-id="auth.user?.id"
            :exclude-instance-ref="draftUuid || undefined"
            :apply-department-id="departmentId"
            apply-filler-defaults
          />
        </div>
        <div class="apply-flow-preview-wrap">
          <WorkflowFlowPreview
            v-if="processGraph?.nodes?.length"
            :process-graph="processGraph"
            :form-data="formData"
            mode="apply"
            :title="t('apply.flow_preview_title')"
          />
        </div>

        <div class="apply-footer-actions">
          <a-space wrap>
            <a-button :loading="savingDraft" @click="saveDraft()">{{ t('apply.save_draft') }}</a-button>
            <a-button type="primary" :loading="submitting" class="!min-h-[44px]" @click="submit">
              {{ t('apply.submit_application') }}
            </a-button>
          </a-space>
        </div>
      </a-card>
    </a-spin>

    <UnsavedLeaveModal
      v-model:visible="leaveModalVisible"
      :saving="leaveSaving"
      @cancel="cancelLeave"
      @discard="discardLeave"
      @save-and-leave="saveAndLeave"
    />

    <WorkflowPrintPreviewOverlay ref="printPreviewRef" />
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { IconLeft } from '@arco-design/web-vue/es/icon'
import { useRoute, useRouter } from 'vue-router'
import { api, type ApiResponse } from '@/api/client'
import PageChrome from '@/components/layout/PageChrome.vue'
import FormRenderer from '@/components/form/FormRenderer.vue'
import ProcessIcon from '@/components/apply/ProcessIcon.vue'
import WorkflowFlowPreview from '@/components/workflow/WorkflowFlowPreview.vue'
import WorkflowPrintPreviewOverlay from '@/components/print/WorkflowPrintPreviewOverlay.vue'
import UnsavedLeaveModal from '@/components/common/UnsavedLeaveModal.vue'
import { useUnsavedLeaveGuard } from '@/composables/useUnsavedLeaveGuard'
import { useBreakpoint } from '@/composables/useBreakpoint'
import { useEmbedDesktop } from '@/composables/useEmbedDesktop'
import { useAuthStore, type Membership } from '@/stores/auth'
import type { FormSchema } from '@/types/form'
import type { ProcessGraph } from '@/utils/workflowFlowGraph'
import { DEFAULT_FORM_SCHEMA } from '@/types/form'
import { applyFormFormulas } from '@/utils/formFormula'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { isEmbedDesktop, notifyClient, embedNavigate, embedRefreshBadges, routerPushWithEmbed } = useEmbedDesktop()
const auth = useAuthStore()

type DeptRow = {
  department_id: number
  label: string
  is_primary?: boolean
  org_unit_id?: number
}

const companyId = ref<number>()
const orgUnitId = ref<number>()
const departmentId = ref<number>()
const formData = ref<Record<string, unknown>>({})
const formSchema = ref<FormSchema | null>(null)
const orgFormModel = {}
const workflowDefId = ref<number>()
const processGraph = ref<ProcessGraph>()
const processIcon = ref('general')
const processTitle = ref('')
const orgUnits = ref<{ id: number; name: string }[]>([])
const departments = ref<DeptRow[]>([])
const { isMobile } = useBreakpoint()
const previewDevice = computed<'desktop' | 'mobile'>(() => (isMobile.value ? 'mobile' : 'desktop'))
const submitting = ref(false)
const savingDraft = ref(false)
const pageLoading = ref(false)
const draftUuid = ref('')
const resubmitFromId = ref<number>()
const pendingResubmitDeptId = ref<number>()
const pendingResubmitOrgUnitId = ref<number>()
const pendingResubmitCompanyId = ref<number>()
const syncingOrg = ref(false)
const savedSnapshot = ref('')
const pageReady = ref(false)
const printPreviewLoading = ref(false)
const printPreviewRef = ref<InstanceType<typeof WorkflowPrintPreviewOverlay> | null>(null)

function buildApplySnapshot() {
  return JSON.stringify({
    companyId: companyId.value,
    orgUnitId: orgUnitId.value,
    departmentId: departmentId.value,
    formData: formData.value,
  })
}

function markApplySaved() {
  savedSnapshot.value = buildApplySnapshot()
}

function isApplyDirty() {
  if (!pageReady.value || !formSchema.value) return false
  return savedSnapshot.value !== buildApplySnapshot()
}

const {
  modalVisible: leaveModalVisible,
  saving: leaveSaving,
  cancelLeave,
  discardLeave,
  saveAndLeave,
  requestLeave,
} = useUnsavedLeaveGuard({
  enabled: () => pageReady.value && !!formSchema.value,
  isDirty: isApplyDirty,
  onSave: async () => saveDraft(true),
  markSaved: markApplySaved,
})

const userCompanyOpts = computed(() => {
  const map = new Map<number, string>()
  for (const m of auth.user?.memberships || []) {
    if (!map.has(m.company_id)) {
      map.set(m.company_id, m.company_name || `公司 #${m.company_id}`)
    }
  }
  return [...map.entries()].map(([value, label]) => ({ value, label }))
})

const showCompanyPicker = computed(() => userCompanyOpts.value.length > 1)
const showOrgUnitPicker = computed(() => orgUnits.value.length > 1)

const companyDisplayName = computed(() => {
  const hit = userCompanyOpts.value.find((c) => c.value === companyId.value)
  if (hit) return hit.label
  if (orgUnits.value.length === 1) return orgUnits.value[0].name
  return ''
})

const orgUnitOpts = computed(() =>
  orgUnits.value.map((u) => ({ label: u.name, value: u.id })),
)

const filteredDeptOpts = computed(() => {
  let rows = departments.value
  if (orgUnitId.value) {
    rows = rows.filter((d) => d.org_unit_id === orgUnitId.value)
  }
  return rows.map((d) => ({ label: d.label, value: d.department_id }))
})

const selectedDeptLabel = computed(() => {
  const hit = departments.value.find((d) => d.department_id === departmentId.value)
  return hit?.label || filteredDeptOpts.value.find((d) => d.value === departmentId.value)?.label || ''
})

function buildPrintFormValues(): Record<string, unknown> {
  if (!formSchema.value) return {}
  const copy = JSON.parse(JSON.stringify(formData.value)) as Record<string, unknown>
  applyFormFormulas(formSchema.value, copy)
  return copy
}

async function openPrintPreview() {
  if (!formSchema.value) return
  printPreviewLoading.value = true
  try {
    const now = new Date()
    await printPreviewRef.value?.open({
      formSchema: formSchema.value,
      formValues: buildPrintFormValues(),
      definitionName: processTitle.value || formSchema.value.title,
      companyId: companyId.value,
      excludeInstanceUuid: draftUuid.value || '',
      processGraph: processGraph.value,
      timeline: [],
      meta: {
        id: 0,
        displayNo: t('apply.print_preview_draft_no'),
        status: 'draft',
        definitionName: processTitle.value || formSchema.value.title,
        initiatorName: auth.user?.display_name || auth.user?.username || '',
        companyName: companyDisplayName.value,
        departmentName: selectedDeptLabel.value,
        departmentPath: selectedDeptLabel.value,
        startedAt: now.toISOString(),
        printedAt: now.toISOString(),
        printerName: auth.user?.display_name || auth.user?.username || '',
      },
    })
  } finally {
    printPreviewLoading.value = false
  }
}

function goBack() {
  requestLeave(() => {
    void routerPushWithEmbed(router, { name: 'apply' })
  })
}

function primaryMembershipForCompany(cid: number): Membership | undefined {
  const rows = (auth.user?.memberships || []).filter((m) => m.company_id === cid)
  return rows.find((m) => m.is_primary) || rows[0]
}

function pickDefaultOrgAndDept() {
  const rows = departments.value
  if (!rows.length) {
    departmentId.value = undefined
    return
  }
  const primaryMem = companyId.value ? primaryMembershipForCompany(companyId.value) : undefined
  const primaryRow =
    rows.find((d) => d.is_primary) ||
    (primaryMem ? rows.find((d) => d.department_id === primaryMem.department_id) : undefined) ||
    rows[0]

  if (primaryRow?.org_unit_id && orgUnits.value.some((u) => u.id === primaryRow.org_unit_id)) {
    orgUnitId.value = primaryRow.org_unit_id
  } else if (orgUnits.value.length === 1) {
    orgUnitId.value = orgUnits.value[0].id
  }

  const inUnit = orgUnitId.value
    ? rows.filter((d) => d.org_unit_id === orgUnitId.value)
    : rows
  const dept =
    inUnit.find((d) => d.is_primary) ||
    (primaryMem ? inUnit.find((d) => d.department_id === primaryMem.department_id) : undefined) ||
    inUnit[0]
  departmentId.value = dept?.department_id
}

async function loadOrgUnits() {
  if (!companyId.value) return
  const res = await api.get<ApiResponse<{ id: number; name: string }[]>>('/org/top-units', {
    params: { company_id: companyId.value },
  })
  if (res.data.ok) {
    orgUnits.value = res.data.data
    if (orgUnits.value.length === 1 && !orgUnitId.value) {
      orgUnitId.value = orgUnits.value[0].id
    }
  }
}

async function loadDepartments() {
  if (!companyId.value) return
  const params: Record<string, number> = { company_id: companyId.value }
  const dRes = await api.get<ApiResponse<DeptRow[]>>('/org/my-departments', { params })
  if (!dRes.data.ok) return
  departments.value = dRes.data.data

  if (pendingResubmitDeptId.value != null) {
    const id = pendingResubmitDeptId.value
    const row = dRes.data.data.find((d) => d.department_id === id)
    if (row) {
      if (row.org_unit_id) orgUnitId.value = row.org_unit_id
      departmentId.value = id
    } else {
      pickDefaultOrgAndDept()
    }
    pendingResubmitDeptId.value = undefined
    pendingResubmitOrgUnitId.value = undefined
    pendingResubmitCompanyId.value = undefined
    return
  }

  pickDefaultOrgAndDept()
}

async function applyCompanyChange(cid: number, keepSelection = false) {
  syncingOrg.value = true
  companyId.value = cid
  if (!keepSelection) {
    orgUnitId.value = undefined
    departmentId.value = undefined
  }
  await loadOrgUnits()
  if (pendingResubmitOrgUnitId.value) {
    orgUnitId.value = pendingResubmitOrgUnitId.value
  }
  await loadDepartments()
  syncingOrg.value = false
}

async function loadForm(defId: number, titleFallback: string) {
  const res = await api.get<
    ApiResponse<{ form_schema: FormSchema; name?: string; process_graph?: ProcessGraph }>
  >(`/workflow/definitions/${defId}`)
  if (res.data.ok) {
    const fs = res.data.data.form_schema as FormSchema
    formSchema.value = fs?.sections ? fs : DEFAULT_FORM_SCHEMA()
    processTitle.value = titleFallback || res.data.data.name || formSchema.value.title || ''
    formSchema.value.title = processTitle.value
    if (res.data.data.process_graph) {
      processGraph.value = res.data.data.process_graph as ProcessGraph
    }
  }
}

watch(companyId, async (cid, prev) => {
  if (syncingOrg.value || cid == null) return
  if (prev !== undefined && cid !== prev && pendingResubmitDeptId.value == null) {
    await applyCompanyChange(cid)
  }
})

watch(orgUnitId, (id, prev) => {
  if (syncingOrg.value || pendingResubmitDeptId.value != null) return
  if (prev !== undefined && id !== prev) {
    const rows = departments.value.filter((d) => !id || d.org_unit_id === id)
    if (!rows.length) {
      departmentId.value = undefined
      return
    }
    const keep = rows.some((d) => d.department_id === departmentId.value)
    if (!keep) {
      const primary = rows.find((d) => d.is_primary) || rows[0]
      departmentId.value = primary.department_id
    }
  }
})

interface ResubmitContext {
  source_instance_id: number
  source_public_uuid: string
  definition_id: number
  definition_name: string
  icon?: string
  company_id: number
  org_unit_id?: number | null
  department_id?: number | null
  form: Record<string, unknown>
}

async function loadResubmitContext(instanceRef: string) {
  const res = await api.get<ApiResponse<ResubmitContext>>(
    `/workflow/instances/${instanceRef}/resubmit`,
  )
  if (!res.data.ok) throw new Error(res.data.message || '无法加载原申请')
  const ctx = res.data.data
  resubmitFromId.value = ctx.source_instance_id
  workflowDefId.value = ctx.definition_id
  processTitle.value = ctx.definition_name || processTitle.value
  if (ctx.icon) processIcon.value = ctx.icon
  pendingResubmitCompanyId.value = ctx.company_id
  if (ctx.org_unit_id) pendingResubmitOrgUnitId.value = ctx.org_unit_id
  if (ctx.department_id) pendingResubmitDeptId.value = ctx.department_id
  formData.value = JSON.parse(JSON.stringify(ctx.form || {})) as Record<string, unknown>
  return ctx.definition_id
}

function resolveInitialCompanyId(): number | undefined {
  if (pendingResubmitCompanyId.value) return pendingResubmitCompanyId.value
  const memberships = auth.user?.memberships || []
  if (!memberships.length) return undefined
  const primary = memberships.find((m) => m.is_primary) || memberships[0]
  return primary.company_id
}

function buildSubmitPayload() {
  const unitId = orgUnitId.value || orgUnits.value[0]?.id
  return {
    definition_id: workflowDefId.value,
    company_id: companyId.value,
    org_unit_id: unitId,
    department_id: departmentId.value,
    form: formData.value,
  }
}

function validateOrgContext(): boolean {
  if (!companyId.value || !departmentId.value || !workflowDefId.value) {
    Message.warning(t('apply.submit_warning'))
    return false
  }
  const unitId = orgUnitId.value || orgUnits.value[0]?.id
  if (!unitId) {
    Message.warning(t('apply.submit_warning'))
    return false
  }
  return true
}

async function saveDraft(silent = false): Promise<boolean> {
  if (!validateOrgContext()) return false
  savingDraft.value = true
  try {
    const payload = { ...buildSubmitPayload(), as_draft: true }
    if (draftUuid.value) {
      const res = await api.put<ApiResponse<{ public_uuid: string }>>(
        `/workflow/instances/${draftUuid.value}`,
        payload,
      )
      if (res.data.ok) {
        markApplySaved()
        if (!silent) Message.success(res.data.message || t('apply.draft_saved'))
        return true
      }
      return false
    }
    const res = await api.post<ApiResponse<{ public_uuid: string }>>('/workflow/instances', payload)
    if (res.data.ok) {
      draftUuid.value = res.data.data.public_uuid
      markApplySaved()
      if (!silent) Message.success(res.data.message || t('apply.draft_saved'))
      // 保存并离开时由守卫负责跳转，此处不要 replace 干扰目标路由
      if (!silent) {
        router.replace({
          name: 'apply-start',
          query: { ...route.query, draft: draftUuid.value },
        })
      }
      return true
    }
    return false
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('apply.draft_save_failed'))
    return false
  } finally {
    savingDraft.value = false
  }
}

async function submit() {
  if (!validateOrgContext()) return
  submitting.value = true
  try {
    const payload = buildSubmitPayload()
    if (draftUuid.value) {
      const res = await api.post<ApiResponse<{ public_uuid: string }>>(
        `/workflow/instances/${draftUuid.value}/submit`,
        payload,
      )
      if (res.data.ok) {
        pageReady.value = false
        savedSnapshot.value = ''
        Message.success(res.data.message)
        embedRefreshBadges()
        if (isEmbedDesktop.value) {
          notifyClient({
            type: 'workflow_submitted',
            uuid: res.data.data.public_uuid,
          })
        }
        embedNavigate('instance-detail', { uuid: res.data.data.public_uuid })
      }
    } else {
      const res = await api.post<ApiResponse<{ public_uuid: string }>>('/workflow/instances', payload)
      if (res.data.ok) {
        pageReady.value = false
        savedSnapshot.value = ''
        Message.success(res.data.message)
        embedRefreshBadges()
        if (isEmbedDesktop.value) {
          notifyClient({
            type: 'workflow_submitted',
            uuid: res.data.data.public_uuid,
          })
        }
        embedNavigate('instance-detail', { uuid: res.data.data.public_uuid })
      }
    }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('apply.submit_failed'))
  } finally {
    submitting.value = false
  }
}

async function loadDraftContext(instanceRef: string) {
  const res = await api.get<
    ApiResponse<{
      public_uuid: string
      definition_id: number
      definition_name?: string
      company_id: number
      department_id?: number
      org_unit_id?: number
      variables?: { form?: Record<string, unknown> }
      status: string
    }>
  >(`/workflow/instances/${instanceRef}`)
  if (!res.data.ok) throw new Error(res.data.message || '无法加载草稿')
  const ctx = res.data.data
  if (ctx.status !== 'draft') throw new Error('该申请已不是草稿')
  draftUuid.value = ctx.public_uuid
  workflowDefId.value = ctx.definition_id
  processTitle.value = ctx.definition_name || processTitle.value
  pendingResubmitCompanyId.value = ctx.company_id
  if (ctx.org_unit_id) pendingResubmitOrgUnitId.value = ctx.org_unit_id
  if (ctx.department_id) pendingResubmitDeptId.value = ctx.department_id
  formData.value = JSON.parse(JSON.stringify(ctx.variables?.form || {})) as Record<string, unknown>
  return ctx.definition_id
}

onMounted(async () => {
  const fromRaw = route.query.from
  const fromRef = fromRaw ? String(fromRaw) : ''
  const draftRaw = route.query.draft
  const draftRef = draftRaw ? String(draftRaw) : ''
  let defId = route.query.def ? Number(route.query.def) : NaN
  processTitle.value = String(route.query.title || '')
  pageLoading.value = true
  try {
    if (!auth.loaded) await auth.fetchMe()
    if (draftRef) {
      try {
        defId = await loadDraftContext(draftRef)
      } catch (e) {
        Message.error(e instanceof Error ? e.message : '加载失败')
        router.replace({ name: 'my-instances' })
        return
      }
    } else if (fromRef) {
      try {
        defId = await loadResubmitContext(fromRef)
      } catch (e) {
        Message.error(e instanceof Error ? e.message : '加载失败')
        router.replace({ name: 'my-instances' })
        return
      }
    }
    if (!defId || Number.isNaN(defId)) {
      router.replace({ name: 'apply' })
      return
    }
    workflowDefId.value = defId

    let initialCompany = resolveInitialCompanyId()
    if (!initialCompany) {
      const pri = await api.get<ApiResponse<{ id: number }>>('/org/primary')
      if (pri.data.ok) initialCompany = pri.data.data.id
    }
    if (initialCompany) {
      await applyCompanyChange(initialCompany, !!resubmitFromId.value)
    }

    if (!resubmitFromId.value) {
      const catRes = await api.get<
        ApiResponse<{ items: { workflow_definition_id: number; icon?: string }[] }[]>
      >('/forms/applications-catalog')
      if (catRes.data.ok) {
        for (const g of catRes.data.data) {
          const hit = g.items.find((it) => it.workflow_definition_id === defId)
          if (hit?.icon) {
            processIcon.value = hit.icon
            break
          }
        }
      }
    }
    await loadForm(defId, processTitle.value)
    markApplySaved()
    pageReady.value = true
  } finally {
    pageLoading.value = false
  }
})
</script>

<style scoped>
.apply-page {
  padding-bottom: 5rem;
}

@media (min-width: 768px) {
  .apply-page {
    padding-bottom: 0;
  }
}

.apply-process-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.apply-process-head-text {
  min-width: 0;
}

.apply-process-title {
  margin: 0;
  font-size: 1.375rem;
  font-weight: 600;
  color: var(--text, #1f2329);
  line-height: 1.3;
}

.apply-resubmit-hint {
  margin: 4px 0 0;
  font-size: var(--app-font-xs, 13px);
  color: var(--text-tertiary, #9699a6);
}

.apply-page {
  min-width: 0;
  max-width: 100%;
  overflow-x: clip;
}

.apply-card {
  border: 1px solid var(--border-strong, var(--border)) !important;
  border-radius: var(--radius-lg) !important;
  box-shadow: var(--shadow-xs) !important;
  min-width: 0;
  max-width: 100%;
}

.apply-card :deep(.arco-card-body) {
  min-width: 0;
  max-width: 100%;
  overflow-x: clip;
}

.device-frame {
  margin: 0 auto;
  width: 100%;
  min-width: 0;
  max-width: 100%;
}
.frame-mobile {
  max-width: 100%;
}

.apply-flow-preview-wrap {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
}

.apply-header-actions {
  justify-content: flex-end;
}

.apply-footer-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border, #e6e9ef);
}

@media (max-width: 767px) {
  .apply-footer-actions {
    position: fixed;
    left: 0;
    right: 0;
    bottom: var(--mobile-tab-bar-height, calc(3.5rem + env(safe-area-inset-bottom, 0px)));
    z-index: 55;
    margin: 0;
    padding: 10px 14px;
    background: rgb(255 255 255 / 94%);
    backdrop-filter: blur(10px);
    border-top: 1px solid var(--border, #e6e9ef);
    box-shadow: 0 -6px 20px rgb(23 25 27 / 8%);
  }

  .apply-footer-actions :deep(.arco-space) {
    display: flex;
    width: 100%;
    flex-wrap: nowrap;
  }

  .apply-footer-actions :deep(.arco-space-item) {
    flex: 1;
  }

  .apply-footer-actions :deep(.arco-btn) {
    width: 100%;
    min-height: 44px;
  }
}

/* 发起公司 + 申请部门：电脑端一行各半，手机端纵向排列 */
.apply-org-grid {
  display: flex;
  flex-direction: column;
}

.apply-org-item :deep(.arco-form-item) {
  margin-bottom: var(--app-space-form-item, 12px);
}

@media (min-width: 768px) {
  .apply-org-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 16px;
    align-items: start;
  }

  .apply-org-item--org {
    grid-column: 1 / -1;
  }

  .apply-org-item--company {
    grid-column: 1;
  }

  .apply-org-item--dept {
    grid-column: 2;
  }

  .apply-org-item--dept :deep(.arco-form-item) {
    margin-bottom: 0;
  }

  .apply-org-item--company :deep(.arco-form-item) {
    margin-bottom: 0;
  }

  .apply-org-grid--with-org .apply-org-item--org :deep(.arco-form-item) {
    margin-bottom: var(--app-space-form-item, 12px);
  }
}
</style>
