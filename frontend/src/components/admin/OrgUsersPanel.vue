<template>
  <div class="org-users-panel">
    <p class="users-hint">{{ t('org.users_hint') }}</p>
    <div class="users-toolbar">
      <a-input-search
        v-model="searchQ"
        :placeholder="t('org.search_users_ph')"
        allow-clear
        class="users-search"
      />
      <a-button type="primary" @click="openCreateUser">{{ t('org.new_user_btn') }}</a-button>
    </div>

    <a-table
      :data="filteredUsers"
      :loading="loading"
      row-key="id"
      :pagination="{ pageSize: 20, showTotal: true }"
      class="users-table"
      @row-click="(record: UserRow) => openUserDrawer(record)"
    >
      <template #columns>
        <a-table-column :title="t('org.col_name')" :width="140">
          <template #cell="{ record }">
            <a-link @click.stop="openUserDrawer(record)">{{ record.display_name }}</a-link>
          </template>
        </a-table-column>
        <a-table-column :title="t('org.col_username')" data-index="username" :width="120" />
        <a-table-column :title="t('org.col_email')" data-index="email" />
        <a-table-column :title="t('org.col_dept_count')" data-index="membership_count" :width="80" />
        <a-table-column :title="t('org.col_status')" :width="160">
          <template #cell="{ record }">
            <a-space wrap>
              <a-tag :color="record.is_active ? 'green' : 'gray'">
                {{ record.is_active ? t('org.status_active') : t('org.status_inactive') }}
              </a-tag>
              <a-tag v-if="record.is_system_admin" color="arcoblue">{{ t('org.sys_admin_badge') }}</a-tag>
            </a-space>
          </template>
        </a-table-column>
        <a-table-column :title="t('org.col_actions')" :width="100" fixed="right">
          <template #cell="{ record }">
            <a-button size="mini" type="text" @click.stop="openUserDrawer(record)">{{ t('org.manage_user') }}</a-button>
          </template>
        </a-table-column>
      </template>
    </a-table>

    <a-drawer
      v-model:visible="drawerVisible"
      :title="drawerTitle"
      :width="640"
      unmount-on-close
      @cancel="drawerVisible = false"
    >
      <a-spin :loading="drawerLoading" class="drawer-spin">
        <template v-if="editUser.id">
          <a-form layout="vertical" class="user-form">
            <a-row :gutter="12">
              <a-col :span="12">
                <a-form-item :label="t('org.username')">
                  <a-input :model-value="editUser.username" disabled />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item :label="t('org.display_name')">
                  <a-input v-model="editUser.display_name" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="12">
              <a-col :span="12">
                <a-form-item :label="t('org.contact_email')">
                  <div class="admin-mail-field">
                    <input
                      v-model="editUserMailbox"
                      type="text"
                      class="admin-mail-input"
                      :placeholder="EMAIL_PLACEHOLDER"
                      spellcheck="false"
                    />
                  </div>
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item :label="t('org.phone')">
                  <a-input v-model="editUser.phone" allow-clear />
                </a-form-item>
              </a-col>
            </a-row>
            <p class="user-field-hint">{{ t('org.email_admin_hint') }}</p>
            <a-row :gutter="12">
              <a-col :span="8">
                <a-form-item :label="t('org.account_enabled')">
                  <a-switch v-model="editUser.is_active" />
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item :label="t('org.is_system_admin')">
                  <a-switch v-model="editUser.is_system_admin" />
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item :label="t('org.locale')">
                  <a-select v-model="editUser.locale" :options="localeOpts" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-form-item :label="t('org.holiday_regions')">
              <a-select
                v-model="editUser.holiday_regions"
                :options="holidayRegionOpts"
                multiple
                allow-clear
                allow-search
                :max-tag-count="4"
                :placeholder="t('org.holiday_regions_ph')"
              />
              <template #extra>{{ t('org.holiday_regions_hint') }}</template>
            </a-form-item>
          </a-form>

          <a-divider>{{ t('org.memberships_title') }}</a-divider>
          <a-table
            v-if="editUser.memberships.length"
            :data="editUser.memberships"
            row-key="membership_id"
            :pagination="false"
            size="small"
            class="mb-3"
          >
            <template #columns>
              <a-table-column :title="t('org.col_dept_path')">
                <template #cell="{ record }">
                  {{ record.department_path || record.department_name }}
                  <a-tag v-if="record.is_primary" size="small" color="arcoblue" class="ml-1">
                    {{ t('org.primary_badge') }}
                  </a-tag>
                </template>
              </a-table-column>
              <a-table-column :title="t('org.col_dept_role')" :width="120">
                <template #cell="{ record }">
                  <a-select
                    v-model="record.role_in_dept"
                    size="small"
                    :options="roleOpts"
                    @change="saveMembership(record)"
                  />
                </template>
              </a-table-column>
              <a-table-column :title="t('org.job_title')" :width="120">
                <template #cell="{ record }">
                  <a-input
                    v-model="record.job_title"
                    size="small"
                    @blur="saveMembership(record)"
                  />
                </template>
              </a-table-column>
              <a-table-column :title="t('org.col_actions')" :width="160">
                <template #cell="{ record }">
                  <a-space>
                    <a-button
                      v-if="!record.is_primary"
                      size="mini"
                      type="text"
                      @click="setPrimary(record.membership_id)"
                    >
                      {{ t('org.set_primary') }}
                    </a-button>
                    <a-popconfirm
                      :content="t('org.remove_dept_confirm')"
                      @ok="removeMembership(record.membership_id)"
                    >
                      <a-button size="mini" type="text" status="danger">{{ t('org.remove_from_dept') }}</a-button>
                    </a-popconfirm>
                  </a-space>
                </template>
              </a-table-column>
            </template>
          </a-table>
          <a-empty v-else :description="t('org.no_dept')" class="mb-3" />

          <div class="add-membership-box">
            <a-tree-select
              v-model="addDeptId"
              :data="deptTree"
              :placeholder="t('org.select_dept')"
              allow-clear
              :field-names="treeFieldNames"
              class="add-dept-select"
            />
            <a-select v-model="addDeptRole" :options="roleOpts" style="width: 110px" />
            <a-input v-model="addDeptJob" :placeholder="t('org.job_title')" style="width: 140px" />
            <a-button type="outline" :disabled="!addDeptId" @click="addMembership">
              {{ t('org.add_dept_membership') }}
            </a-button>
          </div>

          <a-divider>{{ t('org.flow_roles_title') }}</a-divider>
          <p class="user-field-hint">{{ t('org.flow_roles_hint') }}</p>
          <a-select
            v-model="editUserFlowRoleIds"
            :options="flowRoleOpts"
            multiple
            allow-search
            :max-tag-count="4"
            :placeholder="t('org.flow_roles_ph')"
            class="w-full mb-3"
          />
          <a-button type="outline" :loading="savingFlowRoles" @click="saveUserFlowRoles">
            {{ t('org.flow_roles_save') }}
          </a-button>

          <a-divider>{{ t('org.new_password') }}</a-divider>
          <div class="password-row">
            <a-input-password
              v-model="newPassword"
              :placeholder="t('org.password_keep')"
              allow-clear
              class="password-input"
            />
            <a-popconfirm
              :content="t('org.reset_password_confirm', { pwd: defaultResetPwd })"
              @ok="resetPassword(defaultResetPwd)"
            >
              <a-button>{{ t('org.reset_password') }} ({{ defaultResetPwd }})</a-button>
            </a-popconfirm>
            <a-button
              type="primary"
              :disabled="!newPassword"
              @click="resetPassword(newPassword)"
            >
              {{ t('org.reset_password') }}
            </a-button>
          </div>

          <div class="drawer-footer">
            <a-button type="primary" :loading="saving" @click="saveUser">{{ t('org.save_user') }}</a-button>
          </div>
        </template>
      </a-spin>
    </a-drawer>

    <a-modal v-model:visible="createModal" :title="t('org.new_user_btn')" :width="520" @ok="createUser">
      <a-form :model="createForm" layout="vertical">
        <a-form-item :label="t('org.username')" required><a-input v-model="createForm.username" /></a-form-item>
        <a-form-item :label="t('org.email')" required><a-input v-model="createForm.email" /></a-form-item>
        <a-form-item :label="t('org.display_name')"><a-input v-model="createForm.display_name" /></a-form-item>
        <a-form-item :label="t('org.password')"><a-input-password v-model="createForm.password" /></a-form-item>
        <a-form-item :label="t('org.depts_optional')">
          <a-tree-select
            v-model="createDeptIds"
            :data="deptTree"
            multiple
            tree-checkable
            allow-clear
            :placeholder="t('org.no_dept_yet')"
            :field-names="treeFieldNames"
            class="w-full"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'

const emit = defineEmits<{ changed: [] }>()

const { t, locale } = useI18n()
const EMAIL_PLACEHOLDER = 'user@example.com'

interface UserRow {
  id: number
  username: string
  display_name: string
  email?: string
  phone?: string
  is_active: boolean
  is_system_admin: boolean
  membership_count: number
}

interface MembershipRow {
  membership_id: number
  department_id: number
  department_name?: string
  department_path?: string
  is_primary: boolean
  role_in_dept: string
  job_title?: string
}

interface UserDetail {
  id: number
  username: string
  display_name: string
  email?: string
  phone?: string
  is_active: boolean
  is_system_admin: boolean
  locale: string
  holiday_regions?: string[]
  memberships: MembershipRow[]
}

interface TreeNode {
  key: string
  title: string
  id: number
  name: string
  children?: TreeNode[]
}

const defaultResetPwd = 'Imc@2026'
const treeFieldNames = { key: 'key', title: 'title', children: 'children' }

const loading = ref(false)
const users = ref<UserRow[]>([])
const searchQ = ref('')
const companyId = ref<number>()

const drawerVisible = ref(false)
const drawerLoading = ref(false)
const saving = ref(false)
const newPassword = ref('')
const addDeptId = ref<string | number>()
const addDeptRole = ref('member')
const addDeptJob = ref('')
const editUserFlowRoleIds = ref<number[]>([])
const flowRoleOpts = ref<{ label: string; value: number }[]>([])
const savingFlowRoles = ref(false)
const deptTree = ref<TreeNode[]>([])

/** 独立 ref，避免 reactive.email 与部分浏览器隐私扩展冲突 */
const editUserMailbox = ref('')

const editUser = reactive({
  id: 0,
  username: '',
  display_name: '',
  phone: '',
  is_active: true,
  is_system_admin: false,
  locale: 'zh-CN',
  holiday_regions: [] as string[],
  memberships: [] as MembershipRow[],
})

const holidayRegionOpts = ref<{ label: string; value: string }[]>([])

const createModal = ref(false)
const createDeptIds = ref<number[]>([])
const createForm = reactive({
  username: '',
  email: '',
  display_name: '',
  password: defaultResetPwd,
})

const localeOpts = [
  { label: '简体中文', value: 'zh-CN' },
  { label: 'English', value: 'en-US' },
]

const roleOpts = computed(() => [
  { label: t('org.role_member'), value: 'member' },
  { label: t('org.role_manager'), value: 'manager' },
])

const filteredUsers = computed(() => {
  const q = searchQ.value.trim().toLowerCase()
  if (!q) return users.value
  return users.value.filter((u) => {
    const hay = [u.display_name, u.username, u.email || ''].join(' ').toLowerCase()
    return hay.includes(q)
  })
})

const drawerTitle = computed(() =>
  editUser.display_name
    ? t('org.user_drawer_title', { name: editUser.display_name })
    : t('org.profile_title'),
)

function notifyChanged() {
  emit('changed')
}

async function loadFlowRoles() {
  const res = await api.get<ApiResponse<FlowRoleRow[]>>('/admin/flow-roles')
  if (res.data.ok) {
    flowRoleOpts.value = res.data.data
      .filter((r) => r.is_active !== false && !r.is_dept_manager_role)
      .map((r) => ({
        label: `${r.name}（${r.code}）`,
        value: r.id,
      }))
  }
}

interface FlowRoleRow {
  id: number
  code: string
  name: string
  is_active?: boolean
  is_dept_manager_role?: boolean
}

async function loadUserFlowRoles(userId: number) {
  const res = await api.get<ApiResponse<{ role_ids: number[] }>>(`/admin/users/${userId}/flow-roles`)
  if (res.data.ok) {
    editUserFlowRoleIds.value = res.data.data.role_ids || []
  } else {
    editUserFlowRoleIds.value = []
  }
}

async function saveUserFlowRoles() {
  if (!editUser.id) return
  savingFlowRoles.value = true
  try {
    const res = await api.put<ApiResponse<unknown>>(`/admin/users/${editUser.id}/flow-roles`, {
      role_ids: editUserFlowRoleIds.value,
    })
    if (!res.data.ok) throw new Error(res.data.message || t('org.save_failed'))
    Message.success(t('org.flow_roles_saved'))
  } catch (e: unknown) {
    Message.error(e instanceof Error ? e.message : t('org.save_failed'))
  } finally {
    savingFlowRoles.value = false
  }
}

async function loadUsers() {
  loading.value = true
  try {
    const res = await api.get<ApiResponse<UserRow[]>>('/users')
    if (res.data.ok) users.value = res.data.data
  } finally {
    loading.value = false
  }
}

async function loadCompanyTree() {
  const res = await api.get<ApiResponse<{ id: number }>>('/org/primary')
  if (!res.data.ok) return
  companyId.value = res.data.data.id
  const st = await api.get<ApiResponse<{ tree: TreeNode[] }>>(
    `/org/companies/${companyId.value}/structure`,
  )
  if (st.data.ok) {
    deptTree.value = annotateDeptNodes(st.data.data.tree)
  }
}

function annotateDeptNodes(nodes: TreeNode[]): TreeNode[] {
  return nodes.map((n) => ({
    ...n,
    title: n.name,
    children: n.children?.length ? annotateDeptNodes(n.children) : undefined,
  }))
}

function normalizeDeptIds(raw: (number | string)[]): number[] {
  return raw
    .map((x) => {
      if (typeof x === 'number') return x
      const m = String(x).match(/dept-(\d+)/)
      return m ? parseInt(m[1], 10) : parseInt(String(x), 10)
    })
    .filter((id) => !Number.isNaN(id) && id > 0)
}

async function openUserDrawer(row: UserRow) {
  drawerVisible.value = true
  drawerLoading.value = true
  editUserMailbox.value = ''
  newPassword.value = ''
  addDeptId.value = undefined
  addDeptRole.value = 'member'
  addDeptJob.value = ''
  try {
    const res = await api.get<ApiResponse<UserDetail>>(`/users/${row.id}`)
    if (res.data.ok) {
      const u = res.data.data
      editUser.id = u.id
      editUser.username = u.username
      editUser.display_name = u.display_name
      editUserMailbox.value = u.email || ''
      editUser.phone = u.phone || ''
      editUser.is_active = u.is_active
      editUser.is_system_admin = u.is_system_admin
      editUser.locale = u.locale || 'zh-CN'
      editUser.holiday_regions = [...(u.holiday_regions || [])]
      editUser.memberships = (u.memberships || []).map((m) => ({ ...m }))
      await loadUserFlowRoles(u.id)
    }
  } finally {
    drawerLoading.value = false
  }
}

async function saveUser() {
  if (!editUser.id) return
  if (!editUserMailbox.value.trim()) {
    Message.warning(t('org.fill_email'))
    return
  }
  saving.value = true
  try {
    const body: Record<string, unknown> = {
      display_name: editUser.display_name,
      email: editUserMailbox.value.trim(),
      phone: editUser.phone,
      is_active: editUser.is_active,
      is_system_admin: editUser.is_system_admin,
      locale: editUser.locale,
      holiday_regions: editUser.holiday_regions,
    }
    if (newPassword.value) body.password = newPassword.value
    await api.put(`/users/${editUser.id}`, body)
    Message.success(t('org.saved'))
    newPassword.value = ''
    await loadUsers()
    notifyChanged()
  } catch (e: unknown) {
    Message.error(e instanceof Error ? e.message : t('org.save_failed'))
  } finally {
    saving.value = false
  }
}

async function resetPassword(pwd: string) {
  if (!editUser.id || !pwd) return
  await api.put(`/users/${editUser.id}`, { password: pwd })
  Message.success(t('org.reset_password_ok'))
  newPassword.value = ''
}

async function saveMembership(m: MembershipRow) {
  await api.put(`/org/memberships/${m.membership_id}`, {
    role_in_dept: m.role_in_dept,
    job_title: m.job_title,
  })
  Message.success(t('org.saved'))
  if (m.role_in_dept === 'manager') {
    await loadUsers()
    notifyChanged()
  }
}

async function setPrimary(membershipId: number) {
  await api.put(`/org/memberships/${membershipId}/primary`)
  Message.success(t('org.saved'))
  await reloadDrawerUser()
  notifyChanged()
}

async function removeMembership(membershipId: number) {
  await api.delete(`/users/${editUser.id}/memberships/${membershipId}`)
  Message.success(t('org.removed_dept'))
  await reloadDrawerUser()
  await loadUsers()
  notifyChanged()
}

function normalizeDeptId(raw: number | string | undefined): number | undefined {
  if (raw === undefined || raw === null || raw === '') return undefined
  if (typeof raw === 'number') return raw > 0 ? raw : undefined
  const m = String(raw).match(/dept-(\d+)/i)
  if (m) return parseInt(m[1], 10)
  const n = parseInt(String(raw), 10)
  return Number.isNaN(n) || n <= 0 ? undefined : n
}

async function addMembership() {
  const deptId = normalizeDeptId(addDeptId.value)
  if (!editUser.id || !deptId) return
  await api.post(`/users/${editUser.id}/memberships`, {
    department_id: deptId,
    role_in_dept: addDeptRole.value,
    job_title: addDeptJob.value,
    is_primary: !editUser.memberships.length,
  })
  Message.success(t('org.joined_dept'))
  addDeptId.value = undefined
  addDeptJob.value = ''
  addDeptRole.value = 'member'
  await reloadDrawerUser()
  await loadUsers()
  notifyChanged()
}

async function reloadDrawerUser() {
  if (!editUser.id) return
  const res = await api.get<ApiResponse<UserDetail>>(`/users/${editUser.id}`)
  if (res.data.ok) {
    editUser.memberships = (res.data.data.memberships || []).map((m) => ({ ...m }))
  }
}

function openCreateUser() {
  createForm.username = ''
  createForm.email = ''
  createForm.display_name = ''
  createForm.password = defaultResetPwd
  createDeptIds.value = []
  createModal.value = true
}

async function createUser() {
  if (!createForm.username.trim()) {
    Message.warning(t('org.fill_username'))
    return
  }
  if (!createForm.email.trim()) {
    Message.warning(t('org.fill_email'))
    return
  }
  const deptIds = normalizeDeptIds(createDeptIds.value as (number | string)[])
  const memberships = deptIds.map((department_id, idx) => ({
    department_id,
    role_in_dept: 'member',
    is_primary: idx === 0,
  }))
  await api.post('/users', {
    username: createForm.username.trim(),
    email: createForm.email.trim(),
    display_name: createForm.display_name.trim() || createForm.username.trim(),
    password: createForm.password || defaultResetPwd,
    memberships,
  })
  createModal.value = false
  Message.success(t('org.saved'))
  await loadUsers()
  notifyChanged()
}

async function loadHolidayRegionOpts() {
  try {
    const res = await api.get<ApiResponse<{ regions: { code: string; name: string; name_en: string }[] }>>(
      '/holidays/regions',
    )
    const isEn = String(locale.value).startsWith('en')
    holidayRegionOpts.value = (res.data.data?.regions || []).map((r) => ({
      value: r.code,
      label: isEn ? r.name_en : r.name,
    }))
  } catch {
    holidayRegionOpts.value = []
  }
}

onMounted(async () => {
  await Promise.all([loadUsers(), loadCompanyTree(), loadFlowRoles(), loadHolidayRegionOpts()])
})
</script>

<style scoped>
.org-users-panel {
  padding: 0 2px;
}

.users-hint {
  margin: 0 0 12px;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.users-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
  align-items: center;
}

.users-search {
  width: 280px;
  flex: 1;
  min-width: 200px;
  max-width: 360px;
}

.users-table :deep(.arco-table-tr) {
  cursor: pointer;
}

.drawer-spin {
  min-height: 200px;
}

.user-field-hint {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.4;
}

.admin-mail-field {
  width: 100%;
}

.admin-mail-input {
  display: block;
  width: 100%;
  height: 32px;
  padding: 0 12px;
  font-size: 14px;
  line-height: 1.5715;
  color: var(--color-text-1, #1d2129);
  background-color: var(--color-fill-2, #f2f3f5);
  border: 1px solid transparent;
  border-radius: var(--border-radius-small, 4px);
  box-sizing: border-box;
  outline: none;
  font-family: inherit;
}

.admin-mail-input:hover {
  background-color: var(--color-fill-3, #e5e6eb);
}

.admin-mail-input:focus {
  background-color: var(--color-bg-2, #fff);
  border-color: rgb(var(--primary-6, 22 93 255));
}

.add-membership-box {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 16px;
}

.add-dept-select {
  min-width: 220px;
  flex: 1;
}

.password-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 24px;
}

.password-input {
  width: 200px;
}

.drawer-footer {
  position: sticky;
  bottom: 0;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  background: var(--surface);
}
</style>
