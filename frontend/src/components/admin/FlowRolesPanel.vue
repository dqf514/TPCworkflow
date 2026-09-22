<template>
  <div class="flow-roles-panel">
    <a-alert type="info" class="mb-3" :show-icon="true">
      {{ t('flowRole.usage_hint') }}
    </a-alert>

    <a-form layout="inline" class="mb-4 flex flex-wrap gap-2">
      <a-input v-model="newRole.code" :placeholder="t('flowRole.code_ph')" class="w-36" />
      <a-input v-model="newRole.name" :placeholder="t('flowRole.name_ph')" class="w-40" />
      <a-button type="primary" @click="addRole">{{ t('flowRole.add') }}</a-button>
    </a-form>

    <a-row :gutter="16">
      <a-col :xs="24" :md="11">
        <a-table
          :data="roles"
          row-key="id"
          :pagination="false"
          :row-class="roleRowClass"
          @row-click="(record) => selectRole(record.id)"
        >
          <template #columns>
            <a-table-column :title="t('flowRole.col_code')" data-index="code" :width="120" />
            <a-table-column :title="t('flowRole.col_name')" data-index="name" />
            <a-table-column :title="t('flowRole.col_member_count')" :width="88">
              <template #cell="{ record }">
                <a-tag v-if="record.is_dept_manager_role" color="arcoblue">{{ t('flowRole.org_auto') }}</a-tag>
                <span v-else>{{ record.member_count ?? 0 }}</span>
              </template>
            </a-table-column>
            <a-table-column :title="t('flowRole.col_actions')" :width="150">
              <template #cell="{ record }">
                <a-space @click.stop>
                  <a-button size="mini" @click="openRoleEdit(record)">{{ t('flowRole.edit') }}</a-button>
                  <a-popconfirm :content="t('flowRole.disable_confirm')" @ok="deleteRole(record.id)">
                    <a-button size="mini" status="danger">{{ t('flowRole.delete') }}</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-col>

      <a-col :xs="24" :md="13">
        <a-card v-if="selectedRoleId" :title="membersCardTitle" size="small">
          <a-alert
            v-if="selectedRole?.is_dept_manager_role"
            type="warning"
            class="mb-3"
            :show-icon="true"
          >
            {{ t('flowRole.dept_manager_hint') }}
          </a-alert>

          <template v-else>
            <a-form layout="vertical" class="member-form">
              <a-form-item :label="t('flowRole.batch_add_label')">
                <a-select
                  v-model="batchUserIds"
                  :options="availableUserOpts"
                  multiple
                  allow-search
                  :max-tag-count="4"
                  :placeholder="t('flowRole.batch_add_ph')"
                  class="w-full"
                />
              </a-form-item>
              <a-space wrap>
                <a-button type="primary" :disabled="!batchUserIds.length" @click="saveMembersBatch">
                  {{ t('flowRole.save_members') }}
                </a-button>
                <a-button :disabled="!members.length" @click="clearMembers">
                  {{ t('flowRole.clear_members') }}
                </a-button>
              </a-space>
            </a-form>

            <a-table :data="members" row-key="id" :pagination="false" size="small" class="mt-3">
              <template #columns>
                <a-table-column :title="t('org.col_name')">
                  <template #cell="{ record }">{{ memberDisplayName(record) }}</template>
                </a-table-column>
                <a-table-column :title="t('org.col_email')" data-index="email" />
                <a-table-column :title="t('flowRole.col_actions')" :width="80">
                  <template #cell="{ record }">
                    <a-popconfirm :content="t('flowRole.remove_confirm')" @ok="removeMember(record.user_id)">
                      <a-button size="mini" status="danger">{{ t('flowRole.remove') }}</a-button>
                    </a-popconfirm>
                  </template>
                </a-table-column>
              </template>
            </a-table>
          </template>
        </a-card>
        <a-empty v-else :description="t('flowRole.pick_role')" />
      </a-col>
    </a-row>

    <a-modal v-model:visible="roleModal" :title="t('flowRole.edit_title')" @ok="saveRole">
      <a-form :model="roleEdit" layout="vertical">
        <a-form-item :label="t('flowRole.code')"><a-input :model-value="roleEdit.code" disabled /></a-form-item>
        <a-form-item :label="t('flowRole.name')"><a-input v-model="roleEdit.name" /></a-form-item>
        <a-form-item :label="t('flowRole.description')"><a-textarea v-model="roleEdit.description" /></a-form-item>
        <a-form-item :label="t('flowRole.enabled')"><a-switch v-model="roleEdit.is_active" /></a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'

const { t } = useI18n()

interface FlowRoleRow {
  id: number
  code: string
  name: string
  description?: string
  is_active?: boolean
  member_count?: number
  is_dept_manager_role?: boolean
}

interface FlowRoleMemberRow {
  id: number
  user_id: number
  username?: string
  display_name?: string
  email?: string
}

const roles = ref<FlowRoleRow[]>([])
const members = ref<FlowRoleMemberRow[]>([])
const selectedRoleId = ref<number>()
const batchUserIds = ref<number[]>([])
const userOpts = ref<{ label: string; value: number }[]>([])

const selectedRole = computed(() => roles.value.find((r) => r.id === selectedRoleId.value))

const membersCardTitle = computed(() => {
  const name = (selectedRole.value?.name || selectedRole.value?.code || '').trim()
  const prefix = t('flowRole.members_title_prefix')
  return name ? `${prefix}（${name}）` : prefix
})

const availableUserOpts = computed(() => userOpts.value)

function roleRowClass(record: FlowRoleRow) {
  return record.id === selectedRoleId.value ? 'flow-role-row-selected' : ''
}

function memberDisplayName(record: FlowRoleMemberRow) {
  return (record.display_name || record.username || '').trim() || `用户 #${record.user_id}`
}

const newRole = reactive({ code: '', name: '' })
const roleModal = ref(false)
const roleEdit = reactive({ id: 0, code: '', name: '', description: '', is_active: true })

async function load() {
  const res = await api.get<ApiResponse<FlowRoleRow[]>>('/admin/flow-roles')
  if (res.data.ok) roles.value = res.data.data
}

async function loadUsers() {
  const res = await api.get<ApiResponse<{ id: number; display_name: string; username: string; email?: string }[]>>('/users')
  if (res.data.ok) {
    userOpts.value = res.data.data
      .filter((u) => u.id)
      .map((u) => ({
        label: `${u.display_name || u.username}${u.email ? `（${u.email}）` : ''}`,
        value: u.id,
      }))
  }
}

async function selectRole(id: number) {
  selectedRoleId.value = id
  await loadMembers(id)
}

async function loadMembers(roleId: number) {
  const res = await api.get<ApiResponse<FlowRoleMemberRow[]>>(`/admin/flow-roles/${roleId}/members`)
  if (res.data.ok) {
    members.value = res.data.data
    batchUserIds.value = res.data.data.map((m) => m.user_id)
  }
}

watch(selectedRoleId, (id) => {
  if (id) void loadMembers(id)
})

async function addRole() {
  if (!newRole.code || !newRole.name) {
    Message.warning(`${t('flowRole.code_ph')} / ${t('flowRole.name_ph')}`)
    return
  }
  const res = await api.post<ApiResponse<unknown>>('/admin/flow-roles', newRole)
  if (!res.data.ok) {
    Message.error(res.data.message || '创建失败')
    return
  }
  newRole.code = ''
  newRole.name = ''
  Message.success(t('common.success'))
  await load()
}

function openRoleEdit(record: FlowRoleRow) {
  Object.assign(roleEdit, {
    id: record.id,
    code: record.code,
    name: record.name,
    description: record.description || '',
    is_active: record.is_active !== false,
  })
  roleModal.value = true
}

async function saveRole() {
  const res = await api.put<ApiResponse<unknown>>(`/admin/flow-roles/${roleEdit.id}`, roleEdit)
  if (!res.data.ok) {
    Message.error(res.data.message || '保存失败')
    return false
  }
  roleModal.value = false
  Message.success(t('org.saved'))
  await load()
  return true
}

async function deleteRole(id: number) {
  await api.delete(`/admin/flow-roles/${id}`)
  Message.success(t('common.success'))
  if (selectedRoleId.value === id) {
    selectedRoleId.value = undefined
    members.value = []
  }
  await load()
}

async function saveMembersBatch() {
  if (!selectedRoleId.value) return
  const res = await api.put<ApiResponse<FlowRoleMemberRow[]>>(
    `/admin/flow-roles/${selectedRoleId.value}/members/batch`,
    { user_ids: batchUserIds.value },
  )
  if (!res.data.ok) {
    Message.error(res.data.message || '保存失败')
    return
  }
  Message.success(t('flowRole.save_members_ok'))
  members.value = res.data.data
  await load()
}

async function clearMembers() {
  batchUserIds.value = []
  await saveMembersBatch()
}

async function removeMember(userId: number) {
  batchUserIds.value = batchUserIds.value.filter((id) => id !== userId)
  await saveMembersBatch()
}

onMounted(async () => {
  await load()
  await loadUsers()
})
</script>

<style scoped>
.flow-roles-panel {
  width: 100%;
}

.mb-3 {
  margin-bottom: 12px;
}

.mt-3 {
  margin-top: 12px;
}

.member-form :deep(.arco-form-item) {
  margin-bottom: 8px;
}

:deep(.flow-role-row-selected > .arco-table-td) {
  background: var(--color-primary-light-1);
}
</style>
