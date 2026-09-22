import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

/** 字段控件分组（4 大类，常用控件靠前） */
export function useFieldCatalog() {
  const { t } = useI18n()

  const catalog = computed(() => [
    {
      group: t('designer.group.common'),
      groupKey: 'common',
      items: [
        { type: 'input', label: t('designer.field.input') },
        { type: 'textarea', label: t('designer.field.textarea') },
        { type: 'number', label: t('designer.field.number') },
        { type: 'phone', label: t('designer.field.phone') },
        { type: 'email', label: t('designer.field.email') },
        { type: 'money', label: t('designer.field.money') },
        { type: 'plain_amount', label: t('designer.field.plain_amount') },
        { type: 'text_block', label: t('designer.field.text_block') },
        { type: 'section_title', label: t('designer.field.section_title') },
        { type: 'divider', label: t('designer.field.divider') },
      ],
    },
    {
      group: t('designer.group.date_calc'),
      groupKey: 'date_calc',
      items: [
        { type: 'date', label: t('designer.field.date') },
        { type: 'datetime', label: t('designer.field.datetime') },
        { type: 'time', label: t('designer.field.time') },
        { type: 'date_range', label: t('designer.field.date_range') },
        { type: 'leave_calendar', label: t('designer.field.leave_calendar') },
        { type: 'formula', label: t('designer.field.formula') },
        { type: 'serial_no', label: t('designer.field.serial_no') },
      ],
    },
    {
      group: t('designer.group.choice_org'),
      groupKey: 'choice_org',
      items: [
        { type: 'select', label: t('designer.field.select') },
        { type: 'multi_select', label: t('designer.field.multi_select') },
        { type: 'radio', label: t('designer.field.radio') },
        { type: 'checkbox_group', label: t('designer.field.checkbox_group') },
        { type: 'switch', label: t('designer.field.switch') },
        { type: 'user_picker', label: t('designer.field.user_picker') },
        { type: 'dept_picker', label: t('designer.field.dept_picker') },
        { type: 'contact', label: t('designer.field.contact') },
        { type: 'record_set', label: t('designer.field.record_set') },
      ],
    },
    {
      group: t('designer.group.advanced_attach'),
      groupKey: 'advanced_attach',
      items: [
        { type: 'attachment', label: t('designer.field.attachment') },
        { type: 'image', label: t('designer.field.image') },
        { type: 'smart_receipt', label: t('designer.field.smart_receipt') },
        { type: 'location', label: t('designer.field.location') },
        { type: 'detail', label: t('designer.field.detail') },
        { type: 'related_form', label: t('designer.field.related_form') },
      ],
    },
  ])

  const catalogFlat = computed(() => catalog.value.flatMap((g) => g.items))

  function labelForType(type: string) {
    return catalogFlat.value.find((i) => i.type === type)?.label || type
  }

  return { catalog, catalogFlat, labelForType }
}
