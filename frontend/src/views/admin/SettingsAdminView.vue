<template>
  <PageChrome
    :title="pageTitle"
    :description="pageDescription"
  >
    <a-tabs v-model:active-key="tab" type="rounded" class="settings-tabs settings-tabs--nav-hidden" @change="onTabChange">
      <a-tab-pane key="brand" :title="t('settings.tab_brand')">
        <a-card class="settings-card max-w-2xl" :bordered="false">
          <a-form layout="vertical" :model="form">
            <a-form-item :label="t('settings.company_name_label')">
              <a-input v-model="form.COMPANY_NAME" :placeholder="t('settings.company_name_ph')" />
            </a-form-item>

            <a-form-item :label="t('settings.org_logo')">
              <div class="logo-manager">
                <div class="logo-preview-wrap">
                  <BrandLogo
                    size="lg"
                    :image-url="logoPreviewUrl"
                    :fallback="form.COMPANY_NAME || 'T'"
                  />
                  <div class="logo-preview-meta">
                    <p class="logo-hint-title">{{ t('settings.logo_where_title') }}</p>
                    <p class="logo-hint-text">{{ t('settings.logo_where_text') }}</p>
                  </div>
                </div>
                <p class="logo-ratio-hint">{{ t('settings.logo_ratio_hint') }}</p>
                <a-space wrap>
                  <input
                    ref="logoFileInput"
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    class="hidden"
                    @change="onLogoFile"
                  />
                  <a-button type="primary" :loading="logoUploading" @click="pickLogo">
                    {{ t('settings.upload_logo') }}
                  </a-button>
                  <a-button
                    v-if="logoPreviewUrl || form.company_logo_url"
                    :loading="logoRemoving"
                    @click="removeLogo"
                  >
                    {{ t('settings.remove_logo') }}
                  </a-button>
                </a-space>
              </div>
            </a-form-item>

            <a-form-item :label="t('settings.holiday_region')">
              <a-select
                v-model="holidayRegion"
                :options="holidayRegionOpts"
                style="max-width: 280px"
              />
              <template #extra>{{ t('settings.holiday_region_hint') }}</template>
            </a-form-item>

            <a-button type="primary" :loading="saving" @click="save">{{ t('settings.save_company_name') }}</a-button>
          </a-form>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="sectors" :title="t('settings.tab_sectors')">
        <a-card class="rounded-xl">
          <div class="flex justify-between mb-3">
            <span class="text-sm text-gray-500">{{ t('settings.sectors_hint') }}</span>
            <a-button type="primary" @click="openSector()">{{ t('settings.add_sector') }}</a-button>
          </div>
          <a-table :data="sectors" row-key="id" :pagination="false">
            <template #columns>
              <a-table-column :title="t('settings.col_code')" data-index="code" />
              <a-table-column :title="t('settings.col_name')" data-index="name" />
              <a-table-column :title="t('settings.col_sort')" data-index="sort_order" :width="80" />
              <a-table-column :title="t('settings.col_actions')" :width="160">
                <template #cell="{ record }">
                  <a-space>
                    <a-button size="mini" @click="openSector(record)">{{ t('settings.action_edit') }}</a-button>
                    <a-popconfirm :content="t('settings.sector_disable_confirm')" @ok="removeSector(record.id)">
                      <a-button size="mini" status="danger">{{ t('settings.action_disable') }}</a-button>
                    </a-popconfirm>
                  </a-space>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="admins" :title="t('settings.tab_admins')">
        <a-row :gutter="16">
          <a-col :xs="24" :lg="12">
            <a-card :title="t('settings.global_admins')" class="rounded-xl mb-4">
              <p class="text-sm text-gray-500 mb-3">{{ t('settings.global_admins_hint') }}</p>
              <a-select
                v-model="globalAdminIds"
                :options="userOpts"
                multiple
                allow-search
                :placeholder="t('settings.pick_user')"
                class="w-full"
              />
              <a-button type="primary" class="mt-3" :loading="savingAdmins" @click="saveGlobalAdmins">
                {{ t('settings.save_global_admins') }}
              </a-button>
            </a-card>
          </a-col>
          <a-col :xs="24" :lg="12">
            <a-card :title="t('settings.scoped_admins')" class="rounded-xl mb-4">
              <a-button type="primary" class="mb-3" @click="openScoped()">{{ t('settings.add_scoped_admin') }}</a-button>
              <a-table :data="scopedAdmins" row-key="user_id" :pagination="false" size="small">
                <template #columns>
                  <a-table-column :title="t('settings.col_user')">
                    <template #cell="{ record }">{{ record.display_name }} ({{ record.username }})</template>
                  </a-table-column>
                  <a-table-column :title="t('settings.col_sectors')" :width="120">
                    <template #cell="{ record }">
                      {{ t('settings.sectors_count', { n: record.sector_ids?.length || 0 }) }}
                    </template>
                  </a-table-column>
                  <a-table-column :title="t('settings.col_actions')" :width="120">
                    <template #cell="{ record }">
                      <a-space>
                        <a-button size="mini" @click="openScoped(record)">{{ t('settings.action_edit') }}</a-button>
                        <a-popconfirm @ok="removeScoped(record.user_id)">
                          <a-button size="mini" status="danger">{{ t('settings.action_remove') }}</a-button>
                        </a-popconfirm>
                      </a-space>
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <a-tab-pane key="mail" :title="t('settings.tab_mail')">
        <a-card class="settings-card max-w-2xl" :bordered="false">
          <a-form layout="vertical" :model="form">
            <a-form-item :label="t('settings.mail_smtp')">
              <a-input v-model="form.MAIL_SERVER" :placeholder="t('settings.mail_smtp_ph')" />
            </a-form-item>
            <a-form-item :label="t('settings.mail_port')">
              <a-input v-model="form.MAIL_PORT" :placeholder="t('settings.mail_port_ph')" />
            </a-form-item>
            <a-form-item :label="t('settings.mail_security')">
              <div class="mail-security">
                <div class="mail-security-item">
                  <a-switch
                    :model-value="mailUseTls"
                    @update:model-value="setMailTls"
                  />
                  <div>
                    <span class="mail-security-label">{{ t('settings.mail_tls') }}</span>
                    <span class="mail-security-hint">{{ t('settings.mail_tls_hint') }}</span>
                  </div>
                </div>
                <div class="mail-security-item">
                  <a-switch
                    :model-value="mailUseSsl"
                    @update:model-value="setMailSsl"
                  />
                  <div>
                    <span class="mail-security-label">{{ t('settings.mail_ssl') }}</span>
                    <span class="mail-security-hint">{{ t('settings.mail_ssl_hint') }}</span>
                  </div>
                </div>
              </div>
            </a-form-item>
            <a-form-item :label="t('settings.mail_username')">
              <a-input v-model="form.MAIL_USERNAME" :placeholder="t('settings.mail_username_ph')" />
            </a-form-item>
            <a-form-item :label="t('settings.mail_password')">
              <a-input-password v-model="form.MAIL_PASSWORD" :placeholder="t('settings.mail_password_ph')" />
            </a-form-item>
            <a-form-item :label="t('settings.mail_sender')">
              <a-input v-model="form.MAIL_DEFAULT_SENDER" :placeholder="t('settings.mail_sender_ph')" />
              <template #extra>
                <span class="text-xs text-gray-500">{{ t('settings.mail_sender_hint') }}</span>
              </template>
            </a-form-item>
            <a-form-item :label="t('settings.public_base_url')">
              <a-input v-model="form.PUBLIC_BASE_URL" :placeholder="t('settings.public_base_url_ph')" />
              <template #extra>
                <span class="text-xs text-gray-500">{{ t('settings.public_base_url_hint') }}</span>
              </template>
            </a-form-item>
            <a-divider />
            <a-form-item :label="t('settings.mail_test_to')">
              <a-input
                v-model="mailTestTo"
                :placeholder="t('settings.mail_test_to_ph')"
                allow-clear
              />
              <template #extra>
                <span class="text-xs text-gray-500">{{ t('settings.mail_test_extra') }}</span>
              </template>
            </a-form-item>
            <a-space wrap>
              <a-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</a-button>
              <a-button :loading="testingMail" @click="testMail">{{ t('settings.send_test_mail') }}</a-button>
            </a-space>
          </a-form>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="attachments" :title="t('settings.tab_attachments')">
        <a-card class="settings-card max-w-2xl" :bordered="false">
          <p class="text-sm text-gray-500 mb-4">{{ t('settings.attachments_hint') }}</p>
          <a-form layout="vertical" :model="form">
            <a-form-item :label="t('settings.attachments_extensions')">
              <a-textarea
                v-model="form.ATTACHMENT_ALLOWED_EXTENSIONS"
                :placeholder="t('settings.attachments_extensions_ph')"
                :auto-size="{ minRows: 3, maxRows: 6 }"
              />
              <template #extra>
                <span class="text-xs text-gray-500">{{ t('settings.attachments_extensions_extra') }}</span>
              </template>
            </a-form-item>
            <a-form-item :label="t('settings.attachments_max_mb')">
              <a-input-number
                v-model="attachmentMaxMb"
                :min="1"
                :max="500"
                :precision="0"
                class="w-40"
              />
              <template #extra>
                <span class="text-xs text-gray-500">{{ t('settings.attachments_max_mb_extra') }}</span>
              </template>
            </a-form-item>
            <a-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</a-button>
          </a-form>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="sms" :title="t('settings.tab_sms')">
        <a-card class="rounded-xl max-w-2xl">
          <a-form layout="vertical" :model="form">
            <a-form-item :label="t('settings.sms_gateway')"><a-input v-model="form.SMS_GATEWAY_URL" /></a-form-item>
            <a-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</a-button>
          </a-form>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="azure" :title="t('settings.tab_azure')">
        <a-card class="settings-card max-w-2xl" :bordered="false">
          <a-form layout="vertical" :model="form">
            <a-form-item label="Tenant ID"><a-input v-model="form.AZURE_TENANT_ID" /></a-form-item>
            <a-form-item label="Client ID"><a-input v-model="form.AZURE_CLIENT_ID" /></a-form-item>
            <a-form-item label="Client Secret"><a-input-password v-model="form.AZURE_CLIENT_SECRET" /></a-form-item>
            <a-form-item label="Redirect URI"><a-input v-model="form.AZURE_REDIRECT_URI" /></a-form-item>
            <a-button type="primary" :loading="saving" @click="save">{{ t('common.save') }}</a-button>
          </a-form>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="option-sets" :title="t('settings.tab_option_sets')">
        <OptionSetsAdminPanel />
      </a-tab-pane>

      <a-tab-pane key="record-sets" :title="t('settings.tab_record_sets')">
        <RecordSetsAdminPanel />
      </a-tab-pane>

      <a-tab-pane key="exchange-rates" :title="t('settings.tab_exchange_rates')">
        <ExchangeRatesAdminPanel />
      </a-tab-pane>

      <a-tab-pane key="llm" :title="t('settings.tab_llm')">
        <LlmProvidersAdminPanel />
      </a-tab-pane>

      <a-tab-pane key="workflow-instances" :title="t('settings.tab_workflow_instances')">
        <AdminAllInstancesPanel />
      </a-tab-pane>

      <a-tab-pane key="print-templates" :title="t('settings.tab_print_templates')">
        <PrintTemplatesAdminPanel />
      </a-tab-pane>

      <a-tab-pane key="i18n" :title="t('admin.i18n_title')">
        <I18nSettingsPanel />
      </a-tab-pane>
    </a-tabs>

    <a-modal
      v-model:visible="sectorModal"
      :title="sectorEdit.id ? t('settings.sector_edit_title') : t('settings.sector_new_title')"
      @ok="saveSector"
    >
      <a-form :model="sectorEdit" layout="vertical">
        <a-form-item :label="t('settings.col_code')" required><a-input v-model="sectorEdit.code" :disabled="!!sectorEdit.id" /></a-form-item>
        <a-form-item :label="t('settings.col_name')" required><a-input v-model="sectorEdit.name" /></a-form-item>
        <a-form-item :label="t('settings.col_sort')"><a-input-number v-model="sectorEdit.sort_order" /></a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:visible="scopedModal" :title="t('settings.scoped_modal_title')" @ok="saveScoped" :width="560">
      <a-form layout="vertical" :model="scopedEdit">
        <a-form-item :label="t('settings.col_user')" required>
          <a-select v-model="scopedEdit.user_id" :options="userOpts" allow-search :disabled="!!scopedEdit.id" />
        </a-form-item>
        <a-form-item :label="t('settings.managed_sectors')">
          <a-checkbox-group v-model="scopedEdit.sector_ids">
            <a-checkbox v-for="s in sectors" :key="s.id" :value="s.id">{{ s.name }}</a-checkbox>
          </a-checkbox-group>
        </a-form-item>
        <a-form-item :label="t('settings.permissions')">
          <a-checkbox v-model="scopedEdit.can_design_workflow">{{ t('settings.perm_design') }}</a-checkbox>
          <a-checkbox v-model="scopedEdit.can_view_instances">{{ t('settings.perm_view_instances') }}</a-checkbox>
          <a-checkbox v-model="scopedEdit.can_export_instances">{{ t('settings.perm_export') }}</a-checkbox>
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
import { api, type ApiResponse } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useBrandingStore } from '@/stores/branding'
import PageChrome from '@/components/layout/PageChrome.vue'
import BrandLogo from '@/components/BrandLogo.vue'
import I18nSettingsPanel from '@/components/admin/I18nSettingsPanel.vue'
import OptionSetsAdminPanel from '@/components/admin/OptionSetsAdminPanel.vue'
import RecordSetsAdminPanel from '@/components/admin/RecordSetsAdminPanel.vue'
import ExchangeRatesAdminPanel from '@/components/admin/ExchangeRatesAdminPanel.vue'
import LlmProvidersAdminPanel from '@/components/admin/LlmProvidersAdminPanel.vue'
import PrintTemplatesAdminPanel from '@/components/admin/PrintTemplatesAdminPanel.vue'
import AdminAllInstancesPanel from '@/components/admin/AdminAllInstancesPanel.vue'

const SETTING_TABS = [
  'brand',
  'sectors',
  'admins',
  'mail',
  'attachments',
  'sms',
  'azure',
  'option-sets',
  'record-sets',
  'exchange-rates',
  'llm',
  'workflow-instances',
  'print-templates',
  'i18n',
] as const

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const branding = useBrandingStore()
const tab = ref('brand')

const pageTitle = computed(() => {
  if (tab.value === 'workflow-instances') return t('settings.tab_workflow_instances')
  return t('admin.settings_title')
})

const pageDescription = computed(() => {
  if (tab.value === 'workflow-instances') return t('settings.instances_page_desc')
  return t('settings.page_desc')
})
const saving = ref(false)
const testingMail = ref(false)
const mailTestTo = ref('')
const savingAdmins = ref(false)
const logoUploading = ref(false)
const logoRemoving = ref(false)
const logoFileInput = ref<HTMLInputElement | null>(null)
const logoPreviewData = ref('')
const form = reactive<Record<string, string>>({})
const holidayRegion = ref('CN')
const holidayCompanyId = ref<number>()
const holidayRegionOpts = ref<{ label: string; value: string }[]>([])

const DEFAULT_ATTACHMENT_EXTENSIONS =
  'pdf,doc,docx,xls,xlsx,ppt,pptx,txt,csv,png,jpg,jpeg,gif,webp,bmp,zip,rar,7z,eml,msg'

const attachmentMaxMb = computed({
  get() {
    const n = Number(form.ATTACHMENT_MAX_SIZE_MB)
    return Number.isFinite(n) && n > 0 ? n : 20
  },
  set(v: number | undefined) {
    form.ATTACHMENT_MAX_SIZE_MB = v != null ? String(v) : '20'
  },
})

const logoPreviewUrl = computed(() => {
  if (logoPreviewData.value) return logoPreviewData.value
  const url = form.company_logo_url || branding.logoUrl
  return url || ''
})

function settingTruthy(key: string, defaultVal = false) {
  const v = (form[key] || '').toLowerCase()
  if (!v) return defaultVal
  return !['0', 'false', 'no', 'off'].includes(v)
}

const mailUseTls = computed(() => settingTruthy('MAIL_USE_TLS', !settingTruthy('MAIL_USE_SSL')))
const mailUseSsl = computed(() => settingTruthy('MAIL_USE_SSL'))

function setMailTls(on: boolean) {
  form.MAIL_USE_TLS = on ? 'true' : 'false'
  if (on) form.MAIL_USE_SSL = 'false'
}

function setMailSsl(on: boolean) {
  form.MAIL_USE_SSL = on ? 'true' : 'false'
  if (on) form.MAIL_USE_TLS = 'false'
}

const sectors = ref<{ id: number; code: string; name: string; sort_order: number }[]>([])
const sectorModal = ref(false)
const sectorEdit = reactive({ id: 0, code: '', name: '', sort_order: 0 })

const userOpts = ref<{ label: string; value: number }[]>([])
const globalAdminIds = ref<number[]>([])
const scopedAdmins = ref<
  {
    user_id: number
    username: string
    display_name: string
    sector_ids: number[]
    can_design_workflow: boolean
    can_view_instances: boolean
    can_export_instances: boolean
  }[]
>([])
const scopedModal = ref(false)
const scopedEdit = reactive({
  id: 0 as number | undefined,
  user_id: undefined as number | undefined,
  sector_ids: [] as number[],
  can_design_workflow: true,
  can_view_instances: true,
  can_export_instances: true,
})

async function load() {
  const res = await api.get<
    ApiResponse<Record<string, string> & { company_logo_url?: string | null }>
  >('/admin/settings')
  if (res.data.ok) {
    Object.assign(form, res.data.data)
    branding.setLogoUrl(res.data.data.company_logo_url)
    logoPreviewData.value = ''
    if (!form.MAIL_USE_TLS && !form.MAIL_USE_SSL) {
      form.MAIL_USE_TLS = 'true'
      form.MAIL_USE_SSL = 'false'
    }
    if (!mailTestTo.value && auth.user?.email) {
      mailTestTo.value = auth.user.email
    }
    if (!form.ATTACHMENT_ALLOWED_EXTENSIONS?.trim()) {
      form.ATTACHMENT_ALLOWED_EXTENSIONS = DEFAULT_ATTACHMENT_EXTENSIONS
    }
    if (!form.ATTACHMENT_MAX_SIZE_MB?.trim()) {
      form.ATTACHMENT_MAX_SIZE_MB = '20'
    }
  }
  await loadHolidayRegion()
  await loadSectors()
  await loadUsers()
  await loadScoped()
}

async function loadHolidayRegion() {
  try {
    const [regRes, primaryRes] = await Promise.all([
      api.get<ApiResponse<{ regions: { code: string; name: string; name_en: string }[] }>>(
        '/holidays/regions',
      ),
      api.get<ApiResponse<{ id: number; holiday_region?: string }>>('/org/primary'),
    ])
    const isEn = String(locale.value).startsWith('en')
    holidayRegionOpts.value = (regRes.data.data?.regions || []).map((r) => ({
      value: r.code,
      label: isEn ? r.name_en : r.name,
    }))
    if (primaryRes.data.ok && primaryRes.data.data) {
      holidayCompanyId.value = primaryRes.data.data.id
      holidayRegion.value = primaryRes.data.data.holiday_region || 'CN'
    }
  } catch {
    holidayRegionOpts.value = [{ value: 'CN', label: t('settings.holiday_region') }]
  }
}

async function loadSectors() {
  const res = await api.get('/admin/business-sectors') as {
    data: ApiResponse<typeof sectors.value>
  }
  if (res.data.ok) sectors.value = res.data.data
}

async function loadUsers() {
  const res = await api.get('/users') as { data: ApiResponse<{ id: number; username: string; display_name: string; is_system_admin: boolean }[]> }
  if (res.data.ok) {
    userOpts.value = res.data.data.map((u) => ({
      label: `${u.display_name || u.username} (${u.username})`,
      value: u.id,
    }))
    globalAdminIds.value = res.data.data.filter((u) => u.is_system_admin).map((u) => u.id)
  }
}

async function loadScoped() {
  const res = await api.get('/admin/scoped-admins') as { data: ApiResponse<typeof scopedAdmins.value> }
  if (res.data.ok) scopedAdmins.value = res.data.data
}

function pickLogo() {
  logoFileInput.value?.click()
}

function onLogoFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    Message.warning(t('settings.logo_too_large'))
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    const data = String(reader.result || '')
    logoPreviewData.value = data
    uploadLogo(data)
  }
  reader.readAsDataURL(file)
  ;(e.target as HTMLInputElement).value = ''
}

async function uploadLogo(dataUrl: string) {
  logoUploading.value = true
  try {
    const res = await api.post<ApiResponse<{ company_logo_url?: string }>>('/admin/brand-logo', {
      logo_data: dataUrl,
    })
    if (res.data.ok) {
      form.company_logo_url = res.data.data.company_logo_url || ''
      branding.setLogoUrl(form.company_logo_url)
      logoPreviewData.value = ''
      Message.success(t('settings.logo_updated'))
    }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('settings.upload_failed'))
    logoPreviewData.value = ''
  } finally {
    logoUploading.value = false
  }
}

async function removeLogo() {
  logoRemoving.value = true
  try {
    await api.delete('/admin/brand-logo')
    form.company_logo_url = ''
    logoPreviewData.value = ''
    branding.setLogoUrl(null)
    Message.success(t('settings.logo_removed'))
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('settings.remove_failed'))
  } finally {
    logoRemoving.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const { company_logo_url: _logo, ...payload } = form
    await api.put('/admin/settings', payload)
    if (holidayCompanyId.value) {
      await api.put(`/org/companies/${holidayCompanyId.value}`, {
        holiday_region: holidayRegion.value,
      })
    }
    await branding.load()
    Message.success(t('common.save'))
  } finally {
    saving.value = false
  }
}

async function testMail() {
  const to = mailTestTo.value.trim()
  if (!to) {
    Message.warning(t('settings.fill_test_email'))
    return
  }
  testingMail.value = true
  try {
    await api.post('/admin/settings/test-mail', {
      to,
      MAIL_SERVER: form.MAIL_SERVER,
      MAIL_PORT: form.MAIL_PORT,
      MAIL_USE_TLS: form.MAIL_USE_TLS,
      MAIL_USE_SSL: form.MAIL_USE_SSL,
      MAIL_USERNAME: form.MAIL_USERNAME,
      MAIL_PASSWORD: form.MAIL_PASSWORD,
      MAIL_DEFAULT_SENDER: form.MAIL_DEFAULT_SENDER,
    })
    Message.success(t('settings.mail_test_sent', { to }))
  } catch (e) {
    Message.error(e instanceof Error ? e.message : t('settings.send_failed'))
  } finally {
    testingMail.value = false
  }
}

function openSector(row?: { id: number; code: string; name: string; sort_order: number }) {
  if (row) {
    sectorEdit.id = row.id
    sectorEdit.code = row.code
    sectorEdit.name = row.name
    sectorEdit.sort_order = row.sort_order
  } else {
    sectorEdit.id = 0
    sectorEdit.code = ''
    sectorEdit.name = ''
    sectorEdit.sort_order = 0
  }
  sectorModal.value = true
}

async function saveSector() {
  if (!sectorEdit.code || !sectorEdit.name) return Message.warning(t('settings.fill_code_name'))
  if (sectorEdit.id) {
    await api.put(`/admin/business-sectors/${sectorEdit.id}`, sectorEdit)
  } else {
    await api.post('/admin/business-sectors', sectorEdit)
  }
  sectorModal.value = false
  await loadSectors()
  Message.success(t('settings.saved'))
}

async function removeSector(id: number) {
  await api.delete(`/admin/business-sectors/${id}`)
  await loadSectors()
}

async function saveGlobalAdmins() {
  savingAdmins.value = true
  try {
    const res = await api.get('/users') as { data: ApiResponse<{ id: number; is_system_admin: boolean }[]> }
    if (!res.data.ok) return
    for (const u of res.data.data) {
      const should = globalAdminIds.value.includes(u.id)
      if (u.is_system_admin !== should) {
        await api.put(`/users/${u.id}`, { is_system_admin: should })
      }
    }
    Message.success(t('settings.global_admins_updated'))
    await loadUsers()
  } finally {
    savingAdmins.value = false
  }
}

function openScoped(row?: (typeof scopedAdmins.value)[0]) {
  if (row) {
    scopedEdit.id = row.user_id
    scopedEdit.user_id = row.user_id
    scopedEdit.sector_ids = [...row.sector_ids]
    scopedEdit.can_design_workflow = row.can_design_workflow
    scopedEdit.can_view_instances = row.can_view_instances
    scopedEdit.can_export_instances = row.can_export_instances
  } else {
    scopedEdit.id = undefined
    scopedEdit.user_id = undefined
    scopedEdit.sector_ids = []
    scopedEdit.can_design_workflow = true
    scopedEdit.can_view_instances = true
    scopedEdit.can_export_instances = true
  }
  scopedModal.value = true
}

async function saveScoped() {
  if (!scopedEdit.user_id) return Message.warning(t('settings.pick_user_warn'))
  await api.post('/admin/scoped-admins', scopedEdit)
  scopedModal.value = false
  await loadScoped()
  Message.success(t('settings.saved'))
}

async function removeScoped(userId: number) {
  await api.delete(`/admin/scoped-admins/${userId}`)
  await loadScoped()
}

function syncTabFromRoute() {
  const q = route.query.tab
  if (typeof q === 'string' && (SETTING_TABS as readonly string[]).includes(q)) {
    tab.value = q
  }
}

function onTabChange(key: string | number) {
  const k = String(key)
  if (route.query.tab === k) return
  router.replace({ name: 'admin-settings', query: { ...route.query, tab: k } })
}

watch(() => route.query.tab, syncTabFromRoute)

onMounted(() => {
  syncTabFromRoute()
  load()
})
</script>

<style scoped>
.settings-tabs :deep(.arco-tabs-nav) {
  display: none;
}

.settings-tabs--nav-hidden :deep(.arco-tabs-content) {
  padding-top: 0;
}

.settings-card,
:deep(.settings-card) {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  box-shadow: var(--shadow-xs) !important;
}

.settings-card :deep(.arco-form-item) {
  margin-bottom: var(--app-space-form-item, 10px);
}

.settings-card :deep(.arco-form-item-label) {
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text);
}

.settings-card :deep(.arco-input-wrapper),
.settings-card :deep(.arco-select-view-single),
.settings-card :deep(.arco-select-view-multiple),
.settings-card :deep(.arco-picker),
.settings-card :deep(.arco-input-number) {
  min-height: var(--app-control-h, 34px);
  border-radius: var(--radius-sm);
}

.settings-card :deep(.arco-form-item-label-required-symbol) {
  color: var(--danger);
}

.logo-manager {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.logo-preview-wrap {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--surface-muted);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border-strong);
}

.logo-preview-meta {
  flex: 1;
  min-width: 0;
}

.logo-hint-title {
  margin: 0 0 0.25rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text);
}

.logo-hint-text {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.logo-ratio-hint {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.6;
  color: var(--text-secondary);
}

.logo-ratio-hint strong {
  color: var(--text);
  font-weight: 600;
}

.hidden {
  display: none;
}

.mail-security {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  width: 100%;
}

.mail-security-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.mail-security-label {
  display: block;
  font-weight: 600;
  color: var(--text);
  font-size: 0.9375rem;
}

.mail-security-hint {
  display: block;
  font-size: 0.8125rem;
  color: var(--text-tertiary);
  margin-top: 0.15rem;
}
</style>
