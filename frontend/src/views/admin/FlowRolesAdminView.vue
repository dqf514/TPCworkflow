<template>
  <div>
    <h1 class="text-xl font-bold mb-4">{{ t('admin.flow_roles_title') }}</h1>
    <a-row :gutter="16">
      <a-col :xs="24" :lg="12">
        <a-card title="流程角色" class="rounded-xl mb-4">
          <a-form layout="inline" class="mb-4 flex flex-wrap gap-2">
            <a-input v-model="newRole.code" placeholder="编码" class="w-32" />
            <a-input v-model="newRole.name" placeholder="名称" class="w-40" />
            <a-button type="primary" @click="addRole">添加</a-button>
          </a-form>
          <a-table
            :data="roles"
            row-key="id"
            :row-class="(record) => (record.id === selectedRoleId ? 'arco-table-tr-checked' : '')"
            @row-click="(record) => selectRole(record.id)"
          >
            <template #columns>
              <a-table-column title="编码" data-index="code" />
              <a-table-column title="名称" data-index="name" />
              <a-table-column title="状态" :width="72">
                <template #cell="{ record }">{{ record.is_active ? '正常' : '停用' }}</template>
              </a-table-column>
              <a-table-column title="操作" :width="160">
                <template #cell="{ record }">
                  <a-space @click.stop>
                    <a-button size="mini" @click="openRoleEdit(record)">编辑</a-button>
                    <a-popconfirm content="确定停用该角色？" @ok="deleteRole(record.id)">
                      <a-button size="mini" status="danger" :disabled="!record.is_active">删除</a-button>
                    </a-popconfirm>
                  </a-space>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-card>
      </a-col>
      <a-col :xs="24" :lg="12">
        <a-card v-if="selectedRoleId" :title="membersCardTitle" class="rounded-xl">
          <a-form layout="inline" class="mb-3 flex flex-wrap gap-2">
            <a-select
              v-model="newMember.user_id"
              :options="userOpts"
              placeholder="选择用户"
              allow-search
              class="w-48"
            />
            <a-button type="primary" @click="addMember">添加成员</a-button>
          </a-form>
          <a-table :data="members" row-key="id" :pagination="false">
            <template #columns>
              <a-table-column title="姓名">
                <template #cell="{ record }">
                  {{ memberDisplayName(record) }}
                </template>
              </a-table-column>
              <a-table-column title="操作" :width="100">
                <template #cell="{ record }">
                  <a-popconfirm content="移除该成员？" @ok="removeMember(record.id)">
                    <a-button size="mini" status="danger">删除</a-button>
                  </a-popconfirm>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-card>
        <a-empty v-else class="mt-8" description="请选择左侧流程角色" />
      </a-col>
    </a-row>

    <a-modal v-model:visible="roleModal" title="编辑流程角色" @ok="saveRole">
      <a-form :model="roleEdit" layout="vertical">
        <a-form-item label="编码">
          <a-input :model-value="roleEdit.code" disabled />
        </a-form-item>
        <a-form-item label="名称" required>
          <a-input v-model="roleEdit.name" />
        </a-form-item>
        <a-form-item label="说明">
          <a-textarea v-model="roleEdit.description" />
        </a-form-item>
        <a-form-item label="启用">
          <a-switch v-model="roleEdit.is_active" />
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

const { t } = useI18n()

interface FlowRoleMemberRow {
  id: number
  user_id: number
  username?: string
  display_name?: string
}

const roles = ref<Record<string, unknown>[]>([])
const members = ref<FlowRoleMemberRow[]>([])

function memberDisplayName(record: FlowRoleMemberRow) {
  const name = (record.display_name || '').trim()
  if (name) return name
  const uname = (record.username || '').trim()
  if (uname) return uname
  return `用户 #${record.user_id}`
}
const selectedRoleId = ref<number>()

const membersCardTitle = computed(() => {
  const role = roles.value.find((r) => (r.id as number) === selectedRoleId.value)
  const name = String(role?.name || role?.code || '').trim()
  const prefix = '角色成员'
  return name ? `${prefix}（${name}）` : prefix
})

const userOpts = ref<{ label: string; value: number }[]>([])
const newRole = reactive({ code: '', name: '' })
const newMember = reactive({ user_id: undefined as number | undefined })
const roleModal = ref(false)
const roleEdit = reactive({
  id: 0,
  code: '',
  name: '',
  description: '',
  is_active: true,
})

async function load() {
  const res = await api.get<ApiResponse<Record<string, unknown>[]>>('/admin/flow-roles')
  if (res.data.ok) roles.value = res.data.data
}

async function loadUsers() {
  const res = await api.get<ApiResponse<{ id: number; display_name: string; username: string }[]>>('/users')
  if (res.data.ok) {
    userOpts.value = res.data.data.map((u) => ({
      label: u.display_name || u.username,
      value: u.id,
    }))
  }
}

async function selectRole(id: number) {
  selectedRoleId.value = id
  const res = await api.get<ApiResponse<FlowRoleMemberRow[]>>(`/admin/flow-roles/${id}/members`)
  if (res.data.ok) members.value = res.data.data
}

async function addRole() {
  if (!newRole.code || !newRole.name) {
    Message.warning('请填写编码与名称')
    return
  }
  await api.post('/admin/flow-roles', newRole)
  newRole.code = ''
  newRole.name = ''
  Message.success(t('common.success'))
  await load()
}

function openRoleEdit(record: Record<string, unknown>) {
  roleEdit.id = record.id as number
  roleEdit.code = record.code as string
  roleEdit.name = record.name as string
  roleEdit.description = (record.description as string) || ''
  roleEdit.is_active = record.is_active !== false
  roleModal.value = true
}

async function saveRole() {
  await api.put(`/admin/flow-roles/${roleEdit.id}`, {
    name: roleEdit.name,
    description: roleEdit.description,
    is_active: roleEdit.is_active,
  })
  roleModal.value = false
  Message.success('已保存')
  await load()
}

async function deleteRole(id: number) {
  await api.delete(`/admin/flow-roles/${id}`)
  Message.success('角色已停用')
  if (selectedRoleId.value === id) {
    selectedRoleId.value = undefined
    members.value = []
  }
  await load()
}

async function addMember() {
  if (!selectedRoleId.value || !newMember.user_id) {
    Message.warning('请选择用户')
    return
  }
  await api.post(`/admin/flow-roles/${selectedRoleId.value}/members`, {
    user_id: newMember.user_id,
  })
  newMember.user_id = undefined
  Message.success('已添加')
  await selectRole(selectedRoleId.value)
}

async function removeMember(memberId: number) {
  if (!selectedRoleId.value) return
  await api.delete(`/admin/flow-roles/${selectedRoleId.value}/members/${memberId}`)
  Message.success('已移除')
  await selectRole(selectedRoleId.value)
}

onMounted(async () => {
  await load()
  await loadUsers()
})
</script>
