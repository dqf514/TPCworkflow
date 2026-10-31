export const SYSTEM_SETTING_TAB_KEYS = [
  'brand',
  'sectors',
  'admins',
  'mail',
  'sms',
  'azure',
  'attachments',
  'i18n',
] as const

export const FORM_SETTING_TAB_KEYS = [
  'option-sets',
  'record-sets',
  'exchange-rates',
  'llm',
  'print-templates',
] as const

export const SETTINGS_TAB_LABEL_KEYS: Record<string, string> = {
  brand: 'settings.tab_brand',
  sectors: 'settings.tab_sectors',
  admins: 'settings.tab_admins',
  mail: 'settings.tab_mail',
  sms: 'settings.tab_sms',
  azure: 'settings.tab_azure',
  attachments: 'settings.tab_attachments',
  i18n: 'admin.i18n_title',
  'option-sets': 'settings.tab_option_sets',
  'record-sets': 'settings.tab_record_sets',
  'exchange-rates': 'settings.tab_exchange_rates',
  llm: 'settings.tab_llm',
  'print-templates': 'settings.tab_print_templates',
}
