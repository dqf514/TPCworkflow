<template>
  <a-modal
    v-model:visible="visible"
    :title="t('profile.title')"
    :width="modalWidth"
    :footer="false"
    @cancel="emit('update:visible', false)"
  >
    <a-tabs v-model:active-key="tab">
      <a-tab-pane key="profile" :title="t('profile.tab_basic')">
        <a-form :model="profileForm" layout="vertical">
          <a-form-item field="display_name" :label="t('profile.display_name')">
            <a-input v-model="profileForm.display_name" />
          </a-form-item>
          <a-form-item field="email" :label="t('profile.email')">
            <a-input :model-value="profileForm.email" readonly />
            <template #extra><span class="text-xs text-gray-500">{{ t('profile.email_fixed_hint') }}</span></template>
          </a-form-item>
          <a-form-item field="phone" :label="t('profile.phone')">
            <a-input v-model="profileForm.phone" />
          </a-form-item>
          <a-form-item field="dept_job" :label="t('profile.dept_job')">
            <div v-if="deptJobLines.length" class="dept-job-lines">
              <div v-for="(line, idx) in deptJobLines" :key="idx" class="text-sm">{{ line }}</div>
            </div>
            <span v-else class="text-sm text-gray-500">—</span>
            <template #extra><span class="text-xs text-gray-500">{{ t('profile.dept_job_hint') }}</span></template>
          </a-form-item>
          <a-form-item field="avatar" :label="t('profile.avatar')">
            <div class="avatar-row">
              <a-avatar :size="56" :image-url="avatarPreview">{{ auth.user?.display_name?.[0] }}</a-avatar>
              <div class="avatar-actions">
                <a-button size="small" :loading="avatarUploading" @click="pickAvatar">
                  {{ avatarUploading ? t('profile.avatar_uploading') : t('profile.avatar_pick') }}
                </a-button>
                <span class="avatar-hint">{{ t('profile.avatar_hint') }}</span>
              </div>
              <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" class="hidden" @change="onAvatarFile" />
            </div>
          </a-form-item>
          <a-button type="primary" :loading="saving" @click="saveProfile">{{ t('profile.save') }}</a-button>
        </a-form>
      </a-tab-pane>
      <a-tab-pane key="record-sets" :title="t('profile.tab_record_sets')">
        <PersonalRecordSetsPanel />
      </a-tab-pane>
      <a-tab-pane key="password" :title="t('profile.tab_password')">
        <a-alert
          v-if="auth.user?.need_set_password"
          type="warning"
          class="mb-4"
          :title="t('profile.password_not_set')"
        />
        <a-form :model="pwdForm" layout="vertical" @submit-success="savePassword">
          <a-form-item v-if="auth.user?.has_password" field="old_password" :label="t('profile.current_password')" required>
            <a-input-password v-model="pwdForm.old_password" />
          </a-form-item>
          <a-form-item field="new_password" :label="t('profile.new_password')" required>
            <a-input-password v-model="pwdForm.new_password" :placeholder="t('profile.new_password_ph')" />
          </a-form-item>
          <a-form-item field="confirm_password" :label="t('profile.confirm_password')" required>
            <a-input-password v-model="pwdForm.confirm_password" />
          </a-form-item>
          <a-button type="primary" html-type="submit" :loading="pwdSaving">
            {{ auth.user?.has_password ? t('profile.change_password') : t('profile.set_password') }}
          </a-button>
        </a-form>
      </a-tab-pane>
    </a-tabs>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import PersonalRecordSetsPanel from '@/components/profile/PersonalRecordSetsPanel.vue'

const props = defineProps<{ visible: boolean; defaultTab?: string }>()
const emit = defineEmits<{ 'update:visible': [boolean] }>()

const auth = useAuthStore()
const { t } = useI18n()
const tab = ref('profile')
const saving = ref(false)
const pwdSaving = ref(false)
const avatarUploading = ref(false)
const fileInput = ref<HTMLInputElement>()
const avatarPreviewOverride = ref('')

const visible = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v),
})

// 弹窗宽度在窄屏收敛：避免固定 880px 撑破手机视口
const modalWidth = computed(() =>
  tab.value === 'record-sets' ? 'min(880px, 100vw)' : 'min(520px, 100vw)',
)

const profileForm = reactive({
  display_name: '',
  email: '',
  phone: '',
})

const deptJobLines = computed(() => {
  const rows = auth.user?.memberships || []
  return rows
    .map((m) => {
      const dept = m.department_name || '—'
      const title = (m.job_title || '').trim()
      return title ? `${dept} · ${title}` : dept
    })
    .filter(Boolean)
})

const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const avatarPreview = computed(() => {
  if (avatarPreviewOverride.value) return avatarPreviewOverride.value
  return auth.user?.avatar_url || undefined
})

watch(
  () => props.visible,
  (v) => {
    if (!v || !auth.user) return
    tab.value = props.defaultTab || (auth.user.need_set_password ? 'password' : 'profile')
    profileForm.display_name = auth.user.display_name
    profileForm.email = auth.user.email || ''
    profileForm.phone = auth.user.phone || ''
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
    avatarPreviewOverride.value = ''
    if (fileInput.value) fileInput.value.value = ''
  },
)

function pickAvatar() {
  fileInput.value?.click()
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error(t('profile.read_image_failed')))
    reader.readAsDataURL(file)
  })
}

async function onAvatarFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    Message.warning(t('profile.pick_image_only'))
    input.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    Message.warning(t('profile.image_too_large'))
    input.value = ''
    return
  }
  avatarUploading.value = true
  try {
    const dataUrl = await readFileAsDataUrl(file)
    avatarPreviewOverride.value = dataUrl
    const res = await api.post<ApiResponse<{ avatar_url?: string }>>('/auth/avatar', {
      avatar_data: dataUrl,
    })
    if (!res.data.ok) throw new Error(res.data.message || t('profile.upload_failed'))
    await auth.fetchMe()
    avatarPreviewOverride.value = ''
    Message.success(t('profile.avatar_updated'))
  } catch (err) {
    avatarPreviewOverride.value = ''
    Message.error(err instanceof Error ? err.message : t('profile.avatar_upload_failed'))
  } finally {
    avatarUploading.value = false
    input.value = ''
  }
}

async function saveProfile() {
  saving.value = true
  try {
    await auth.updateProfile({
      display_name: profileForm.display_name,
      phone: profileForm.phone,
    })
    Message.success(t('profile.saved'))
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('profile.save_failed'))
  } finally {
    saving.value = false
  }
}

async function savePassword() {
  if (pwdForm.new_password.length < 6) return Message.warning(t('profile.password_too_short'))
  if (pwdForm.new_password !== pwdForm.confirm_password) return Message.warning(t('profile.password_mismatch'))
  pwdSaving.value = true
  try {
    await auth.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
    })
    Message.success(t('profile.password_updated'))
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('profile.password_failed'))
  } finally {
    pwdSaving.value = false
  }
}
</script>

<style scoped>
.hidden {
  display: none;
}

.avatar-row {
  display: flex;
  align-items: center;
  gap: var(--app-space-12);
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-4);
}

.avatar-hint {
  font-size: var(--app-font-xs);
  color: var(--text-tertiary);
}

.dept-job-lines {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-4);
}
</style>
