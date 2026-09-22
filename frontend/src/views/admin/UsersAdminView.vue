<template>
  <div>
    <h1 class="text-xl font-bold mb-4">{{ t('admin.users_title') }}</h1>
    <a-card class="rounded-xl mb-4">
      <a-form :model="createForm" layout="vertical" @submit-success="createUser">
        <a-row :gutter="12">
          <a-col :xs="24" :sm="8"><a-form-item label="用户名" required><a-input v-model="createForm.username" /></a-form-item></a-col>
          <a-col :xs="24" :sm="8"><a-form-item label="显示名"><a-input v-model="createForm.display_name" /></a-form-item></a-col>
          <a-col :xs="24" :sm="8"><a-form-item label="邮箱"><a-input v-model="createForm.email" /></a-form-item></a-col>
          <a-col :xs="24" :sm="8"><a-form-item label="手机"><a-input v-model="createForm.phone" /></a-form-item></a-col>
          <a-col :xs="24" :sm="8"><a-form-item label="密码"><a-input-password v-model="createForm.password" /></a-form-item></a-col>
        </a-row>
        <a-button type="primary" html-type="submit">创建用户</a-button>
      </a-form>
    </a-card>
    <a-table :data="users" row-key="id">
      <template #columns>
        <a-table-column title="用户名" data-index="username" />
        <a-table-column title="显示名" data-index="display_name" />
        <a-table-column title="邮箱" data-index="email" />
        <a-table-column title="手机" data-index="phone" />
        <a-table-column title="状态" :width="72">
          <template #cell="{ record }">{{ record.is_active ? '正常' : '停用' }}</template>
        </a-table-column>
        <a-table-column title="管理员" :width="80">
          <template #cell="{ record }">{{ record.is_system_admin ? '是' : '' }}</template>
        </a-table-column>
        <a-table-column title="操作" :width="160">
          <template #cell="{ record }">
            <a-space>
              <a-button size="mini" type="primary" @click="openEdit(record)">编辑</a-button>
              <a-popconfirm content="确定停用该用户？" @ok="deleteUser(record.id)">
                <a-button size="mini" status="danger" :disabled="!record.is_active">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>

    <a-modal v-model:visible="editVisible" title="编辑用户" :width="520" @ok="saveUser">
      <a-form :model="editForm" layout="vertical">
        <a-form-item label="用户名">
          <a-input :model-value="editForm.username" disabled />
        </a-form-item>
        <a-form-item label="显示名">
          <a-input v-model="editForm.display_name" />
        </a-form-item>
        <a-form-item label="邮箱">
          <a-input v-model="editForm.email" />
        </a-form-item>
        <a-form-item label="手机">
          <a-input v-model="editForm.phone" />
        </a-form-item>
        <a-form-item label="新密码">
          <a-input-password v-model="editForm.password" placeholder="留空则不修改" />
        </a-form-item>
        <a-form-item label="系统管理员">
          <a-switch v-model="editForm.is_system_admin" />
        </a-form-item>
        <a-form-item label="账号启用">
          <a-switch v-model="editForm.is_active" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'

const { t } = useI18n()
const users = ref<Record<string, unknown>[]>([])
const editVisible = ref(false)
const createForm = reactive({
  username: '',
  display_name: '',
  email: '',
  phone: '',
  password: 'ChangeMe123',
})
const editForm = reactive({
  id: 0,
  username: '',
  display_name: '',
  email: '',
  phone: '',
  password: '',
  is_system_admin: false,
  is_active: true,
})

async function load() {
  const res = await api.get<ApiResponse<Record<string, unknown>[]>>('/users')
  if (res.data.ok) users.value = res.data.data
}

async function createUser() {
  await api.post('/users', createForm)
  Message.success(t('common.success'))
  createForm.username = ''
  createForm.display_name = ''
  createForm.email = ''
  createForm.phone = ''
  await load()
}

function openEdit(record: Record<string, unknown>) {
  editForm.id = record.id as number
  editForm.username = record.username as string
  editForm.display_name = (record.display_name as string) || ''
  editForm.email = (record.email as string) || ''
  editForm.phone = (record.phone as string) || ''
  editForm.password = ''
  editForm.is_system_admin = !!record.is_system_admin
  editForm.is_active = record.is_active !== false
  editVisible.value = true
}

async function saveUser() {
  const body: Record<string, unknown> = {
    display_name: editForm.display_name,
    email: editForm.email,
    phone: editForm.phone,
    is_system_admin: editForm.is_system_admin,
    is_active: editForm.is_active,
  }
  if (editForm.password) body.password = editForm.password
  await api.put(`/users/${editForm.id}`, body)
  editVisible.value = false
  Message.success('已保存')
  await load()
}

async function deleteUser(id: number) {
  await api.delete(`/users/${id}`)
  Message.success('用户已停用')
  await load()
}

onMounted(load)
</script>
