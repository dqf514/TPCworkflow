<template>
  <PageChrome :title="t('org.title')" :description="t('org.subtitle')" class="org-structure-page page-shell">
    <a-tabs v-model:active-key="mainTab" type="rounded" class="org-tabs" @change="onMainTabChange">
      <a-tab-pane key="structure" :title="t('org.tab_structure')">
        <div class="structure-toolbar">
          <span class="toolbar-company-name">{{ companyName }}</span>
          <a-input-search
            v-model="searchQ"
            :placeholder="t('org.search_ph')"
            class="toolbar-search"
            allow-clear
            @search="onSearch"
          />
          <a-space wrap class="toolbar-actions">
            <a-button :disabled="!companyId" @click="openDeptModal()">{{ t('org.new_dept') }}</a-button>
          </a-space>
        </div>

        <div class="structure-body">
          <aside class="structure-tree-panel">
            <a-spin :loading="treeLoading" class="tree-spin">
              <a-tree
                v-if="displayTree.length"
                :key="structureTreeKey"
                :data="displayTree"
                :selected-keys="selectedTreeKeys"
                :expanded-keys="expandedKeys"
                block-node
                show-line
                @select="onTreeSelect"
                @expand="onTreeExpand"
              >
                <template #title="nodeData">
                  <div class="tree-node-row">
                    <component
                      :is="nodeData?.nodeType === 'company' ? IconHome : IconFolder"
                      class="tree-node-icon"
                    />
                    <span class="tree-node-label">
                      <span class="tree-node-name">{{ nodeData?.name || nodeData?.title }}</span>
                      <span
                        v-if="nodeData?.manager?.display_name && nodeData?.nodeType !== 'company'"
                        class="tree-node-manager"
                      >
                        {{ t('org.manager_label', { name: nodeData.manager.display_name }) }}
                      </span>
                    </span>
                    <a-tag
                      v-if="nodeData?.nodeType !== 'company'"
                      size="small"
                      class="tree-node-count"
                    >
                      {{ t('org.member_count', { n: nodeData?.member_count ?? 0 }) }}
                    </a-tag>
                  </div>
                </template>
              </a-tree>
              <a-empty v-else :description="t('org.tree_empty')" class="tree-empty" />
            </a-spin>
          </aside>

          <main class="structure-main-panel">
            <template v-if="selectedDeptId">
              <div class="panel-head flex flex-wrap justify-between gap-2">
                <span class="panel-head-title">
                  <span class="dept-path-label">{{ deptPathLabel }}</span>
                  <span class="dept-member-count">{{ deptMemberCount }}人</span>
                </span>
                <a-space wrap>
                  <a-button type="primary" @click="openAddMember">{{ t('org.add_member') }}</a-button>
                  <a-button @click="openDeptModal(selectedDeptId)">{{ t('org.new_subdept') }}</a-button>
                  <a-button @click="openDeptEdit">{{ t('org.edit_dept') }}</a-button>
                  <a-popconfirm :content="t('org.delete_dept_confirm')" @ok="deleteDept">
                    <a-button status="danger">{{ t('org.delete_dept') }}</a-button>
                  </a-popconfirm>
                </a-space>
              </div>
              <div class="panel-body">
                <a-table
                  :data="members"
                  row-key="membership_id"
                  :pagination="false"
                  :loading="membersLoading"
                  :scroll="{ x: 'max-content' }"
                  @row-click="(r: MemberRow) => openMemberProfile(r)"
                >
                  <template #columns>
                    <a-table-column :title="t('org.col_name')" :width="180">
                      <template #cell="{ record }">
                        <a-link @click.stop="openMemberProfile(record)">{{ record.display_name }}</a-link>
                        <a-tag v-if="record.role_in_dept === 'manager'" color="arcoblue" size="small" class="ml-2">
                          {{ t('org.role_manager') }}
                        </a-tag>
                      </template>
                    </a-table-column>
                    <a-table-column :title="t('org.col_username')" data-index="username" :width="130" />
                    <a-table-column :title="t('org.col_job')" data-index="job_title" :width="150" />
                    <a-table-column :title="t('org.col_dept_count')" :width="88">
                      <template #cell="{ record }">
                        {{ record.membership_count ?? 1 }}
                      </template>
                    </a-table-column>
                    <a-table-column :title="t('org.col_dept_role')" :width="110">
                      <template #cell="{ record }">
                        {{ record.role_in_dept === 'manager' ? t('org.role_manager') : t('org.role_member') }}
                      </template>
                    </a-table-column>
                    <a-table-column :title="t('org.col_actions')" :width="280" fixed="right">
                      <template #cell="{ record }">
                        <a-space>
                          <a-button size="mini" @click.stop="openMemberProfile(record)">{{ t('org.member_detail') }}</a-button>
                          <a-button
                            v-if="record.role_in_dept !== 'manager'"
                            size="mini"
                            type="primary"
                            @click.stop="setManager(record)"
                          >
                            {{ t('org.set_manager') }}
                          </a-button>
                          <a-popconfirm
                            :content="t('org.remove_dept_confirm')"
                            @ok="removeMember(record.membership_id)"
                          >
                            <a-button size="mini" status="danger" @click.stop>{{ t('org.remove_from_dept') }}</a-button>
                          </a-popconfirm>
                        </a-space>
                      </template>
                    </a-table-column>
                  </template>
                </a-table>
              </div>
            </template>
            <template v-else-if="companyId && companyName">
              <div class="panel-head">{{ companyName }}</div>
              <div class="panel-body company-overview">
                <div class="company-facts">
                  <div class="company-fact">
                    <span class="company-fact-label">{{ t('org.org_name') }}</span>
                    <span class="company-fact-value">{{ companyName }}</span>
                  </div>
                  <div class="company-fact">
                    <span class="company-fact-label">{{ t('org.dept_count') }}</span>
                    <span class="company-fact-value">{{ deptCount }}</span>
                  </div>
                  <div class="company-fact">
                    <span class="company-fact-label">{{ t('org.member_total') }}</span>
                    <span class="company-fact-value">{{ totalMemberCount }}</span>
                  </div>
                  <div class="company-fact company-fact--wide">
                    <span class="company-fact-label">{{ t('org.tips') }}</span>
                    <span class="company-fact-value company-fact-value--muted">{{ t('org.tips_text') }}</span>
                  </div>
                </div>
              </div>
            </template>
            <a-empty v-else class="panel-empty" :description="t('org.loading')" />
          </main>
        </div>
      </a-tab-pane>

      <a-tab-pane key="users" :title="t('org.tab_users')">
        <OrgUsersPanel @changed="onUsersPanelChanged" />
      </a-tab-pane>

      <a-tab-pane key="roles" :title="t('org.tab_roles')">
        <p class="text-sm text-gray-500 mb-3">
          {{ t('org.roles_hint') }}
        </p>
        <FlowRolesPanel />
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:visible="deptModal" :title="deptEdit.id ? t('org.edit_dept_title') : t('org.new_dept_title')" @ok="saveDept">
      <a-form :model="deptEdit" layout="vertical">
        <a-form-item :label="t('org.dept_name')" required><a-input v-model="deptEdit.name" /></a-form-item>
        <a-form-item :label="t('org.parent_dept')">
          <a-tree-select
            v-model="deptEdit.parent_id"
            :data="deptTreeForSelect"
            :placeholder="t('org.parent_ph')"
            allow-clear
            :field-names="treeFieldNames"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:visible="memberModal" :title="t('org.add_member_title')" @ok="saveMember" :width="560">
      <a-tabs v-model:active-key="memberAddTab">
        <a-tab-pane key="exist" :title="t('org.tab_exist_user')">
          <a-select
            v-model="memberForm.user_ids"
            :options="addMemberUserOpts"
            multiple
            allow-search
            :max-tag-count="4"
            :placeholder="t('org.pick_users')"
            class="w-full"
          />
          <p class="text-xs text-gray-500 mt-2">{{ t('org.pick_users_hint') }}</p>
          <p v-if="!selectedDeptId" class="text-xs text-gray-500 mt-1">{{ t('org.pick_dept_first') }}</p>
        </a-tab-pane>
        <a-tab-pane key="new" :title="t('org.tab_new_user')">
          <a-form :model="newUserForm" layout="vertical">
            <a-form-item :label="t('org.username')" required><a-input v-model="newUserForm.username" /></a-form-item>
            <a-form-item :label="t('org.email')" required><a-input v-model="newUserForm.email" /></a-form-item>
            <a-form-item :label="t('org.display_name')"><a-input v-model="newUserForm.display_name" /></a-form-item>
            <a-form-item :label="t('org.password')"><a-input-password v-model="newUserForm.password" /></a-form-item>
            <a-form-item :label="t('org.depts_optional')">
              <a-tree-select
                v-model="newUserDeptIds"
                :data="treeData"
                multiple
                tree-checkable
                allow-clear
                :placeholder="t('org.no_dept_yet')"
                :field-names="treeFieldNames"
                class="w-full"
              />
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>
      <a-form v-if="memberAddTab === 'exist'" :model="memberForm" layout="vertical" class="mt-3">
        <a-form-item :label="t('org.dept_role')">
          <a-radio-group v-model="memberForm.role_in_dept">
            <a-radio value="member">{{ t('org.role_member') }}</a-radio>
            <a-radio value="manager">{{ t('org.role_manager') }}</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item :label="t('org.job_title')"><a-input v-model="memberForm.job_title" /></a-form-item>
      </a-form>
      <a-form v-else :model="memberForm" layout="vertical" class="mt-3">
        <a-form-item :label="t('org.first_dept_role')">
          <a-radio-group v-model="memberForm.role_in_dept">
            <a-radio value="member">{{ t('org.role_member') }}</a-radio>
            <a-radio value="manager">{{ t('org.role_manager') }}</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item :label="t('org.job_title')"><a-input v-model="memberForm.job_title" /></a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:visible="profileModal"
      :title="profileUser?.display_name || t('org.profile_title')"
      :footer="false"
      :width="640"
    >
      <a-spin :loading="profileLoading">
        <template v-if="profileUser">
          <a-descriptions :column="1" bordered size="medium" class="mb-4">
            <a-descriptions-item :label="t('org.username')">{{ profileUser.username }}</a-descriptions-item>
            <a-descriptions-item :label="t('org.display_name')">{{ profileUser.display_name }}</a-descriptions-item>
            <a-descriptions-item :label="t('org.email')">{{ profileUser.email || '—' }}</a-descriptions-item>
            <a-descriptions-item :label="t('org.phone')">{{ profileUser.phone || '—' }}</a-descriptions-item>
            <a-descriptions-item :label="t('org.holiday_regions')">
              {{ profileHolidayLabel || t('org.holiday_regions_inherit') }}
            </a-descriptions-item>
          </a-descriptions>
          <div class="text-sm font-semibold mb-2">{{ t('org.depts') }}</div>
          <div v-if="profileUser.memberships?.length" class="flex flex-wrap gap-2 mb-4">
            <a-tag
              v-for="m in profileUser.memberships"
              :key="m.membership_id"
              closable
              :color="m.is_primary ? 'arcoblue' : undefined"
              @close="removeMembershipFromProfile(m.membership_id)"
            >
              {{ m.department_path || m.department_name }}
              <span v-if="m.is_primary" class="ml-1 opacity-80">{{ t('org.primary_badge') }}</span>
            </a-tag>
          </div>
          <a-empty v-else :description="t('org.no_dept')" class="mb-4" />
          <a-space>
            <a-button type="primary" @click="openUserEditFromProfile">{{ t('org.edit_profile') }}</a-button>
            <a-button v-if="selectedDeptId" @click="openAddDeptToProfile">{{ t('org.join_current_dept') }}</a-button>
          </a-space>
        </template>
      </a-spin>
    </a-modal>

    <a-modal v-model:visible="userModal" :title="t('org.edit_user')" @ok="saveUser">
      <a-form :model="userEdit" layout="vertical">
        <a-form-item :label="t('org.display_name')"><a-input v-model="userEdit.display_name" /></a-form-item>
        <a-form-item :label="t('org.contact_email')">
          <div class="admin-mail-field">
            <input
              v-model="userEditMailbox"
              type="text"
              class="admin-mail-input"
              :placeholder="EMAIL_PLACEHOLDER"
              spellcheck="false"
            />
          </div>
          <template #extra>
            <span class="text-xs text-gray-500">{{ t('org.email_admin_hint') }}</span>
          </template>
        </a-form-item>
        <a-form-item :label="t('org.phone')"><a-input v-model="userEdit.phone" /></a-form-item>
        <a-form-item :label="t('org.job_title')"><a-input v-model="userEdit.job_title" :placeholder="t('org.job_ph')" /></a-form-item>
        <a-form-item :label="t('org.holiday_regions')">
          <a-select
            v-model="userEdit.holiday_regions"
            :options="holidayRegionOpts"
            multiple
            allow-clear
            allow-search
            :placeholder="t('org.holiday_regions_ph')"
          />
          <template #extra>{{ t('org.holiday_regions_hint') }}</template>
        </a-form-item>
        <a-form-item :label="t('org.new_password')"><a-input-password v-model="userEdit.password" :placeholder="t('org.password_keep')" /></a-form-item>
        <a-form-item :label="t('org.membership_role')">
          <a-radio-group v-model="userEdit.role_in_dept">
            <a-radio value="member">{{ t('org.role_member') }}</a-radio>
            <a-radio value="manager">{{ t('org.role_manager') }}</a-radio>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-modal>
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { IconFolder, IconHome } from '@arco-design/web-vue/es/icon'
import { api, type ApiResponse } from '@/api/client'
import FlowRolesPanel from '@/components/admin/FlowRolesPanel.vue'
import OrgUsersPanel from '@/components/admin/OrgUsersPanel.vue'
import PageChrome from '@/components/layout/PageChrome.vue'
import { useBrandingStore } from '@/stores/branding'

const { t, locale } = useI18n()

const EMAIL_PLACEHOLDER = 'user@example.com'

interface TreeNode {
  key: string
  title: string
  id: number
  name: string
  nodeType?: 'company' | 'department'
  isLeaf?: boolean
  member_count?: number
  manager?: { display_name: string; user_id: number; membership_id: number }
  children?: TreeNode[]
}

interface MemberRow {
  membership_id: number
  user_id: number
  username: string
  display_name: string
  role_in_dept: string
  job_title?: string
  membership_count?: number
}

interface UserMembership {
  membership_id: number
  department_id: number
  department_name?: string
  department_path?: string
  is_primary: boolean
  role_in_dept: string
  job_title?: string
}

interface UserProfileDetail {
  id: number
  username: string
  display_name: string
  email?: string
  phone?: string
  holiday_regions?: string[]
  memberships: UserMembership[]
}

interface StructurePayload {
  company: { name: string }
  tree: TreeNode[]
}

const route = useRoute()
const router = useRouter()
const branding = useBrandingStore()
const mainTab = ref('structure')
const companyId = ref<number>()
const companyName = ref('')
const treeData = ref<TreeNode[]>([])
const structureTreeKey = ref(0)
const treeLoading = ref(false)
const members = ref<MemberRow[]>([])
const membersLoading = ref(false)
const selectedTreeKeys = ref<string[]>([])
const expandedKeys = ref<string[]>([])
const selectedDeptId = ref<number>()
const selectedDeptName = ref('')

const deptPathLabel = computed(() => {
  if (!selectedDeptId.value || !selectedDeptName.value) return ''
  const hit = findNodeWithParent(treeData.value, `dept-${selectedDeptId.value}`)
  const parentName = hit?.parent?.name?.trim()
  return parentName
    ? `${parentName} / ${selectedDeptName.value}`
    : selectedDeptName.value
})

const deptMemberCount = computed(() => {
  if (!selectedDeptId.value) return 0
  if (!membersLoading.value) return members.value.length
  const hit = findNodeWithParent(treeData.value, `dept-${selectedDeptId.value}`)
  return hit?.node?.member_count ?? members.value.length
})
const searchQ = ref('')
const userOpts = ref<{ label: string; value: number }[]>([])

const deptModal = ref(false)
const memberModal = ref(false)
const memberAddTab = ref('exist')
const userModal = ref(false)
const profileModal = ref(false)
const profileLoading = ref(false)
const profileUser = ref<UserProfileDetail | null>(null)
const profileHolidayLabel = computed(() => {
  const codes = profileUser.value?.holiday_regions || []
  if (!codes.length) return ''
  const map = Object.fromEntries(holidayRegionOpts.value.map((o) => [o.value, o.label]))
  return codes.map((c) => map[c] || c).join('、')
})
const newUserDeptIds = ref<(number | string)[]>([])

const deptEdit = reactive({
  id: 0,
  name: '',
  parent_id: undefined as string | number | undefined,
})
const memberForm = reactive({
  user_ids: [] as number[],
  role_in_dept: 'member',
  job_title: '',
})

const addMemberUserOpts = computed(() => {
  const inDept = new Set(members.value.map((m) => m.user_id))
  return userOpts.value.filter((o) => !inDept.has(o.value))
})
const newUserForm = reactive({
  username: '',
  email: '',
  display_name: '',
  password: 'ChangeMe123',
})
const userEdit = reactive({
  membership_id: 0,
  user_id: 0,
  display_name: '',
  phone: '',
  password: '',
  job_title: '',
  role_in_dept: 'member',
  holiday_regions: [] as string[],
})

const userEditMailbox = ref('')
const holidayRegionOpts = ref<{ label: string; value: string }[]>([])

const treeFieldNames = { key: 'key', title: 'title', children: 'children' }

const displayTree = computed<TreeNode[]>(() => {
  if (!companyId.value || !companyName.value) return []
  return [
    {
      key: `company-${companyId.value}`,
      title: companyName.value,
      id: companyId.value,
      name: companyName.value,
      nodeType: 'company',
      children: treeData.value,
      isLeaf: !treeData.value.length,
    },
  ]
})

function collectDescendantIds(node: TreeNode): Set<number> {
  const ids = new Set<number>([node.id])
  for (const ch of node.children || []) {
    collectDescendantIds(ch).forEach((id) => ids.add(id))
  }
  return ids
}

function filterTreeExcludeIds(nodes: TreeNode[], excludeIds: Set<number>): TreeNode[] {
  return nodes
    .filter((n) => !excludeIds.has(n.id))
    .map((n) => {
      const children = n.children?.length ? filterTreeExcludeIds(n.children, excludeIds) : undefined
      return {
        ...n,
        children: children?.length ? children : undefined,
        isLeaf: !children?.length,
      }
    })
}

const deptTreeForSelect = computed(() => {
  if (!deptEdit.id) return treeData.value
  const self = findNode(treeData.value, `dept-${deptEdit.id}`)
  if (!self) return treeData.value
  return filterTreeExcludeIds(treeData.value, collectDescendantIds(self))
})

function countDepts(nodes: TreeNode[]): number {
  let n = 0
  for (const node of nodes) {
    n += 1
    if (node.children?.length) n += countDepts(node.children)
  }
  return n
}

function sumMembers(nodes: TreeNode[]): number {
  let s = 0
  for (const node of nodes) {
    s += node.member_count || 0
    if (node.children?.length) s += sumMembers(node.children)
  }
  return s
}

const deptCount = computed(() => countDepts(treeData.value))
const totalMemberCount = computed(() => sumMembers(treeData.value))

function collectExpandKeys(nodes: TreeNode[]): string[] {
  const keys: string[] = []
  for (const n of nodes) {
    keys.push(n.key)
    if (n.children?.length) keys.push(...collectExpandKeys(n.children))
  }
  return keys
}

watch(
  () => route.query.tab,
  (tab) => {
    if (tab === 'roles') mainTab.value = 'roles'
    else if (tab === 'users') mainTab.value = 'users'
  },
  { immediate: true },
)

async function onUsersPanelChanged() {
  await loadUserOpts()
  await loadStructure()
  if (selectedDeptId.value) await loadMembers(selectedDeptId.value)
}

function onMainTabChange(key: string | number) {
  const k = String(key)
  if (route.query.tab === k) return
  router.replace({ name: route.name || 'admin-org', query: { ...route.query, tab: k } })
}

watch(companyId, async (id) => {
  selectedDeptId.value = undefined
  selectedDeptName.value = ''
  members.value = []
  if (!id) {
    selectedTreeKeys.value = []
    expandedKeys.value = []
    treeData.value = []
    companyName.value = ''
    return
  }
  selectedTreeKeys.value = [`company-${id}`]
  await loadStructure()
})

watch(
  displayTree,
  (tree) => {
    expandedKeys.value = collectExpandKeys(tree)
  },
  { deep: true },
)

async function loadPrimary() {
  await branding.load()
  const res = await api.get('/org/primary') as { data: ApiResponse<{ id: number; name: string }> }
  if (res.data.ok) {
    companyId.value = res.data.data.id
    companyName.value = res.data.data.name || branding.companyName
    selectedTreeKeys.value = [`company-${res.data.data.id}`]
    await loadStructure()
  }
}

async function loadStructure() {
  if (!companyId.value) return
  treeLoading.value = true
  try {
    const res = await api.get(
      `/org/companies/${companyId.value}/structure`,
    ) as { data: ApiResponse<StructurePayload> }
    if (res.data.ok) {
      companyName.value = res.data.data.company.name || branding.companyName
      treeData.value = annotateDeptNodes(res.data.data.tree)
      structureTreeKey.value += 1
    }
  } finally {
    treeLoading.value = false
  }
}

function annotateDeptNodes(nodes: TreeNode[]): TreeNode[] {
  return nodes.map((n) => {
    const kids = annotateDeptNodes(n.children || [])
    return {
      ...n,
      nodeType: 'department' as const,
      title: n.name,
      children: kids,
      isLeaf: kids.length === 0,
    }
  })
}

async function loadMembers(deptId: number) {
  if (!companyId.value) return
  membersLoading.value = true
  try {
    const res = await api.get<ApiResponse<MemberRow[]>>(
      `/org/companies/${companyId.value}/departments/${deptId}/members`,
    )
    if (res.data.ok) members.value = res.data.data
  } finally {
    membersLoading.value = false
  }
}

async function loadUserOpts() {
  const res = await api.get<ApiResponse<{ id: number; display_name: string; username: string }[]>>('/users')
  if (res.data.ok) {
    userOpts.value = res.data.data.map((u) => ({
      label: `${u.display_name || u.username} (${u.username})`,
      value: u.id,
    }))
  }
}

function findNode(nodes: TreeNode[], key: string): TreeNode | null {
  return findNodeWithParent(nodes, key)?.node ?? null
}

function findNodeWithParent(
  nodes: TreeNode[],
  key: string,
  parent: TreeNode | null = null,
): { node: TreeNode; parent: TreeNode | null } | null {
  for (const n of nodes) {
    if (n.key === key) return { node: n, parent }
    if (n.children?.length) {
      const hit = findNodeWithParent(n.children, key, n)
      if (hit) return hit
    }
  }
  return null
}

function onTreeExpand(keys: (string | number)[]) {
  expandedKeys.value = keys.map(String)
}

function onTreeSelect(keys: (string | number)[]) {
  const key = String(keys[0] || '')
  if (!key) return
  selectedTreeKeys.value = [key]
  if (key.startsWith('company-')) {
    selectedDeptId.value = undefined
    selectedDeptName.value = ''
    members.value = []
    return
  }
  if (!key.startsWith('dept-')) return
  const node = findNode(treeData.value, key)
  if (!node) return
  selectedDeptId.value = node.id
  selectedDeptName.value = node.name
  loadMembers(node.id)
}

function normalizeParentId(raw: number | string | undefined | null): number | undefined {
  if (raw === undefined || raw === null || raw === '') return undefined
  if (typeof raw === 'number') return raw > 0 ? raw : undefined
  const m = String(raw).match(/dept-(\d+)/i)
  if (m) return parseInt(m[1], 10)
  const n = parseInt(String(raw), 10)
  return Number.isNaN(n) || n <= 0 ? undefined : n
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

function deptSelectKey(deptId?: number) {
  return deptId ? `dept-${deptId}` : undefined
}

function openDeptModal(parentKey?: number) {
  deptEdit.id = 0
  deptEdit.name = ''
  deptEdit.parent_id = deptSelectKey(parentKey)
  deptModal.value = true
}

function openDeptEdit() {
  if (!selectedDeptId.value) return
  deptEdit.id = selectedDeptId.value
  deptEdit.name = selectedDeptName.value
  const hit = findNodeWithParent(treeData.value, `dept-${selectedDeptId.value}`)
  deptEdit.parent_id = hit?.parent ? deptSelectKey(hit.parent.id) : undefined
  deptModal.value = true
}

async function saveDept() {
  if (!companyId.value || !deptEdit.name.trim()) return
  const parentId = normalizeParentId(deptEdit.parent_id)
  try {
    if (deptEdit.id) {
      await api.put(`/org/companies/${companyId.value}/departments/${deptEdit.id}`, {
        name: deptEdit.name,
        parent_id: parentId ?? null,
      })
    } else {
      const res = await api.post<ApiResponse<{ id: number; name: string }>>(
        `/org/companies/${companyId.value}/departments`,
        {
          name: deptEdit.name,
          parent_id: parentId,
        },
      )
      deptModal.value = false
      Message.success(t('org.saved'))
      await loadStructure()
      const newId = res.data.ok ? res.data.data?.id : undefined
      const expandKeys = new Set(expandedKeys.value)
      expandKeys.add(`company-${companyId.value}`)
      if (parentId) expandKeys.add(`dept-${parentId}`)
      if (newId) {
        expandKeys.add(`dept-${newId}`)
        selectedTreeKeys.value = [`dept-${newId}`]
        selectedDeptId.value = newId
        selectedDeptName.value = deptEdit.name.trim()
        await loadMembers(newId)
      }
      expandedKeys.value = [...expandKeys]
      return
    }
    deptModal.value = false
    Message.success(t('org.saved'))
    await loadStructure()
    if (parentId) {
      expandedKeys.value = [...new Set([...expandedKeys.value, `dept-${parentId}`, `company-${companyId.value}`])]
    }
    if (selectedDeptId.value) await loadMembers(selectedDeptId.value)
  } catch (e: unknown) {
    Message.error(e instanceof Error ? e.message : t('org.save_failed'))
  }
}

async function deleteDept() {
  if (!companyId.value || !selectedDeptId.value) return
  try {
    await api.delete(`/org/companies/${companyId.value}/departments/${selectedDeptId.value}`)
    Message.success(t('org.dept_deleted'))
    selectedDeptId.value = undefined
    selectedDeptName.value = ''
    members.value = []
    selectedTreeKeys.value = companyId.value ? [`company-${companyId.value}`] : []
    await loadStructure()
  } catch (e: unknown) {
    Message.error(e instanceof Error ? e.message : t('org.delete_failed'))
  }
}

function openAddMember() {
  memberForm.user_ids = []
  memberForm.role_in_dept = 'member'
  memberForm.job_title = ''
  memberAddTab.value = 'exist'
  newUserDeptIds.value = selectedDeptId.value ? [deptSelectKey(selectedDeptId.value)!] : []
  memberModal.value = true
}

async function saveMember() {
  if (!companyId.value) return
  if (memberAddTab.value === 'exist') {
    if (!selectedDeptId.value) return Message.warning(t('org.pick_dept_first'))
    if (!memberForm.user_ids.length) return Message.warning(t('org.pick_users_warn'))
    let added = 0
    let skipped = 0
    for (const user_id of memberForm.user_ids) {
      try {
        await api.post(`/org/companies/${companyId.value}/departments/${selectedDeptId.value}/members`, {
          user_id,
          role_in_dept: memberForm.role_in_dept,
          job_title: memberForm.job_title,
        })
        added++
      } catch {
        skipped++
      }
    }
    if (!added) {
      return Message.warning(t('org.members_batch_none'))
    }
    if (skipped) {
      Message.warning(t('org.members_batch_partial', { added, skipped }))
    }
  } else {
    if (!newUserForm.username.trim()) return Message.warning(t('org.fill_username'))
    if (!newUserForm.email.trim()) return Message.warning(t('org.fill_email'))
    const deptIds = normalizeDeptIds(newUserDeptIds.value as (number | string)[])
    if (!deptIds.length && selectedDeptId.value) deptIds.push(selectedDeptId.value)
    const memberships = deptIds.map((department_id, idx) => ({
      department_id,
      role_in_dept: memberForm.role_in_dept,
      job_title: memberForm.job_title,
      is_primary: idx === 0,
    }))
    await api.post('/users', {
      username: newUserForm.username,
      email: newUserForm.email,
      display_name: newUserForm.display_name || newUserForm.username,
      password: newUserForm.password,
      memberships,
    })
  }
  memberModal.value = false
  Message.success(t('org.saved'))
  await loadStructure()
  if (selectedDeptId.value) await loadMembers(selectedDeptId.value)
  await loadUserOpts()
}

async function openMemberProfile(record: MemberRow) {
  profileLoading.value = true
  profileModal.value = true
  try {
    const res = await api.get(`/users/${record.user_id}`) as { data: ApiResponse<UserProfileDetail> }
    if (res.data.ok) profileUser.value = res.data.data
  } finally {
    profileLoading.value = false
  }
}

async function reloadProfile() {
  if (!profileUser.value) return
  const res = await api.get(`/users/${profileUser.value.id}`) as { data: ApiResponse<UserProfileDetail> }
  if (res.data.ok) profileUser.value = res.data.data
}

async function removeMembershipFromProfile(membershipId: number) {
  if (!profileUser.value) return
  await api.delete(`/users/${profileUser.value.id}/memberships/${membershipId}`)
  Message.success(t('org.removed_dept'))
  await reloadProfile()
  await loadStructure()
  if (selectedDeptId.value) await loadMembers(selectedDeptId.value)
}

function openUserEditFromProfile() {
  if (!profileUser.value) return
  const m =
    profileUser.value.memberships?.find((x) => x.department_id === selectedDeptId.value)
    || profileUser.value.memberships?.[0]
  openUserEdit({
    membership_id: m?.membership_id || 0,
    user_id: profileUser.value.id,
    display_name: profileUser.value.display_name,
    role_in_dept: m?.role_in_dept || 'member',
    username: profileUser.value.username,
    job_title: m?.job_title,
  })
  profileModal.value = false
}

async function openAddDeptToProfile() {
  if (!profileUser.value || !selectedDeptId.value || !companyId.value) return
  await api.post(`/users/${profileUser.value.id}/memberships`, {
    department_id: selectedDeptId.value,
    role_in_dept: 'member',
    is_primary: !profileUser.value.memberships?.length,
  })
  Message.success(t('org.joined_dept'))
  await reloadProfile()
  await loadStructure()
  await loadMembers(selectedDeptId.value)
}

async function setManager(record: MemberRow) {
  await api.put(`/org/memberships/${record.membership_id}`, { role_in_dept: 'manager' })
  Message.success(t('org.set_manager_ok'))
  await loadMembers(selectedDeptId.value!)
  await loadStructure()
}

async function openUserEdit(record: MemberRow) {
  userEdit.membership_id = record.membership_id
  userEdit.user_id = record.user_id
  userEdit.display_name = record.display_name
  userEdit.role_in_dept = record.role_in_dept
  userEdit.job_title = record.job_title || ''
  userEdit.password = ''
  userEditMailbox.value = ''
  userEdit.phone = ''
  userEdit.holiday_regions = []
  const res = await api.get<ApiResponse<{
    email?: string
    phone?: string
    display_name?: string
    holiday_regions?: string[]
  }>>(
    `/users/${record.user_id}`,
  )
  if (res.data.ok) {
    userEditMailbox.value = res.data.data.email || ''
    userEdit.phone = res.data.data.phone || ''
    userEdit.display_name = res.data.data.display_name || userEdit.display_name
    userEdit.holiday_regions = [...(res.data.data.holiday_regions || [])]
  }
  userModal.value = true
}

async function saveUser() {
  if (!userEditMailbox.value.trim()) return Message.warning(t('org.fill_email'))
  const body: Record<string, unknown> = {
    display_name: userEdit.display_name,
    email: userEditMailbox.value.trim(),
    phone: userEdit.phone,
    holiday_regions: userEdit.holiday_regions,
  }
  if (userEdit.password) body.password = userEdit.password
  await api.put(`/users/${userEdit.user_id}`, body)
  await api.put(`/org/memberships/${userEdit.membership_id}`, {
    role_in_dept: userEdit.role_in_dept,
    job_title: userEdit.job_title,
  })
  userModal.value = false
  Message.success(t('org.saved'))
  await loadMembers(selectedDeptId.value!)
}

async function removeMember(membershipId: number) {
  await api.delete(`/org/memberships/${membershipId}`)
  Message.success(t('org.removed_keep_account'))
  await loadMembers(selectedDeptId.value!)
  await loadStructure()
}

async function onSearch() {
  if (!searchQ.value.trim() || !companyId.value) return
  const res = await api.get<ApiResponse<{ departments: { id: number; name: string }[] }>>('/org/search', {
    params: { q: searchQ.value, company_id: companyId.value },
  })
  const dept = res.data.data?.departments?.[0]
  if (dept) {
    const key = `dept-${dept.id}`
    selectedTreeKeys.value = [key]
    selectedDeptId.value = dept.id
    selectedDeptName.value = dept.name
    await loadMembers(dept.id)
  } else {
    Message.info(t('org.dept_not_found'))
  }
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
  await Promise.all([loadPrimary(), loadUserOpts(), loadHolidayRegionOpts()])
})
</script>

<style scoped>
.org-structure-page {
  display: flex;
  flex-direction: column;
  min-height: calc(100dvh - 7rem);
}

.org-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.org-tabs :deep(.arco-tabs-content) {
  flex: 1;
  min-height: 0;
}

.structure-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.toolbar-company-name {
  font-weight: 600;
  font-size: 15px;
  padding: 0.35rem 0.75rem;
  background: var(--brand-soft);
  color: var(--brand);
  border-radius: var(--radius-sm);
}

.toolbar-search {
  width: 240px;
}

.structure-body {
  display: flex;
  flex: 1;
  gap: 0;
  min-height: calc(100dvh - 12rem);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}

.structure-tree-panel {
  flex: 0 0 330px;
  max-width: 42%;
  min-width: 272px;
  border-right: 1px solid var(--border, #e5e6eb);
  display: flex;
  flex-direction: column;
  background: var(--surface-muted, #fafbfc);
}

.tree-spin {
  flex: 1;
  min-height: 0;
  padding: 12px 10px;
  overflow: auto;
}

.tree-spin :deep(.arco-tree-node-title) {
  flex: 1;
  min-width: 0;
}

.tree-node-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
  line-height: 1.5;
  max-width: 100%;
}

.tree-node-icon {
  flex-shrink: 0;
  font-size: 15px;
  color: #86909c;
}

.tree-node-label {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tree-node-name {
  font-weight: 500;
  color: #1d2129;
}

.tree-node-manager {
  margin-left: 6px;
  font-size: 12px;
  font-weight: normal;
  color: #86909c;
}

.tree-node-count {
  flex-shrink: 0;
}

.structure-main-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.panel-head {
  padding: 12px 16px;
  border-bottom: 1px solid #e5e6eb;
  background: #f7f8fa;
}

.panel-head-title {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
}

.dept-path-label {
  font-weight: 600;
  color: #1d2129;
}

.dept-member-count {
  font-size: 12px;
  font-weight: 400;
  color: #86909c;
}

.panel-body {
  flex: 1;
  overflow: auto;
  padding: 0;
}

.panel-body :deep(.arco-table) {
  border-radius: 0;
}

.company-overview {
  padding: 16px;
}

.company-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.company-fact {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  background: var(--surface-muted, #f7f8fa);
  border-radius: var(--radius-md, 8px);
  min-width: 0;
}

.company-fact--wide {
  grid-column: 1 / -1;
}

.company-fact-label {
  font-size: var(--app-font-xs, 12.5px);
  color: var(--text-tertiary, #86909c);
}

.company-fact-value {
  font-size: var(--app-font-base, 15px);
  font-weight: 500;
  color: var(--text, #1d2129);
  word-break: break-word;
}

.company-fact-value--muted {
  font-weight: 400;
  color: var(--text-secondary, #4e5969);
  line-height: 1.6;
}

.panel-empty,
.tree-empty {
  margin-top: 4rem;
}

@media (max-width: 900px) {
  .structure-body {
    flex-direction: column;
    min-height: auto;
  }
  .structure-tree-panel {
    flex: none;
    max-width: none;
    width: 100%;
    max-height: 42vh;
    border-right: none;
    border-bottom: 1px solid #e5e6eb;
  }
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
</style>
