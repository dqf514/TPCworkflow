<template>
  <a-modal
    v-model:visible="visible"
    title="导出到财务系统格式"
    :ok-loading="submitting"
    ok-text="导出凭证"
    cancel-text="取消"
    :width="560"
    unmount-on-close
    @before-ok="handleSubmit"
    @cancel="handleCancel"
  >
    <p class="finance-export-desc">
      按用友 YonSuite BIP「凭证导入」模板生成 Excel，可直接在财务系统中导入。请根据实际账簿填写下列参数。
    </p>

    <a-form layout="vertical" :model="form">
      <a-form-item label="导出方案" required>
        <a-select
          v-model="form.profileId"
          :options="profileOpts"
          placeholder="选择流程类型"
          @change="onProfileChange"
        />
      </a-form-item>

      <template v-if="activeProfile">
        <p v-if="activeProfile.description" class="profile-hint">{{ activeProfile.description }}</p>
        <a-form-item
          v-for="field in activeProfile.options"
          :key="field.key"
          :label="field.label"
          :required="field.required && field.type !== 'switch'"
        >
          <a-switch
            v-if="field.type === 'switch'"
            v-model="form.options[field.key]"
          />
          <a-input
            v-else
            v-model="form.options[field.key]"
            :placeholder="field.placeholder || ''"
            allow-clear
          />
          <div v-if="field.hint" class="field-hint">{{ field.hint }}</div>
        </a-form-item>
      </template>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import { downloadBlob, parseContentDispositionFilename } from '@/utils/downloadBlob'
import { formatDateTime } from '@/utils/dateTime'

export interface FinanceExportOptionField {
  key: string
  label: string
  type: 'text' | 'switch'
  required?: boolean
  default?: string | boolean
  placeholder?: string
  hint?: string
}

export interface FinanceExportProfile {
  id: string
  name: string
  description?: string
  options: FinanceExportOptionField[]
  source?: string
}

const props = defineProps<{
  sectorId?: number
  instanceIds?: number[]
}>()

const visible = defineModel<boolean>('visible', { default: false })

const profiles = ref<FinanceExportProfile[]>([])
const submitting = ref(false)
const form = reactive({
  profileId: '',
  options: {} as Record<string, string | boolean>,
})

const profileOpts = computed(() =>
  profiles.value.map((p) => ({
    label: p.source === 'custom' ? `${p.name}（自定义）` : p.name,
    value: p.id,
  })),
)

const activeProfile = computed(() =>
  profiles.value.find((p) => p.id === form.profileId),
)

function resetOptions(profile: FinanceExportProfile | undefined) {
  form.options = {}
  if (!profile) return
  for (const field of profile.options || []) {
    if (field.type === 'switch') {
      form.options[field.key] = Boolean(field.default)
    } else {
      form.options[field.key] = String(field.default ?? '')
    }
  }
}

function onProfileChange(id: string) {
  resetOptions(profiles.value.find((p) => p.id === id))
}

async function loadProfiles() {
  const params = props.sectorId ? { sector_id: props.sectorId } : undefined
  const res = (await api.get('/workflow/finance-export/profiles', { params })) as {
    data: ApiResponse<(FinanceExportProfile & { source?: string })[]>
  }
  if (res.data.ok) {
    profiles.value = res.data.data
    if (!form.profileId && profiles.value.length) {
      form.profileId = profiles.value[0].id
      resetOptions(profiles.value[0])
    }
  }
}

watch(visible, (v) => {
  if (v) void loadProfiles()
})

async function handleSubmit() {
  if (!props.sectorId) {
    Message.warning('请先选择业务板块')
    return false
  }
  if (!props.instanceIds?.length) {
    Message.warning('请先勾选需要导出的流程')
    return false
  }
  if (!form.profileId) {
    Message.warning('请选择导出方案')
    return false
  }
  const profile = activeProfile.value
  if (profile) {
    for (const field of profile.options) {
      if (!field.required || field.type === 'switch') continue
      const val = form.options[field.key]
      if (val == null || String(val).trim() === '') {
        Message.warning(`请填写${field.label}`)
        return false
      }
    }
  }

  submitting.value = true
  try {
    const res = await api.post(
      '/workflow/finance-export/export',
      {
        sector_id: props.sectorId,
        instance_ids: props.instanceIds,
        profile_id: form.profileId,
        options: form.options,
      },
      { responseType: 'blob', timeout: 120000 },
    )
    const blob = res.data as Blob
    const contentType = String(res.headers['content-type'] || '')
    if (contentType.includes('application/json')) {
      const text = await blob.text()
      let msg = '导出失败'
      try {
        const body = JSON.parse(text) as { message?: string }
        if (body.message) msg = body.message
      } catch {
        if (text) msg = text
      }
      Message.error(msg)
      return false
    }
    const profileName = profile?.name || form.profileId
    const fallback = `凭证导入_${profileName}_${formatDateTime(new Date().toISOString()).replace(/[:\s]/g, '')}.xlsx`
    const fname = parseContentDispositionFilename(res.headers['content-disposition']) || fallback
    downloadBlob(blob, fname)
    Message.success('财务凭证已导出')
    visible.value = false
    return true
  } catch (err) {
    Message.error(err instanceof Error ? err.message : '导出失败')
    return false
  } finally {
    submitting.value = false
  }
}

function handleCancel() {
  visible.value = false
}
</script>

<style scoped>
.finance-export-desc {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.profile-hint {
  margin: -4px 0 12px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.field-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>
