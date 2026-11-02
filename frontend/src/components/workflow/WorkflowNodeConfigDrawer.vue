<template>
  <a-drawer
    :visible="visible"
    :width="'min(520px, 100vw)'"
    :popup-container="drawerPopupContainer"
    unmount-on-close
    :title="drawerTitle"
    :ok-text="t('common.ok')"
    :cancel-text="t('common.cancel')"
    @cancel="emit('close')"
  >
    <a-tabs
      v-if="nodeType"
      :key="`${nodeType}-${nodeId}`"
      v-model:active-key="drawerTabKey"
      class="node-config-drawer-tabs"
      :lazy-load="false"
      :destroy-on-hide="false"
    >
      <a-tab-pane
        v-if="showAssigneeTab"
        key="assignee"
        :title="assigneeTabTitle"
      >
        <a-form layout="vertical" size="small">
          <a-form-item field="title" :label="t('flowDesign.node_title')">
            <a-input v-model="localConfig.title" :placeholder="t('flowDesign.node_title_ph')" />
          </a-form-item>

          <template v-if="isTaskNode">
            <a-form-item field="apv_rel" :label="t('flowDesign.approve_mode')">
              <a-radio-group
                v-model="localConfig.apv_rel"
                type="button"
                size="small"
                :aria-label="t('flowDesign.approve_mode')"
              >
                <a-radio value="or">{{ t('flowDesign.mode_or') }}</a-radio>
                <a-radio value="and">{{ t('flowDesign.mode_and') }}</a-radio>
                <a-radio value="sequential">{{ t('flowDesign.mode_seq') }}</a-radio>
              </a-radio-group>
            </a-form-item>
          </template>

          <a-form-item field="assignee_type" :label="t('flowDesign.assignee_type')">
            <a-radio-group
              v-model="localConfig.assignee_type"
              direction="vertical"
              class="assignee-radio-group"
              :aria-label="t('flowDesign.assignee_type')"
            >
              <a-radio value="initiator_dept_manager">{{ t('flowDesign.assignee_dept_mgr') }}</a-radio>
              <a-radio value="parent_dept_manager">{{ t('flowDesign.assignee_parent_mgr') }}</a-radio>
              <a-radio value="dept_chain">{{ t('flowDesign.assignee_dept_chain') }}</a-radio>
              <a-radio value="dept_manager">{{ t('flowDesign.assignee_dept_pick') }}</a-radio>
              <a-radio value="flow_role">{{ t('flowDesign.assignee_flow_role') }}</a-radio>
              <a-radio value="fixed_users">{{ t('flowDesign.assignee_fixed') }}</a-radio>
              <a-radio value="initiator">{{ t('flowDesign.assignee_initiator') }}</a-radio>
            </a-radio-group>
          </a-form-item>

          <a-alert v-if="localConfig.assignee_type === 'initiator_dept_manager'" type="info" class="mb-2">
            {{ t('flowDesign.dept_mgr_hint') }}
          </a-alert>
          <a-alert v-if="localConfig.assignee_type === 'dept_chain'" type="info" class="mb-2">
            {{ t('flowDesign.chain_hint') }}
          </a-alert>

          <a-alert v-if="localConfig.assignee_type === 'flow_role'" type="info" class="mb-2">
            {{ t('flowDesign.flow_role_hint') }}
          </a-alert>

          <a-form-item
            v-if="localConfig.assignee_type === 'flow_role'"
            field="flow_role_code"
            :label="t('flowDesign.role_code')"
          >
            <a-select
              v-model="localConfig.flow_role_code"
              :options="flowRoleOpts"
              allow-search
              :placeholder="t('flowDesign.pick_role')"
              :aria-label="t('flowDesign.role_code')"
            />
          </a-form-item>

          <a-form-item
            v-if="localConfig.assignee_type === 'fixed_users'"
            field="user_ids"
            :label="t('flowDesign.pick_users')"
          >
            <a-select
              v-model="localConfig.user_ids"
              :options="userOpts"
              multiple
              allow-search
              :max-tag-count="3"
              :aria-label="t('flowDesign.pick_users')"
            />
          </a-form-item>

          <a-form-item
            v-if="localConfig.assignee_type === 'dept_manager'"
            field="department_id"
            :label="t('flowDesign.pick_dept')"
          >
            <a-tree-select
              v-model="localConfig.department_id"
              :data="deptTree"
              :placeholder="t('flowDesign.pick_dept')"
              allow-search
              :aria-label="t('flowDesign.pick_dept')"
              :field-names="{ key: 'id', title: 'name', children: 'children' }"
            />
          </a-form-item>
        </a-form>
      </a-tab-pane>

      <a-tab-pane v-if="nodeType === 'condition'" key="condition" :title="t('flowDesign.tab_condition')">
        <p class="hint">{{ t('flowDesign.condition_hint') }}</p>
        <!-- 空数据提示：只有默认分支时给出说明，而不是一片空白 -->
        <p v-if="!localBranches.length" class="branch-empty" role="status">{{ t('flowDesign.no_branch') }}</p>
        <div v-for="(br, bi) in localBranches" :key="bi" class="branch-card">
          <div class="branch-head">
            <span>{{ br.expr === 'default' ? t('flowDesign.default_branch') : t('flowDesign.branch_n', { n: bi + 1 }) }}</span>
            <a-button
              v-if="br.expr !== 'default'"
              size="mini"
              status="danger"
              :aria-label="`删除${t('flowDesign.branch_n', { n: bi + 1 })}`"
              @click="removeBranch(bi)"
            >
              {{ t('flowDesign.branch_delete') }}
            </a-button>
          </div>
          <a-form-item
            v-if="br.expr !== 'default'"
            :field="`branch_label_${bi}`"
            :label="t('flowDesign.branch_label')"
            class="!mb-2"
          >
            <a-input v-model="branchLabels[bi]" :placeholder="t('flowDesign.branch_label_ph')" />
          </a-form-item>
          <a-form-item
            v-if="br.expr !== 'default'"
            :field="`branch_priority_${bi}`"
            :label="t('flowDesign.branch_priority')"
            class="!mb-2"
          >
            <a-input-number v-model="branchPriorities[bi]" :min="1" :max="98" />
          </a-form-item>
          <template v-if="br.expr !== 'default'">
            <div class="branch-row">
              <a-select
                v-model="branchExprs[bi].field"
                :options="formFieldOpts"
                :placeholder="t('flowDesign.pick_field')"
                :aria-label="t('flowDesign.pick_field')"
                allow-search
                @change="onBranchFieldChange(bi)"
              />
              <a-select
                v-model="branchExprs[bi].op"
                :options="opOptsForBranch(bi)"
                :aria-label="t('flowDesign.compare_op')"
                class="branch-op"
              />
              <a-select
                v-if="fieldTypeForBranch(bi) === 'switch'"
                v-model="branchExprs[bi].value"
                :options="switchCondOpts"
                :aria-label="t('flowDesign.cond_value')"
                class="branch-value"
              />
              <a-select
                v-else-if="['select', 'radio'].includes(fieldTypeForBranch(bi) || '')"
                v-model="branchExprs[bi].value"
                :options="fieldOptionOpts(bi)"
                :loading="isFieldOptionLoading(bi)"
                allow-search
                :placeholder="t('flowDesign.cond_value')"
                :aria-label="t('flowDesign.cond_value')"
                class="branch-value"
              />
              <a-input-number
                v-else-if="isNumericBranchField(bi)"
                v-model="branchNumericValues[bi]"
                :placeholder="t('flowDesign.cond_value')"
                :aria-label="t('flowDesign.cond_value')"
                class="branch-value"
              />
              <a-input
                v-else
                v-model="branchExprs[bi].value"
                :placeholder="t('flowDesign.cond_value')"
                :aria-label="t('flowDesign.cond_value')"
              />
            </div>
            <p class="branch-preview">{{ previewExpr(bi) }}</p>
            <p v-if="fieldTypeForBranch(bi) === 'switch'" class="branch-type-hint">
              {{ t('flowDesign.switch_field_hint') }}
            </p>
          </template>
          <a-form-item
            v-if="!visualMode"
            field="goto_node"
            :label="t('flowDesign.goto_node')"
            class="!mb-0 mt-2"
          >
            <a-select
              v-model="br.target"
              :options="targetOpts"
              allow-search
              :aria-label="t('flowDesign.goto_node')"
            />
          </a-form-item>
          <p v-else-if="br.expr !== 'default'" class="visual-hint">{{ t('flowDesign.branch_path_visual') }}</p>
        </div>
        <a-button long class="mt-2" @click="addBranch">{{ t('flowDesign.add_branch') }}</a-button>
      </a-tab-pane>

      <a-tab-pane
        v-if="isTaskNode"
        key="permissions"
        :title="t('flowDesign.tab_permissions')"
      >
        <p class="hint">{{ t('flowDesign.perm_hint') }}</p>
        <!-- 空数据提示：没有表单字段时给出说明，而不是只渲染一张空表头 -->
        <p v-if="!permRows.length" class="branch-empty" role="status">{{ t('flowDesign.no_perm_fields') }}</p>
        <a-table
          v-else
          :data="permRows"
          :pagination="false"
          size="small"
          row-key="key"
          :scroll="{ y: 360 }"
          :data-caption="t('flowDesign.perm_hint')"
        >
          <template #columns>
            <a-table-column :title="t('flowDesign.perm_field')" data-index="label" :width="148">
              <template #cell="{ record }">
                <span :style="{ paddingLeft: `${record.indent * 16}px` }">{{ record.label }}</span>
              </template>
            </a-table-column>
            <a-table-column :title="t('flowDesign.perm_mode')" :width="200">
              <template #cell="{ record }">
                <a-radio-group
                  :model-value="localConfig.field_permissions![record.key]"
                  type="button"
                  size="mini"
                  :aria-label="t('flowDesign.perm_aria', { label: record.label })"
                  @change="(v: string | number | boolean) => onPermChange(record.key, String(v) as FieldPermMode)"
                >
                  <a-radio value="hidden">{{ t('flowDesign.perm_hidden') }}</a-radio>
                  <a-radio value="read">{{ t('flowDesign.perm_read') }}</a-radio>
                  <a-radio value="edit">{{ t('flowDesign.perm_edit') }}</a-radio>
                </a-radio-group>
              </template>
            </a-table-column>
            <a-table-column :title="t('flowDesign.perm_node_required')" :width="88" align="center">
              <template #cell="{ record }">
                <a-checkbox
                  :model-value="!!localConfig.field_node_required?.[record.key]"
                  :disabled="localConfig.field_permissions![record.key] !== 'edit'"
                  :aria-label="`${record.label}：${t('flowDesign.perm_node_required')}`"
                  @change="(checked: boolean) => setNodeRequired(record.key, checked)"
                />
              </template>
            </a-table-column>
            <a-table-column :title="t('flowDesign.perm_must_modify')" :width="88" align="center">
              <template #cell="{ record }">
                <a-checkbox
                  :model-value="!!localConfig.field_must_modify?.[record.key]"
                  :disabled="localConfig.field_permissions![record.key] !== 'edit'"
                  :aria-label="`${record.label}：${t('flowDesign.perm_must_modify')}`"
                  @change="(checked: boolean) => setMustModify(record.key, checked)"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
        <a-space class="mt-2">
          <a-button size="mini" @click="setAllPerm('read')">{{ t('flowDesign.perm_all_read') }}</a-button>
          <a-button size="mini" @click="setAllPerm('edit')">{{ t('flowDesign.perm_all_edit') }}</a-button>
        </a-space>
      </a-tab-pane>

      <a-tab-pane
        v-if="isTaskNode"
        key="send_email"
        :title="t('flowDesign.tab_send_email')"
      >
        <p class="hint">{{ t('flowDesign.send_email_hint') }}</p>
        <div class="node-drawer-form">
          <div class="node-drawer-field node-drawer-field--switch">
            <div class="node-drawer-label">{{ t('flowDesign.send_email_enable') }}</div>
            <a-switch
              size="small"
              :model-value="!!localSendEmail.enabled"
              :aria-label="t('flowDesign.send_email_enable')"
              @update:model-value="setSendEmailEnabled"
            />
          </div>
          <div v-show="localSendEmail.enabled" class="node-drawer-fields">
            <div class="node-drawer-field">
              <div class="node-drawer-label">{{ t('flowDesign.send_email_trigger') }}</div>
              <a-radio-group
                v-model="localSendEmail.trigger"
                type="button"
                size="small"
                :aria-label="t('flowDesign.send_email_trigger')"
              >
                <a-radio value="on_enter">{{ t('flowDesign.send_email_trigger_enter') }}</a-radio>
                <a-radio value="on_complete">{{ t('flowDesign.send_email_trigger_complete') }}</a-radio>
              </a-radio-group>
              <p class="hint mt-1 mb-0">
                {{
                  localSendEmail.trigger === 'on_complete'
                    ? t('flowDesign.send_email_trigger_complete_hint')
                    : t('flowDesign.send_email_trigger_enter_hint')
                }}
              </p>
            </div>
            <div class="node-drawer-field">
              <div class="node-drawer-label">{{ t('flowDesign.send_email_recipient_type') }}</div>
              <a-radio-group
                v-model="localSendEmail.recipient_type"
                direction="vertical"
                :aria-label="t('flowDesign.send_email_recipient_type')"
              >
                <a-radio value="org_user">{{ t('flowDesign.send_email_org_user') }}</a-radio>
                <a-radio value="form_field">{{ t('flowDesign.send_email_form_field') }}</a-radio>
              </a-radio-group>
            </div>
            <div
              v-if="localSendEmail.recipient_type === 'org_user'"
              class="node-drawer-field"
            >
              <div class="node-drawer-label">{{ t('flowDesign.send_email_pick_users') }}</div>
              <a-select
                v-model="localSendEmail.user_ids"
                :options="userOpts"
                multiple
                allow-search
                :max-tag-count="3"
                :placeholder="t('flowDesign.send_email_pick_users_ph')"
                :aria-label="t('flowDesign.send_email_pick_users')"
              />
            </div>
            <div v-else class="node-drawer-field">
              <div class="node-drawer-label">{{ t('flowDesign.send_email_pick_field') }}</div>
              <a-select
                v-model="localSendEmail.field_key"
                :options="emailFieldOpts"
                allow-search
                :placeholder="t('flowDesign.send_email_pick_field_ph')"
                :aria-label="t('flowDesign.send_email_pick_field')"
              />
              <p v-if="!emailFieldOpts.length" class="hint mt-1">{{ t('flowDesign.send_email_no_field') }}</p>
            </div>
            <a-divider margin="12px" />
            <p class="hint">{{ t('flowDesign.send_email_template_hint') }}</p>
            <div class="node-drawer-field">
              <div class="node-drawer-label">{{ t('flowDesign.send_email_subject') }}</div>
              <a-input
                v-model="localSendEmail.subject"
                :placeholder="t('flowDesign.send_email_subject_ph')"
                :aria-label="t('flowDesign.send_email_subject')"
              />
            </div>
            <div class="node-drawer-field">
              <div class="node-drawer-label">{{ t('flowDesign.send_email_body') }}</div>
              <a-textarea
                v-model="localSendEmail.body"
                :auto-size="{ minRows: 5, maxRows: 12 }"
                :placeholder="t('flowDesign.send_email_body_ph')"
                :aria-label="t('flowDesign.send_email_body')"
              />
            </div>
            <p v-if="isZhLocale" class="hint hint-vars" v-pre>可用占位符：{{flow_name}}、{{display_no}}、{{initiator_name}}、{{node_name}}、{{recipient_name}}、{{detail_url}}、{{form_summary}}</p>
            <p v-else class="hint hint-vars" v-pre>Placeholders: {{flow_name}}, {{display_no}}, {{initiator_name}}, {{node_name}}, {{recipient_name}}, {{detail_url}}, {{form_summary}}</p>
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane
        v-if="nodeType === 'handler'"
        key="notify_applicant"
        :title="t('flowDesign.tab_notify_applicant')"
      >
        <p class="hint">{{ t('flowDesign.notify_applicant_hint') }}</p>
        <div class="node-drawer-form">
          <div class="node-drawer-field node-drawer-field--switch">
            <div class="node-drawer-label">{{ t('flowDesign.notify_applicant_enable') }}</div>
            <a-switch
              size="small"
              :model-value="!!localNotifyApplicant.enabled"
              :aria-label="t('flowDesign.notify_applicant_enable')"
              @update:model-value="setNotifyApplicantEnabled"
            />
          </div>
          <div v-show="localNotifyApplicant.enabled" class="node-drawer-fields">
            <div class="node-drawer-field">
              <div class="node-drawer-label">{{ t('flowDesign.notify_applicant_subject') }}</div>
              <a-input
                v-model="localNotifyApplicant.subject"
                :placeholder="t('flowDesign.notify_applicant_subject_ph')"
                :aria-label="t('flowDesign.notify_applicant_subject')"
              />
            </div>
            <div class="node-drawer-field">
              <div class="node-drawer-label">{{ t('flowDesign.notify_applicant_body') }}</div>
              <a-textarea
                v-model="localNotifyApplicant.body"
                :auto-size="{ minRows: 6, maxRows: 12 }"
                :placeholder="t('flowDesign.notify_applicant_body_ph')"
                :aria-label="t('flowDesign.notify_applicant_body')"
              />
            </div>
            <p v-if="isZhLocale" class="hint hint-vars" v-pre>可用占位符：{{flow_name}}、{{display_no}}、{{initiator_name}}、{{detail_url}}、{{handler_node_name}}</p>
            <p v-else class="hint hint-vars" v-pre>Placeholders: {{flow_name}}, {{display_no}}, {{initiator_name}}, {{detail_url}}, {{handler_node_name}}</p>
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane v-if="nodeType === 'start'" key="start" :title="t('flowDesign.tab_start')">
        <a-alert type="info">{{ t('flowDesign.start_hint') }}</a-alert>
        <a-form-item field="title" class="mt-3" :label="t('flowDesign.node_title')">
          <a-input v-model="localConfig.title" />
        </a-form-item>
      </a-tab-pane>
    </a-tabs>
    <template #footer>
      <div class="drawer-footer">
        <a-popconfirm
          v-if="canDeleteNode"
          :content="t('flowDesign.delete_node_confirm')"
          @ok="emit('delete')"
        >
          <a-button status="danger">{{ t('flowDesign.delete_node') }}</a-button>
        </a-popconfirm>
        <a-space>
          <a-button @click="emit('close')">{{ t('common.cancel') }}</a-button>
          <a-button type="primary" :loading="saving" :disabled="saving" @click="onConfirm">
            {{ t('common.ok') }}
          </a-button>
        </a-space>
      </div>
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@arco-design/web-vue'
import { api, type ApiResponse } from '@/api/client'
import {
  fieldOptionsToSelectOpts,
  resolveFieldOptions,
  resolveOptionLabel,
  type FieldOptionItem,
} from '@/composables/useFieldOptions'
import {
  CONDITION_OPS,
  defaultNodeConfig,
  type ConditionBranch,
  type FieldPermMode,
  type NodeNotifyApplicantConfig,
  type NodeSendEmailConfig,
  type NodeSendEmailTrigger,
  type WorkflowNodeConfig,
} from '@/composables/useWorkflowAssignee'
import { flattenFormFieldsForPermissions } from '@/utils/formFieldTree'
import type { FormSchema } from '@/types/form'
import {
  SWITCH_CONDITION_OPTS,
  coerceConditionStoredValue,
  defaultOpForFieldType,
  fieldKeyFromConditionPath,
  fieldTypeForConditionPath,
  findFormFieldDef,
  formatConditionValueLabel,
  isNumericConditionField,
  opsForFieldType,
  parseConditionEditorValue,
  staticFieldOptionItems,
} from '@/utils/conditionFieldMeta'

const props = withDefaults(
  defineProps<{
    visible: boolean
    nodeType: string
    nodeId: string
    config: WorkflowNodeConfig
    branches?: ConditionBranch[]
    formSchema?: FormSchema
    targetNodeIds: string[]
    /** 节点 id → 可读标题，供「跳转目标」下拉展示 */
    targetNodeLabels?: Record<string, string>
    /** 垂直流程模式：分支路径由画布维护，不手动选跳转节点 */
    visualMode?: boolean
    /** 全屏时将抽屉挂载到该容器内，避免被全屏层遮挡 */
    embedContainer?: HTMLElement | null
  }>(),
  {},
)

const drawerPopupContainer = computed(() => props.embedContainer || 'body')

const emit = defineEmits<{
  close: []
  save: [payload: { config: WorkflowNodeConfig; branches?: ConditionBranch[] }]
  delete: []
}>()

const { t, locale } = useI18n()

const isZhLocale = computed(() => String(locale.value).startsWith('zh'))

const localConfig = reactive<WorkflowNodeConfig>({})
const localSendEmail = reactive<NodeSendEmailConfig>({
  enabled: false,
  trigger: 'on_enter',
  recipient_type: 'org_user',
  user_ids: [],
  field_key: undefined,
  subject: '',
  body: '',
})
const localNotifyApplicant = reactive<NodeNotifyApplicantConfig>({
  enabled: false,
  subject: '',
  body: '',
})
const localBranches = ref<ConditionBranch[]>([])
/** 保存中（防止重复提交） */
const saving = ref(false)
const branchExprs = ref<{ field: string; op: string; value: string }[]>([])
const branchNumericValues = ref<(number | undefined)[]>([])
const branchLabels = ref<string[]>([])
const branchPriorities = ref<number[]>([])
const fieldOptionCache = ref<Record<string, { label: string; value: string }[]>>({})
const fieldOptionItemsCache = ref<Record<string, FieldOptionItem[]>>({})
const fieldOptionLoadingKeys = ref<Set<string>>(new Set())
const fieldOptionLoadedKeys = ref<Set<string>>(new Set())
const drawerTabKey = ref('assignee')

const flowRoleOpts = ref<{ label: string; value: string }[]>([])
const userOpts = ref<{ label: string; value: number }[]>([])
const deptTree = ref<Record<string, unknown>[]>([])

const isTaskNode = computed(() => props.nodeType === 'approver' || props.nodeType === 'handler')
const canDeleteNode = computed(
  () => props.nodeType !== 'start' && props.nodeType !== 'end',
)
const showAssigneeTab = computed(
  () => isTaskNode.value || props.nodeType === 'cc',
)
const assigneeTabTitle = computed(() =>
  props.nodeType === 'cc' ? t('flowDesign.tab_cc') : t('flowDesign.tab_assignee'),
)

const defaultTabKey = computed(() => {
  if (props.nodeType === 'condition') return 'condition'
  if (props.nodeType === 'start') return 'start'
  return 'assignee'
})

const drawerTitle = computed(() => {
  const titles: Record<string, string> = {
    approver: t('flowDesign.drawer_approver'),
    handler: t('flowDesign.drawer_handler'),
    cc: t('flowDesign.drawer_cc'),
    condition: t('flowDesign.drawer_condition'),
    start: t('flowDesign.drawer_start'),
    end: t('flowDesign.drawer_end'),
  }
  return titles[props.nodeType] || t('flowDesign.node_props')
})

const permRows = computed(() => flattenFormFieldsForPermissions(props.formSchema))

const formFieldOpts = computed(() =>
  permRows.value.map((r) => ({ label: r.label, value: `form.${r.key}` })),
)

const emailFieldOpts = computed(() =>
  permRows.value
    .filter((r) => r.type === 'email' && !r.parentKey)
    .map((r) => ({ label: r.label, value: r.key })),
)

const targetOpts = computed(() =>
  props.targetNodeIds
    .filter((id) => id !== props.nodeId)
    // 展示节点的可读标题，而不是内部 node id
    .map((id) => ({ label: props.targetNodeLabels?.[id] || id, value: id })),
)

const opOpts = computed(() =>
  CONDITION_OPS.map((o) => ({ label: t(o.labelKey), value: o.value })),
)

const switchCondOpts = SWITCH_CONDITION_OPTS.map((o) => ({ ...o }))

function fieldTypeForBranch(bi: number): string | undefined {
  const field = branchExprs.value[bi]?.field
  if (!field) return undefined
  return fieldTypeForConditionPath(field, permRows.value)
}

function isNumericBranchField(bi: number): boolean {
  return isNumericConditionField(fieldTypeForBranch(bi))
}

function opOptsForBranch(bi: number) {
  const allowed = new Set(opsForFieldType(fieldTypeForBranch(bi)))
  return opOpts.value.filter((o) => allowed.has(o.value))
}

function fieldOptionOpts(bi: number) {
  const field = branchExprs.value[bi]?.field
  if (!field) return []
  return fieldOptionCache.value[field] || []
}

function isFieldOptionLoading(bi: number): boolean {
  const field = branchExprs.value[bi]?.field
  if (!field) return false
  return fieldOptionLoadingKeys.value.has(field)
}

async function ensureFieldOptions(fieldPath: string, force = false) {
  const path = (fieldPath || '').trim()
  if (!path || path === 'form.') return
  if (!force && fieldOptionLoadedKeys.value.has(path)) return
  const key = fieldKeyFromConditionPath(path)
  const def = findFormFieldDef(props.formSchema, key)
  if (!def) {
    fieldOptionCache.value[path] = []
    fieldOptionItemsCache.value[path] = []
    fieldOptionLoadedKeys.value = new Set(fieldOptionLoadedKeys.value).add(path)
    return
  }
  fieldOptionLoadingKeys.value = new Set(fieldOptionLoadingKeys.value).add(path)
  try {
    const items = await resolveFieldOptions(def)
    fieldOptionItemsCache.value[path] = items
    const opts = fieldOptionsToSelectOpts(items)
    fieldOptionCache.value[path] = opts.length ? opts : staticFieldOptionItems(def)
    fieldOptionLoadedKeys.value = new Set(fieldOptionLoadedKeys.value).add(path)
  } finally {
    const next = new Set(fieldOptionLoadingKeys.value)
    next.delete(path)
    fieldOptionLoadingKeys.value = next
  }
}

async function preloadBranchFieldOptions() {
  const paths = new Set(
    branchExprs.value
      .map((ex) => ex.field)
      .filter((p) => p && p !== 'form.'),
  )
  await Promise.all([...paths].map((p) => ensureFieldOptions(p)))
}

function invalidateFieldOptionCache() {
  fieldOptionCache.value = {}
  fieldOptionItemsCache.value = {}
  fieldOptionLoadingKeys.value = new Set()
  fieldOptionLoadedKeys.value = new Set()
}

function onBranchFieldChange(bi: number) {
  const type = fieldTypeForBranch(bi)
  const ex = branchExprs.value[bi]
  if (!ex) return
  ex.op = defaultOpForFieldType(type)
  if (type === 'switch') {
    ex.value = 'true'
    branchNumericValues.value[bi] = undefined
    return
  }
  if (isNumericConditionField(type)) {
    ex.value = ''
    branchNumericValues.value[bi] = undefined
    return
  }
  void ensureFieldOptions(ex.field, true).then(() => {
    const opts = fieldOptionOpts(bi)
    ex.value = opts[0]?.value || ''
  })
  branchNumericValues.value[bi] = undefined
}

function ensurePerms() {
  if (!localConfig.field_permissions) localConfig.field_permissions = {}
  if (!localConfig.field_node_required) localConfig.field_node_required = {}
  if (!localConfig.field_must_modify) localConfig.field_must_modify = {}
  for (const row of permRows.value) {
    if (!localConfig.field_permissions[row.key]) {
      localConfig.field_permissions[row.key] = 'read'
    }
  }
}

function onPermChange(key: string, mode: FieldPermMode) {
  if (!localConfig.field_permissions) localConfig.field_permissions = {}
  localConfig.field_permissions[key] = mode
  if (mode !== 'edit') {
    if (localConfig.field_node_required) delete localConfig.field_node_required[key]
    if (localConfig.field_must_modify) delete localConfig.field_must_modify[key]
  }
}

function setNodeRequired(key: string, checked: boolean) {
  if (!localConfig.field_node_required) localConfig.field_node_required = {}
  if (checked) localConfig.field_node_required[key] = true
  else delete localConfig.field_node_required[key]
}

function setMustModify(key: string, checked: boolean) {
  if (!localConfig.field_must_modify) localConfig.field_must_modify = {}
  if (checked) localConfig.field_must_modify[key] = true
  else delete localConfig.field_must_modify[key]
}

function syncSendEmailFromConfig() {
  const src = props.config?.send_email || {}
  localSendEmail.enabled = !!src.enabled
  localSendEmail.trigger = (src.trigger as NodeSendEmailTrigger) || 'on_enter'
  localSendEmail.recipient_type = src.recipient_type || 'org_user'
  localSendEmail.user_ids = [...(src.user_ids || [])]
  localSendEmail.field_key = src.field_key
  localSendEmail.subject = src.subject || ''
  localSendEmail.body = src.body || ''
}

function setSendEmailEnabled(v: boolean | string | number) {
  localSendEmail.enabled = !!v
}

function applySendEmailToConfig() {
  if (!localSendEmail.enabled) {
    delete localConfig.send_email
  } else {
    localConfig.send_email = {
      enabled: true,
      trigger: localSendEmail.trigger || 'on_enter',
      recipient_type: localSendEmail.recipient_type || 'org_user',
      user_ids:
        localSendEmail.recipient_type === 'org_user'
          ? [...(localSendEmail.user_ids || [])]
          : undefined,
      field_key:
        localSendEmail.recipient_type === 'form_field'
          ? localSendEmail.field_key
          : undefined,
      subject: (localSendEmail.subject || '').trim() || undefined,
      body: (localSendEmail.body || '').trim() || undefined,
    }
  }
}

function syncNotifyApplicantFromConfig() {
  const src = props.config?.notify_applicant_on_enter || {}
  localNotifyApplicant.enabled = !!src.enabled
  localNotifyApplicant.subject = src.subject || ''
  localNotifyApplicant.body = src.body || ''
}

function setNotifyApplicantEnabled(v: boolean | string | number) {
  localNotifyApplicant.enabled = !!v
}

function applyNotifyApplicantToConfig() {
  if (props.nodeType !== 'handler') {
    delete localConfig.notify_applicant_on_enter
    return
  }
  if (!localNotifyApplicant.enabled) {
    delete localConfig.notify_applicant_on_enter
    return
  }
  localConfig.notify_applicant_on_enter = {
    enabled: true,
    subject: (localNotifyApplicant.subject || '').trim() || undefined,
    body: (localNotifyApplicant.body || '').trim() || undefined,
  }
}

function syncFromProps() {
  const base = defaultNodeConfig(props.nodeType)
  Object.keys(localConfig).forEach((key) => {
    delete (localConfig as Record<string, unknown>)[key]
  })
  Object.assign(localConfig, base, JSON.parse(JSON.stringify(props.config || {})))
  syncSendEmailFromConfig()
  syncNotifyApplicantFromConfig()
  if (isTaskNode.value) ensurePerms()

  if (props.nodeType === 'condition') {
    localBranches.value = JSON.parse(JSON.stringify(props.branches?.length ? props.branches : [
      { expr: { field: 'form.days', op: 'gt', value: 0 }, target: '' },
      { expr: 'default', target: '' },
    ]))
    branchExprs.value = localBranches.value.map((br) => {
      if (br.expr === 'default' || typeof br.expr === 'string') {
        return { field: 'form.', op: 'eq', value: '' }
      }
      const ex = br.expr as { field?: string; op?: string; value?: unknown }
      const field = ex.field || 'form.'
      const type = fieldTypeForConditionPath(field, permRows.value)
      return {
        field,
        op: ex.op || defaultOpForFieldType(type),
        value: parseConditionEditorValue(type, ex.value),
      }
    })
    branchNumericValues.value = localBranches.value.map((br, bi) => {
      if (br.expr === 'default' || typeof br.expr === 'string') return undefined
      const ex = br.expr as { value?: unknown }
      const type = fieldTypeForBranch(bi)
      if (!isNumericConditionField(type)) return undefined
      const num = Number(ex.value)
      return Number.isNaN(num) ? undefined : num
    })
    branchLabels.value = localBranches.value.map((br) => br.label || '')
    branchPriorities.value = localBranches.value.map((br, i) =>
      br.expr === 'default' ? 99 : br.priority ?? i + 1,
    )
    invalidateFieldOptionCache()
    void preloadBranchFieldOptions()
  }
}

function previewExpr(bi: number) {
  const ex = branchExprs.value[bi]
  if (!ex) return ''
  const fieldOpt = formFieldOpts.value.find((o) => o.value === ex.field)
  const opOpt = opOptsForBranch(bi).find((o) => o.value === ex.op)
  const type = fieldTypeForBranch(bi)
  const rawValue = isNumericBranchField(bi) ? branchNumericValues.value[bi] : ex.value
  const fieldPath = ex.field
  const items = fieldOptionItemsCache.value[fieldPath]
  const valueLabel =
    items?.length && ['select', 'radio', 'multi_select', 'checkbox_group'].includes(type || '')
      ? resolveOptionLabel(rawValue, items)
      : formatConditionValueLabel(type, rawValue)
  return `${fieldOpt?.label || ex.field} ${opOpt?.label || ex.op} ${valueLabel}`
}

function addBranch() {
  const pri = localBranches.value.filter((b) => b.expr !== 'default').length + 1
  const firstField = formFieldOpts.value[0]?.value || 'form.'
  const firstType = fieldTypeForConditionPath(firstField, permRows.value)
  const defaultOp = defaultOpForFieldType(firstType)
  const defaultValue =
    firstType === 'switch'
      ? 'true'
      : staticFieldOptionItems(findFormFieldDef(props.formSchema, fieldKeyFromConditionPath(firstField)))[0]
          ?.value || ''
  // 插入位置必须在改动数组长度之前算好，否则后续 splice 会用到已变更的长度
  const insertAt = localBranches.value.length - 1
  localBranches.value.splice(insertAt, 0, {
    expr: { field: firstField, op: defaultOp, value: defaultValue },
    target: '',
    label: t('flowDesign.branch_label_new', { n: pri }),
    priority: pri,
  })
  branchExprs.value.splice(insertAt, 0, {
    field: firstField,
    op: defaultOp,
    value: defaultValue,
  })
  branchNumericValues.value.splice(insertAt, 0, undefined)
  branchLabels.value.splice(insertAt, 0, t('flowDesign.branch_label_new', { n: pri }))
  branchPriorities.value.splice(insertAt, 0, pri)
  const newBi = insertAt
  if (newBi >= 0 && ['select', 'radio'].includes(firstType || '')) {
    void ensureFieldOptions(firstField, true).then(() => {
      const opts = fieldOptionOpts(newBi)
      if (opts.length) branchExprs.value[newBi].value = opts[0].value
    })
  }
}

function removeBranch(bi: number) {
  localBranches.value.splice(bi, 1)
  branchExprs.value.splice(bi, 1)
  branchNumericValues.value.splice(bi, 1)
  branchLabels.value.splice(bi, 1)
  branchPriorities.value.splice(bi, 1)
}

function buildBranches(): ConditionBranch[] {
  return localBranches.value.map((br, bi) => {
    if (br.expr === 'default') {
      return {
        expr: 'default',
        target: br.target,
        label: branchLabels.value[bi] || t('flowDesign.default_condition'),
        priority: 99,
      }
    }
    const ex = branchExprs.value[bi]
    const type = fieldTypeForBranch(bi)
    const rawValue = isNumericBranchField(bi) ? branchNumericValues.value[bi] : ex.value
    const value = coerceConditionStoredValue(type, rawValue)
    return {
      expr: { field: ex.field, op: ex.op, value },
      target: br.target,
      label: branchLabels.value[bi] || '',
      priority: branchPriorities.value[bi] ?? bi + 1,
    }
  })
}

function setAllPerm(mode: FieldPermMode) {
  ensurePerms()
  for (const row of permRows.value) {
    localConfig.field_permissions![row.key] = mode
    if (mode !== 'edit') {
      delete localConfig.field_node_required![row.key]
      delete localConfig.field_must_modify![row.key]
    }
  }
}

function onConfirm() {
  // 防止重复提交
  if (saving.value) return
  saving.value = true
  applySendEmailToConfig()
  applyNotifyApplicantToConfig()
  const payload: { config: WorkflowNodeConfig; branches?: ConditionBranch[] } = {
    config: JSON.parse(JSON.stringify(localConfig)),
  }
  if (props.nodeType === 'condition') {
    payload.branches = buildBranches()
  }
  emit('save', payload)
  emit('close')
}

// 抽屉关闭后复位保存状态，允许再次打开时保存
watch(
  () => props.visible,
  (v) => {
    if (!v) saving.value = false
  },
)

async function loadOptions() {
  // 选项加载失败时不能抛出未捕获异常：下拉会退化为空，但要有明确提示
  const [roles, users] = await Promise.allSettled([
    api.get<ApiResponse<{ code: string; name: string }[]>>('/admin/flow-roles'),
    api.get<ApiResponse<{ id: number; display_name: string; username: string }[]>>('/workflow/users/options'),
  ])
  if (roles.status === 'fulfilled' && roles.value.data.ok) {
    flowRoleOpts.value = roles.value.data.data.map((r) => ({
      label: `${r.name}（${r.code}）`,
      value: r.code,
    }))
  } else {
    Message.warning(t('flowDesign.role_load_failed'))
  }
  if (users.status === 'fulfilled' && users.value.data.ok) {
    userOpts.value = users.value.data.data.map((u) => ({
      label: u.display_name || u.username,
      value: u.id,
    }))
  } else {
    Message.warning(t('flowDesign.user_load_failed'))
  }
  try {
    const primary = await api.get<ApiResponse<{ id: number }>>('/org/primary')
    if (primary.data.ok?.id) {
      const st = await api.get<ApiResponse<{ departments: Record<string, unknown>[] }>>(
        `/org/companies/${primary.data.data.id}/structure`,
      )
      if (st.data.ok) deptTree.value = (st.data.data.tree as Record<string, unknown>[]) || []
    }
  } catch {
    Message.warning(t('flowDesign.dept_load_failed'))
  }
}

watch(
  () => localConfig.assignee_type,
  (type) => {
    if (type === 'flow_role' && isTaskNode.value && !localConfig.apv_rel) {
      localConfig.apv_rel = 'or'
    }
  },
)

watch(
  () => props.visible,
  (v) => {
    if (v) {
      drawerTabKey.value = defaultTabKey.value
      syncFromProps()
      loadOptions()
    }
  },
)

watch(
  () => props.nodeId,
  () => {
    if (props.visible) {
      drawerTabKey.value = defaultTabKey.value
      syncFromProps()
    }
  },
)

watch(
  () => props.formSchema,
  () => {
    if (props.visible && props.nodeType === 'condition') {
      invalidateFieldOptionCache()
      void preloadBranchFieldOptions()
    }
  },
  { deep: true },
)
</script>

<style scoped>
.hint {
  font-size: var(--app-font-xs);
  color: var(--text-tertiary);
  margin: 0 0 var(--app-space-md);
  line-height: 1.5;
}

.assignee-radio-group :deep(.arco-radio) {
  margin-bottom: var(--app-space-6);
}

.branch-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--app-space-10);
  margin-bottom: var(--app-space-10);
  background: var(--surface-muted);
}

.branch-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: var(--app-font-xs);
  margin-bottom: var(--app-space-sm);
}

.branch-row {
  display: grid;
  /* 固定 108px / 140px 在窄屏放不下，统一用 minmax(0,1fr) 自适应 */
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 108px) minmax(0, 1fr);
  gap: var(--app-space-8);
}

/* 窄屏：条件行改为单列堆叠，避免横向溢出 */
@media (max-width: 640px) {
  .branch-row {
    grid-template-columns: minmax(0, 1fr);
  }
}

/* 空数据提示 */
.branch-empty {
  margin: 0 0 var(--app-space-10);
  padding: var(--app-space-14) var(--app-space-10);
  border: 1px dashed var(--border);
  border-radius: var(--radius-md);
  color: var(--text-tertiary);
  font-size: var(--app-font-xs);
  text-align: center;
}

/* 条件行内的下拉填满所在栅格列 */
.branch-op,
.branch-value {
  width: 100%;
  min-width: 0;
}

.branch-preview {
  margin: var(--app-space-6) 0 0;
  font-size: var(--app-font-xs);
  color: var(--brand-text);
}

.branch-type-hint {
  margin: var(--app-space-xs) 0 0;
  font-size: var(--app-font-xs);
  color: var(--text-tertiary);
  line-height: 1.45;
}

.visual-hint {
  margin: var(--app-space-sm) 0 0;
  font-size: var(--app-font-xs);
  color: var(--text-tertiary);
}

.drawer-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

/* 独立于 Form Studio 顶层 Tab 样式，保证「发送邮件 / 通知申请人」等内容可见 */
.node-config-drawer-tabs :deep(.arco-tabs-content) {
  overflow: visible;
}

.node-config-drawer-tabs :deep(.arco-tabs-content-list) {
  height: auto !important;
}

.node-config-drawer-tabs :deep(.arco-tabs-content-item.arco-tabs-content-item-active) {
  height: auto !important;
  overflow: visible;
}

.node-config-drawer-tabs :deep(.arco-tabs-pane) {
  height: auto !important;
  overflow: visible;
  padding-top: var(--app-space-4);
}

.node-drawer-form {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-12);
}

.node-drawer-fields {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-12);
}

.node-drawer-field {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-6);
}

.node-drawer-field--switch {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: var(--app-space-12);
}

.node-drawer-field--switch .node-drawer-label {
  flex: 1;
  min-width: 0;
  margin: 0;
}

.node-drawer-field--switch :deep(.arco-switch) {
  flex-shrink: 0;
  align-self: center;
  width: auto;
}

.node-drawer-label {
  font-size: var(--app-font-sm);
  color: var(--text-secondary);
  line-height: 1.4;
}

.hint-vars {
  font-family: ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace;
  word-break: break-all;
}
</style>
