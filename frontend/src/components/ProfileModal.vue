<template>
  <a-modal
    v-model:visible="visible"
    title="个人中心"
    :width="modalWidth"
    :footer="false"
    @cancel="emit('update:visible', false)"
  >
    <a-tabs v-model:active-key="tab">
      <a-tab-pane key="profile" title="基本信息">
        <a-form :model="profileForm" layout="vertical">
          <a-form-item label="显示名">
            <a-input v-model="profileForm.display_name" />
          </a-form-item>
          <a-form-item label="邮箱">
            <a-input :model-value="profileForm.email" readonly />
            <template #extra><span class="text-xs text-gray-500">邮箱不可自行修改，请联系管理员</span></template>
          </a-form-item>
          <a-form-item label="手机">
            <a-input v-model="profileForm.phone" />
          </a-form-item>
          <a-form-item label="部门职务">
            <div v-if="deptJobLines.length" class="dept-job-lines">
              <div v-for="(line, idx) in deptJobLines" :key="idx" class="text-sm">{{ line }}</div>
            </div>
            <span v-else class="text-sm text-gray-500">—</span>
            <template #extra><span class="text-xs text-gray-500">职务由各任职部门分别设置</span></template>
          </a-form-item>
          <a-form-item label="头像">
            <div class="avatar-row">
              <a-avatar :size="56" :image-url="avatarPreview">{{ auth.user?.display_name?.[0] }}</a-avatar>
              <div class="avatar-actions">
                <a-button size="small" :loading="avatarUploading" @click="pickAvatar">
                  {{ avatarUploading ? '上传中…' : '选择图片' }}
                </a-button>
                <span class="avatar-hint">支持 PNG/JPEG/WEBP，选择后立即上传</span>
              </div>
              <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" class="hidden" @change="onAvatarFile" />
            </div>
          </a-form-item>
          <a-button type="primary" :loading="saving" @click="saveProfile">保存资料</a-button>
        </a-form>
      </a-tab-pane>
      <a-tab-pane key="record-sets" title="我的配置表">
        <PersonalRecordSetsPanel />
      </a-tab-pane>
      <a-tab-pane key="password" title="密码">
        <a-alert
          v-if="auth.user?.need_set_password"
          type="warning"
          class="mb-4"
          title="您尚未设置登录密码，请设置后也可使用账号密码登录。"
        />
        <a-form :model="pwdForm" layout="vertical" @submit-success="savePassword">
          <a-form-item v-if="auth.user?.has_password" label="当前密码" required>
            <a-input-password v-model="pwdForm.old_password" />
          </a-form-item>
          <a-form-item label="新密码" required>
            <a-input-password v-model="pwdForm.new_password" placeholder="至少 6 位" />
          </a-form-item>
          <a-form-item label="确认新密码" required>
            <a-input-password v-model="pwdForm.confirm_password" />
          </a-form-item>
          <a-button type="primary" html-type="submit" :loading="pwdSaving">
            {{ auth.user?.has_password ? '修改密码' : '设置密码' }}
          </a-button>
        </a-form>
      </a-tab-pane>
    </a-tabs>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import PersonalRecordSetsPanel from '@/components/profile/PersonalRecordSetsPanel.vue'

const props = defineProps<{ visible: boolean; defaultTab?: string }>()
const emit = defineEmits<{ 'update:visible': [boolean] }>()

const auth = useAuthStore()
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

const modalWidth = computed(() => (tab.value === 'record-sets' ? 880 : 520))

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
    reader.onerror = () => reject(new Error('读取图片失败'))
    reader.readAsDataURL(file)
  })
}

async function onAvatarFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    Message.warning('请选择图片文件')
    input.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    Message.warning('图片不能超过 5 MB')
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
    if (!res.data.ok) throw new Error(res.data.message || '上传失败')
    await auth.fetchMe()
    avatarPreviewOverride.value = ''
    Message.success('头像已更新')
  } catch (err) {
    avatarPreviewOverride.value = ''
    Message.error(err instanceof Error ? err.message : '头像上传失败')
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
    Message.success('资料已保存')
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function savePassword() {
  if (pwdForm.new_password.length < 6) return Message.warning('新密码至少 6 位')
  if (pwdForm.new_password !== pwdForm.confirm_password) return Message.warning('两次密码不一致')
  pwdSaving.value = true
  try {
    await auth.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
    })
    Message.success('密码已更新')
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '失败')
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
  gap: 12px;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.avatar-hint {
  font-size: 12px;
  color: var(--color-text-3);
}

.dept-job-lines {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
