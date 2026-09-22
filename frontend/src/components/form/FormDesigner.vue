<template>
  <div class="form-designer">
    <div class="designer-left">
      <div class="panel-title">{{ t('designer.palette') }}</div>
      <div class="palette-scroll">
        <section v-for="g in fieldCatalog" :key="g.groupKey" class="palette-section">
          <div class="palette-group-title">{{ g.group }}</div>
          <div class="palette-grid">
            <button
              v-for="item in g.items"
              :key="item.type"
              type="button"
              class="palette-tile"
              draggable="true"
              :title="`${item.label} — ${t('designer.palette_drag_hint')}`"
              @click="addField(item.type)"
              @dragstart="onPaletteDragStart($event, item.type)"
              @dragend="onDragEnd"
            >
              <FieldTypeIcon :type="item.type" />
              <span class="palette-tile-label">{{ item.label }}</span>
            </button>
          </div>
        </section>
      </div>
      <a-button long class="palette-add-section" @click="addSection">{{ t('designer.add_section') }}</a-button>
    </div>

    <div class="designer-center">
      <div class="center-toolbar">
        <a-radio-group v-model="device" type="button" size="small">
          <a-radio value="desktop">{{ t('designer.desktop') }}</a-radio>
          <a-radio value="mobile">{{ t('designer.mobile') }}</a-radio>
        </a-radio-group>
      </div>
      <div class="canvas" :class="`preview-${device}`">
        <div
          v-for="(sec, si) in schema.sections"
          :key="sec.id"
          class="canvas-section"
          :class="{ 'section-active': selectedSectionId === sec.id }"
          @click="selectSection(sec)"
        >
          <div class="sec-head">
            <a-input v-model="sec.title" size="small" class="sec-title-input" @click.stop />
            <a-tag v-if="selectedSectionId === sec.id" size="small" color="arcoblue" class="sec-active-tag">
              {{ t('designer.section_active') }}
            </a-tag>
            <a-space @click.stop>
              <a-button size="mini" @click="moveSection(si, -1)" :disabled="si === 0">↑</a-button>
              <a-button size="mini" @click="moveSection(si, 1)" :disabled="si >= schema.sections.length - 1">↓</a-button>
              <a-button size="mini" status="danger" @click="removeSection(si)">删</a-button>
            </a-space>
          </div>
          <div
            class="sec-body"
            @dragover.prevent="onSectionDragOver($event, sec.id)"
            @dragleave="onSectionDragLeave(sec.id)"
            @drop.prevent="onSectionDrop($event, sec)"
          >
            <div
              v-for="(field, fi) in sec.fields"
              :key="field.id"
              class="field-chip"
              :class="{
                active: selected?.id === field.id,
                'drop-before': dropTarget?.sectionId === sec.id && dropTarget?.index === fi,
              }"
              draggable="true"
              @click.stop="selectField(field, sec)"
              @dragstart.stop="onFieldDragStart($event, sec, field)"
              @dragover.prevent.stop="onFieldDragOver($event, sec.id, fi)"
              @dragleave.stop="onFieldDragLeave"
              @drop.prevent.stop="onFieldDrop($event, sec, fi)"
              @dragend="onDragEnd"
            >
              <span class="drag-handle" title="拖动排序">⋮⋮</span>
              <span class="type-tag">{{ field.type }}</span>
              <span class="truncate">
                {{ field.label || field.key }}
                <a-tag v-if="hasFieldLinkage(field)" size="small" color="purple" class="linkage-tag">联动</a-tag>
                <a-tag v-if="isLinkageTarget(field.id)" size="small" color="arcoblue" class="linkage-tag">受控</a-tag>
                <span v-if="field.type === 'detail'" class="col-count">
                  （{{ t('designer.detail_cols', { n: detailColCount(field) }) }}）
                </span>
              </span>
              <a-space class="chip-actions" @click.stop>
                <a-button size="mini" @click="moveField(sec, fi, -1)" :disabled="fi === 0">↑</a-button>
                <a-button size="mini" @click="moveField(sec, fi, 1)" :disabled="fi >= sec.fields.length - 1">↓</a-button>
                <a-button size="mini" status="danger" @click="removeField(sec, fi)">{{ t('designer.delete_short') }}</a-button>
              </a-space>
            </div>
            <div
              v-if="!sec.fields.length"
              class="sec-drop-empty"
              :class="{ 'drop-active': dropTarget?.sectionId === sec.id && dropTarget?.index === sec.fields.length }"
            >
              <a-empty :description="emptySectionHint(sec)" />
            </div>
            <div
              v-else
              class="sec-drop-tail"
              :class="{ 'drop-active': dropTarget?.sectionId === sec.id && dropTarget?.index === sec.fields.length }"
              @dragover.prevent.stop="onFieldDragOver($event, sec.id, sec.fields.length)"
              @drop.prevent.stop="onFieldDrop($event, sec, sec.fields.length)"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="designer-right">
      <div class="panel-head-row">
        <div class="panel-title">{{ t('designer.field_props') }}</div>
        <a-button
          v-if="selected"
          size="mini"
          status="danger"
          @click="removeSelectedField"
        >
          {{ t('designer.delete_field') }}
        </a-button>
      </div>
      <template v-if="selected">
        <div class="props-scroll">
          <a-form layout="vertical" size="small" class="props-form" :key="propsPanelKey">
            <div class="props-grid cols-3">
              <a-form-item :label="t('designer.label')" class="props-item">
                <a-input v-model="selected.label" />
              </a-form-item>
              <a-form-item v-if="needsKey(selected.type)" :label="t('designer.field_key')" class="props-item">
                <a-input v-model="selected.key" />
              </a-form-item>
              <a-form-item :label="t('designer.type')" class="props-item">
                <a-input :model-value="selected.type" disabled />
              </a-form-item>
            </div>

            <div class="props-switches">
              <label v-if="needsKey(selected.type)" class="props-switch-cell">
                <span>{{ t('designer.required') }}</span>
                <a-switch v-model="selected.required" size="small" />
              </label>
              <label class="props-switch-cell">
                <span>{{ t('designer.visible') }}</span>
                <a-switch v-model="selected.visible" size="small" />
              </label>
              <label
                v-if="needsKey(selected.type) || selected.type === 'leave_calendar'"
                class="props-switch-cell"
              >
                <span>{{ t('designer.printable') }}</span>
                <a-switch v-model="selected.printable" size="small" />
              </label>
              <label v-if="selected.type === 'detail'" class="props-switch-cell">
                <span>{{ t('designer.detail_summary') }}</span>
                <a-switch v-model="detailShowSummary" size="small" />
              </label>
              <label v-if="selected.type === 'related_form'" class="props-switch-cell">
                <span>{{ t('designer.related_multi') }}</span>
                <a-switch v-model="relatedMultiple" size="small" />
              </label>
            </div>

            <template v-if="selected.type === 'user_picker' || selected.type === 'dept_picker'">
              <div class="props-section-title">{{ t('designer.picker_options') }}</div>
              <div class="props-switches">
                <label class="props-switch-cell">
                  <span>{{ t('designer.picker_multiple') }}</span>
                  <a-switch v-model="pickerMultiple" size="small" />
                </label>
                <label v-if="selected.type === 'user_picker'" class="props-switch-cell">
                  <span>{{ t('designer.picker_default_self') }}</span>
                  <a-switch v-model="pickerDefaultSelf" size="small" />
                </label>
                <label v-if="selected.type === 'dept_picker'" class="props-switch-cell">
                  <span>{{ t('designer.picker_default_primary_dept') }}</span>
                  <a-switch v-model="pickerDefaultPrimaryDept" size="small" />
                </label>
              </div>
              <p class="hint-text">{{ pickerOptionsHint }}</p>
            </template>

            <template v-if="isCalendarSyncableType(selected.type)">
              <div class="props-section-title">{{ t('designer.calendar_sync_title') }}</div>
              <div class="props-switches">
                <label class="props-switch-cell">
                  <span>{{ t('designer.calendar_sync') }}</span>
                  <a-switch v-model="syncToCalendar" size="small" />
                </label>
              </div>
              <p class="hint-text">{{ t('designer.calendar_sync_hint') }}</p>
            </template>

            <template v-if="selected.type === 'date_range'">
              <div class="props-section-title">{{ t('designer.date_range_props') }}</div>
              <div class="props-switches">
                <label class="props-switch-cell">
                  <span>{{ t('designer.date_range_half_day') }}</span>
                  <a-switch v-model="dateRangeHalfDay" size="small" />
                </label>
                <label class="props-switch-cell">
                  <span>{{ t('designer.date_range_count_workdays') }}</span>
                  <a-switch v-model="dateRangeCountWorkdays" size="small" />
                </label>
              </div>
              <a-form-item :label="t('designer.date_range_auto_days')" class="props-item">
                <a-select
                  v-model="dateRangeAutoDaysKey"
                  :options="dateRangeAutoDaysOptions"
                  allow-clear
                  allow-search
                  :placeholder="t('designer.date_range_auto_days_ph')"
                />
              </a-form-item>
              <p class="hint-text">{{ t('designer.date_range_half_day_hint') }}</p>
            </template>

            <div v-if="needsKey(selected.type)" class="props-grid cols-2">
              <a-form-item :label="t('designer.placeholder')" class="props-item props-item-span-2">
                <a-input v-model="selected.placeholder" />
              </a-form-item>
            </div>

            <div class="props-section-title">{{ t('designer.grid_divider') }}</div>
            <div class="props-grid cols-2">
              <a-form-item :label="t('designer.desktop')" class="props-item">
                <a-slider v-model="selected.span!.desktop" :min="6" :max="24" :step="2" />
              </a-form-item>
              <a-form-item :label="t('designer.mobile')" class="props-item">
                <a-slider v-model="selected.span!.mobile" :min="12" :max="24" :step="12" />
              </a-form-item>
            </div>

            <template v-if="hasOptions(selected.type)">
              <div class="props-section-title">{{ t('designer.options') }}</div>
              <FieldOptionsPanel :field="selected" />
            </template>

            <template v-if="isLinkageSource(selected.type)">
              <div class="props-section-title">{{ t('designer.linkage_title') }}</div>
              <FieldLinkagePanel :field="selected" :schema="schema" />
            </template>

            <template v-if="needsKey(selected.type)">
              <div class="props-section-title">{{ t('designer.show_when_title') }}</div>
              <FieldShowWhenPanel :field="selected" :schema="schema" />
            </template>

            <template v-if="selected.type === 'record_set'">
              <div class="props-section-title">{{ t('designer.record_set_props') }}</div>
              <RecordSetPickerPanel :field="selected" />
            </template>

            <template v-if="selected.type === 'smart_receipt'">
              <SmartReceiptDesignerPanel :field="selected" :schema="schema" />
            </template>

            <template v-if="selected.type === 'plain_amount'">
              <div class="props-section-title">{{ t('designer.plain_amount_props') }}</div>
              <a-form-item :label="t('designer.formula_precision')" class="props-item">
                <a-input-number v-model="plainAmountPrecision" :min="0" :max="8" />
              </a-form-item>
              <p class="hint-text">{{ t('designer.plain_amount_hint') }}</p>
            </template>

            <FormulaDesignerPanel
              v-if="selected.type === 'formula'"
              :field="selected"
              :schema="schema"
            />

            <template v-if="selected.type === 'serial_no'">
              <div class="props-section-title">{{ t('designer.serial_props') }}</div>
              <p class="hint-text">{{ t('designer.serial_hint') }}</p>
              <a-form-item :label="t('designer.serial_prefix')" class="props-item">
                <a-input v-model="serialPrefix" :placeholder="t('designer.serial_prefix_ph')" />
              </a-form-item>
              <a-form-item :label="t('designer.serial_date_part')" class="props-item">
                <a-select v-model="serialDatePart" :options="serialDatePartOpts" />
              </a-form-item>
              <a-form-item :label="t('designer.serial_separator')" class="props-item">
                <a-input v-model="serialSeparator" :placeholder="t('designer.serial_separator_ph')" />
              </a-form-item>
              <a-form-item :label="t('designer.serial_seq_digits')" class="props-item">
                <a-input-number v-model="serialSeqDigits" :min="1" :max="10" />
              </a-form-item>
              <a-form-item :label="t('designer.serial_suffix')" class="props-item">
                <a-input v-model="serialSuffix" :placeholder="t('designer.serial_suffix_ph')" />
              </a-form-item>
              <a-form-item :label="t('designer.serial_reset_cycle')" class="props-item">
                <a-select v-model="serialResetCycle" :options="serialResetCycleOpts" />
              </a-form-item>
              <a-form-item :label="t('designer.serial_scope')" class="props-item">
                <a-select v-model="serialScope" :options="serialScopeOpts" />
              </a-form-item>
              <a-form-item :label="t('designer.serial_pattern_adv')" class="props-item">
                <a-textarea
                  v-model="serialPatternAdvanced"
                  :auto-size="{ minRows: 2, maxRows: 4 }"
                  :placeholder="t('designer.serial_pattern_adv_ph')"
                />
              </a-form-item>
              <p class="hint-text hint-vars" v-pre>{{ t('designer.serial_tokens') }}</p>
              <p class="hint-text serial-preview">{{ t('designer.serial_preview', { sample: serialPreview }) }}</p>
            </template>

            <template v-if="selected.type === 'text_block'">
              <a-form-item :label="t('designer.text_content')" class="props-item">
                <a-textarea v-model="textBlockContent" :auto-size="{ minRows: 2, maxRows: 6 }" />
              </a-form-item>
            </template>

            <LeaveCalendarDesignerPanel v-if="selected.type === 'leave_calendar'" :field="selected" />

            <template v-if="selected.type === 'detail'">
              <div class="props-section-title">{{ t('designer.detail_cols_tpl') }}</div>
              <p class="hint-text">{{ t('designer.detail_cols_hint') }}</p>
              <div
                v-for="(col, ci) in detailColumns"
                :key="col.id"
                class="detail-col-chip"
                :class="{ active: detailColSelected?.id === col.id }"
                @click="selectDetailCol(col)"
              >
                <span class="detail-col-name">{{ col.label }} ({{ col.type }})</span>
                <a-space class="chip-actions" @click.stop>
                  <a-button size="mini" @click="moveDetailCol(ci, -1)" :disabled="ci === 0">↑</a-button>
                  <a-button size="mini" @click="moveDetailCol(ci, 1)" :disabled="ci >= detailColumns.length - 1">↓</a-button>
                  <a-button size="mini" status="danger" @click="removeDetailCol(ci)">{{ t('designer.delete_short') }}</a-button>
                </a-space>
              </div>
              <a-dropdown trigger="click" @select="addDetailCol">
                <a-button size="mini" long class="mt-1">{{ t('designer.add_detail_col') }}</a-button>
                <template #content>
                  <a-doption v-for="item in detailCatalogFlat" :key="item.type" :value="item.type">
                    {{ item.label }}
                  </a-doption>
                </template>
              </a-dropdown>
              <template v-if="detailColSelected">
                <div class="props-section-title mt-2 props-section-row">
                  <span>{{ t('designer.col_props') }}</span>
                  <a-button size="mini" status="danger" @click="removeSelectedDetailCol">
                    {{ t('designer.delete_col') }}
                  </a-button>
                </div>
                <div class="props-grid cols-3">
                  <a-form-item :label="t('designer.col_label')" class="props-item">
                    <a-input v-model="detailColSelected.label" />
                  </a-form-item>
                  <a-form-item :label="t('designer.col_key')" class="props-item">
                    <a-input v-model="detailColSelected.key" />
                  </a-form-item>
                  <a-form-item :label="t('designer.required')" class="props-item props-item-switch">
                    <a-switch v-model="detailColSelected.required" size="small" />
                  </a-form-item>
                </div>
                <template v-if="detailColSelected && hasOptions(detailColSelected.type)">
                  <div class="props-section-title">{{ t('designer.col_options') }}</div>
                  <FieldOptionsPanel :field="detailColSelected" />
                </template>
                <FormulaDesignerPanel
                  v-if="detailColSelected?.type === 'formula'"
                  :field="detailColSelected"
                  :schema="schema"
                  :detail-key="selected.key"
                />
                <template v-if="detailColSelected?.type === 'plain_amount'">
                  <div class="props-section-title">{{ t('designer.plain_amount_props') }}</div>
                  <a-form-item :label="t('designer.formula_precision')" class="props-item">
                    <a-input-number v-model="detailColPlainAmountPrecision" :min="0" :max="8" />
                  </a-form-item>
                  <p class="hint-text">{{ t('designer.plain_amount_hint') }}</p>
                </template>
                <template
                  v-if="detailColSelected && (detailColSelected.type === 'attachment' || detailColSelected.type === 'image')"
                >
                  <div class="props-section-title">{{ t('designer.attachment_props') }}</div>
                  <label class="props-switch-cell">
                    <span>{{ t('designer.attachment_allow_multiple') }}</span>
                    <a-switch v-model="detailColAllowMultiple" size="small" />
                  </label>
                  <a-form-item
                    v-if="detailColAllowMultiple"
                    :label="t('designer.attachment_max_count')"
                    class="props-item"
                  >
                    <a-input-number v-model="detailColMaxCount" :min="2" :max="20" />
                  </a-form-item>
                  <p v-else class="hint-text">{{ t('designer.attachment_single_hint') }}</p>
                  <div class="props-section-title">{{ t('designer.detail_col_receipt') }}</div>
                  <label class="props-switch-cell">
                    <span>{{ t('designer.detail_col_receipt_enable') }}</span>
                    <a-switch v-model="detailColRecognitionEnabled" size="small" />
                  </label>
                  <p class="hint-text">{{ t('designer.detail_col_receipt_hint') }}</p>
                </template>
              </template>
            </template>

            <template v-if="selected.type === 'related_form'">
              <div class="props-section-title">{{ t('designer.related_link_scope') }}</div>
              <a-form-item :label="t('designer.related_forms')" class="props-item">
                <a-select
                  v-model="relatedFormKeys"
                  :options="publishedFormOpts"
                  multiple
                  allow-search
                  :placeholder="t('designer.related_forms_ph')"
                  :max-tag-count="3"
                />
              </a-form-item>
              <p class="hint-text">{{ t('designer.related_forms_hint') }}</p>
            </template>
          </a-form>
        </div>
      </template>
      <a-empty v-else :description="sectionOnlyHint" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api, type ApiResponse } from '@/api/client'
import { useFieldCatalog } from '@/composables/useFieldCatalog'
import FieldOptionsPanel from '@/components/form/FieldOptionsPanel.vue'
import FieldLinkagePanel from '@/components/form/FieldLinkagePanel.vue'
import FieldShowWhenPanel from '@/components/form/FieldShowWhenPanel.vue'
import RecordSetPickerPanel from '@/components/form/RecordSetPickerPanel.vue'
import SmartReceiptDesignerPanel from '@/components/form/SmartReceiptDesignerPanel.vue'
import FormulaDesignerPanel from '@/components/form/FormulaDesignerPanel.vue'
import FieldTypeIcon from '@/components/form/FieldTypeIcon.vue'
import LeaveCalendarDesignerPanel from '@/components/form/LeaveCalendarDesignerPanel.vue'
import { DEFAULT_FORM_SCHEMA, newField, type FormFieldDef, type FormSchema, type FormSection } from '@/types/form'
import { usesCountWorkdays } from '@/utils/dateRangeValue'
import {
  defaultSerialNoProps,
  previewSerialNo,
  type SerialDatePart,
  type SerialResetCycle,
  type SerialScope,
} from '@/utils/serialNoPattern'
import {
  getFieldLinkage,
  isLinkageSourceType,
  isLinkageTargetField,
} from '@/composables/useFieldLinkage'

const DND_FIELD_TYPE = 'application/x-tpcw-field-type'
const DND_FIELD_MOVE = 'application/x-tpcw-field-move'

const { t } = useI18n()
const { catalog: fieldCatalog, catalogFlat, labelForType } = useFieldCatalog()

const props = defineProps<{ modelValue?: FormSchema; currentFormKey?: string }>()
const emit = defineEmits<{ 'update:modelValue': [FormSchema] }>()

const schema = ref<FormSchema>(props.modelValue ? JSON.parse(JSON.stringify(props.modelValue)) : DEFAULT_FORM_SCHEMA())
const device = ref<'desktop' | 'mobile'>('desktop')
const selected = ref<FormFieldDef | null>(null)
const selectedSectionId = ref<string>('')
const dropTarget = ref<{ sectionId: string; index: number } | null>(null)
/** 属性面板 key：schema 深拷贝后强制重绑选中字段，避免开关等控件 UI 不刷新 */
const propsPanelKey = ref(0)

const selectedSection = computed(() =>
  schema.value.sections.find((s) => s.id === selectedSectionId.value) || null,
)

const sectionOnlyHint = computed(() => {
  if (selectedSection.value) {
    return t('designer.section_selected_hint', { title: selectedSection.value.title || t('designer.new_section') })
  }
  return t('designer.pick_field')
})

function emptySectionHint(sec: FormSection) {
  if (selectedSectionId.value === sec.id) return t('designer.empty_section_active')
  return t('designer.empty_section')
}

const textBlockContent = computed({
  get: () => String(selected.value?.props?.content || ''),
  set: (v: string) => {
    if (selected.value?.props) selected.value.props.content = v
  },
})

const publishedFormOpts = ref<{ label: string; value: string }[]>([])
const detailColSelected = ref<FormFieldDef | null>(null)

const relatedFormKeys = computed({
  get: () => schema.value.settings?.relatedFormKeys || [],
  set: (v: string[]) => {
    if (!schema.value.settings) schema.value.settings = { relatedFormKeys: [] }
    schema.value.settings.relatedFormKeys = v
  },
})

const detailColumns = computed({
  get: () => {
    if (!selected.value?.props) return []
    return (selected.value.props.columns as FormFieldDef[]) || []
  },
  set: (cols: FormFieldDef[]) => {
    if (selected.value?.props) selected.value.props.columns = cols
  },
})

const detailShowSummary = computed({
  get: () => selected.value?.props?.showSummary !== false,
  set: (v: boolean) => {
    if (selected.value?.props) selected.value.props.showSummary = v
  },
})

const relatedMultiple = computed({
  get: () => !!selected.value?.props?.multiple,
  set: (v: boolean) => {
    if (selected.value?.props) selected.value.props.multiple = v
  },
})

function ensurePickerProps() {
  if (!selected.value?.props) selected.value!.props = {}
}

const pickerMultiple = computed({
  get: () => !!selected.value?.props?.multiple,
  set: (v: boolean) => {
    ensurePickerProps()
    selected.value!.props!.multiple = v
  },
})

const pickerDefaultSelf = computed({
  get: () => !!selected.value?.props?.defaultSelf,
  set: (v: boolean) => {
    ensurePickerProps()
    selected.value!.props!.defaultSelf = v
  },
})

const pickerDefaultPrimaryDept = computed({
  get: () => !!selected.value?.props?.defaultPrimaryDept,
  set: (v: boolean) => {
    ensurePickerProps()
    selected.value!.props!.defaultPrimaryDept = v
  },
})

const syncToCalendar = computed({
  get: () => selected.value?.props?.syncToCalendar === true,
  set: (v: boolean) => {
    if (!selected.value) return
    if (!selected.value.props) selected.value.props = {}
    selected.value.props.syncToCalendar = v
  },
})

function ensureDateRangeProps() {
  if (!selected.value) return
  if (!selected.value.props) selected.value.props = {}
}

const dateRangeHalfDay = computed({
  get: () => selected.value?.props?.halfDay === true,
  set: (v: boolean) => {
    ensureDateRangeProps()
    selected.value!.props!.halfDay = v
  },
})

const dateRangeCountWorkdays = computed({
  get: () => {
    const field = selected.value
    if (!field) return false
    const v = field.props?.countWorkdays
    if (v === true) return true
    if (v === false) return false
    return usesCountWorkdays(field, dateRangeAutoDaysOptions.value.map((o) => o.value))
  },
  set: (v: boolean) => {
    ensureDateRangeProps()
    selected.value!.props!.countWorkdays = v
  },
})

const dateRangeAutoDaysKey = computed({
  get: () => String(selected.value?.props?.autoDaysKey || ''),
  set: (v: string) => {
    ensureDateRangeProps()
    selected.value!.props!.autoDaysKey = v || ''
  },
})

const dateRangeAutoDaysOptions = computed(() => {
  const currentId = selected.value?.id
  const opts: { label: string; value: string }[] = []
  for (const sec of schema.value.sections || []) {
    for (const field of sec.fields || []) {
      if (field.type === 'number' && field.key && field.id !== currentId) {
        opts.push({ label: `${field.label} (${field.key})`, value: field.key })
      }
    }
  }
  return opts
})

const detailColRecognitionEnabled = computed({
  get: () => {
    const rec = detailColSelected.value?.props?.recognition as { enabled?: boolean } | undefined
    return rec?.enabled === true
  },
  set: (v: boolean) => {
    const col = detailColSelected.value
    if (!col) return
    if (!col.props) col.props = {}
    if (!col.props.recognition || typeof col.props.recognition !== 'object') {
      col.props.recognition = {
        enabled: v,
        scene: 'expense',
        autoFill: true,
        mappings: [],
      }
    } else {
      ;(col.props.recognition as { enabled: boolean }).enabled = v
    }
  },
})

const detailColAllowMultiple = computed({
  get: () => detailColSelected.value?.props?.allowMultiple === true,
  set: (v: boolean) => {
    const col = detailColSelected.value
    if (!col) return
    if (!col.props) col.props = {}
    col.props.allowMultiple = v
    if (!v) {
      col.props.maxCount = 1
    } else if (!col.props.maxCount || Number(col.props.maxCount) < 2) {
      col.props.maxCount = 5
    }
  },
})

const detailColMaxCount = computed({
  get: () => Math.max(2, Number(detailColSelected.value?.props?.maxCount) || 5),
  set: (v: number) => {
    const col = detailColSelected.value
    if (!col) return
    if (!col.props) col.props = {}
    col.props.maxCount = Math.min(20, Math.max(2, Number(v) || 5))
  },
})

const pickerOptionsHint = computed(() => {
  if (selected.value?.type === 'user_picker') return t('designer.picker_default_self_hint')
  if (selected.value?.type === 'dept_picker') return t('designer.picker_default_primary_dept_hint')
  return ''
})

const detailCatalogFlat = computed(() =>
  catalogFlat.value.filter(
    (i) =>
      !['detail', 'related_form', 'divider', 'text_block', 'section_title', 'leave_calendar'].includes(i.type),
    ),
)


const plainAmountPrecision = computed({
  get: () => Number(selected.value?.props?.precision ?? 2),
  set: (v: number) => {
    if (!selected.value) return
    if (!selected.value.props) selected.value.props = {}
    selected.value.props.precision = v
  },
})

function ensureSerialProps() {
  if (!selected.value || selected.value.type !== 'serial_no') return
  if (!selected.value.props) selected.value.props = {}
  if (!selected.value.props.serial || typeof selected.value.props.serial !== 'object') {
    const legacyPattern = String(selected.value.props.pattern || '').trim()
    selected.value.props.serial = {
      ...defaultSerialNoProps().serial,
      ...(legacyPattern ? { pattern: legacyPattern } : {}),
      resetCycle: (selected.value.props.resetCycle as SerialResetCycle) || 'day',
    }
  }
}

function clearSerialPatternOverride() {
  if (!selected.value?.props?.serial) return
  const serial = selected.value.props.serial as Record<string, unknown>
  serial.pattern = ''
  delete selected.value.props.pattern
}

const serialDatePartOpts = computed(() => [
  { label: t('designer.serial_date_none'), value: 'none' },
  { label: t('designer.serial_date_yyyy'), value: 'YYYY' },
  { label: t('designer.serial_date_yyyymm'), value: 'YYYYMM' },
  { label: t('designer.serial_date_yyyymmdd'), value: 'YYYYMMDD' },
])

const serialResetCycleOpts = computed(() => [
  { label: t('designer.serial_reset_day'), value: 'day' },
  { label: t('designer.serial_reset_month'), value: 'month' },
  { label: t('designer.serial_reset_year'), value: 'year' },
  { label: t('designer.serial_reset_never'), value: 'never' },
])

const serialScopeOpts = computed(() => [
  { label: t('designer.serial_scope_company'), value: 'company' },
  { label: t('designer.serial_scope_definition'), value: 'definition' },
  { label: t('designer.serial_scope_global'), value: 'global' },
])

const serialPrefix = computed({
  get: () => {
    ensureSerialProps()
    return String((selected.value?.props?.serial as Record<string, unknown>)?.prefix || '')
  },
  set: (v: string) => {
    ensureSerialProps()
    ;(selected.value!.props!.serial as Record<string, unknown>).prefix = v
    clearSerialPatternOverride()
  },
})

const serialSuffix = computed({
  get: () => {
    ensureSerialProps()
    return String((selected.value?.props?.serial as Record<string, unknown>)?.suffix || '')
  },
  set: (v: string) => {
    ensureSerialProps()
    ;(selected.value!.props!.serial as Record<string, unknown>).suffix = v
    clearSerialPatternOverride()
  },
})

const serialSeparator = computed({
  get: () => {
    ensureSerialProps()
    const v = (selected.value?.props?.serial as Record<string, unknown>)?.separator
    return v === undefined || v === null ? '-' : String(v)
  },
  set: (v: string) => {
    ensureSerialProps()
    ;(selected.value!.props!.serial as Record<string, unknown>).separator = v
    clearSerialPatternOverride()
  },
})

const serialSeqDigits = computed({
  get: () => {
    ensureSerialProps()
    return Number((selected.value?.props?.serial as Record<string, unknown>)?.seqDigits ?? 4)
  },
  set: (v: number) => {
    ensureSerialProps()
    ;(selected.value!.props!.serial as Record<string, unknown>).seqDigits = Math.max(1, Math.min(10, Number(v) || 4))
    clearSerialPatternOverride()
  },
})

const serialDatePart = computed({
  get: () => {
    ensureSerialProps()
    return String((selected.value?.props?.serial as Record<string, unknown>)?.datePart || 'YYYYMMDD') as SerialDatePart
  },
  set: (v: SerialDatePart) => {
    ensureSerialProps()
    ;(selected.value!.props!.serial as Record<string, unknown>).datePart = v
    clearSerialPatternOverride()
  },
})

const serialResetCycle = computed({
  get: () => {
    ensureSerialProps()
    return String((selected.value?.props?.serial as Record<string, unknown>)?.resetCycle || 'day') as SerialResetCycle
  },
  set: (v: SerialResetCycle) => {
    ensureSerialProps()
    ;(selected.value!.props!.serial as Record<string, unknown>).resetCycle = v
  },
})

const serialScope = computed({
  get: () => {
    ensureSerialProps()
    return String((selected.value?.props?.serial as Record<string, unknown>)?.scope || 'company') as SerialScope
  },
  set: (v: SerialScope) => {
    ensureSerialProps()
    ;(selected.value!.props!.serial as Record<string, unknown>).scope = v
  },
})

const serialPatternAdvanced = computed({
  get: () => {
    ensureSerialProps()
    const serial = selected.value?.props?.serial as Record<string, unknown> | undefined
    return String(serial?.pattern || selected.value?.props?.pattern || '')
  },
  set: (v: string) => {
    ensureSerialProps()
    const serial = selected.value!.props!.serial as Record<string, unknown>
    serial.pattern = v
    if (v.trim()) {
      selected.value!.props!.pattern = v
      selected.value!.props!.resetCycle = serial.resetCycle
    } else {
      delete selected.value!.props!.pattern
    }
  },
})

const serialPreview = computed(() => {
  if (!selected.value || selected.value.type !== 'serial_no') return ''
  ensureSerialProps()
  return previewSerialNo(selected.value, 1)
})

const detailColPlainAmountPrecision = computed({
  get: () => Number(detailColSelected.value?.props?.precision ?? 2),
  set: (v: number) => {
    if (!detailColSelected.value) return
    if (!detailColSelected.value.props) detailColSelected.value.props = {}
    detailColSelected.value.props.precision = v
  },
})


function detailColCount(field: FormFieldDef) {
  return ((field.props?.columns as FormFieldDef[]) || []).length
}

function addDetailCol(type: string | number | Record<string, unknown>) {
  if (!selected.value || selected.value.type !== 'detail') return
  const typeStr = String(type)
  const col = newField(typeStr)
  col.label = labelForType(typeStr)
  col.key = `${col.key}_${detailColumns.value.length + 1}`
  if (!selected.value.props) selected.value.props = {}
  const cols = [...detailColumns.value, col]
  selected.value.props.columns = cols
  detailColSelected.value = col
  emitSchema()
}

function removeDetailCol(ci: number) {
  const cols = [...detailColumns.value]
  cols.splice(ci, 1)
  detailColumns.value = cols
  detailColSelected.value = null
  emitSchema()
}

function moveDetailCol(ci: number, delta: number) {
  const t = ci + delta
  const cols = [...detailColumns.value]
  if (t < 0 || t >= cols.length) return
  ;[cols[ci], cols[t]] = [cols[t], cols[ci]]
  detailColumns.value = cols
  emitSchema()
}

onMounted(async () => {
  if (!schema.value.settings) schema.value.settings = { relatedFormKeys: [] }
  ensureSelectedSection()
  const res = await api.get<ApiResponse<{ key: string; name: string; status: string }[]>>(
    '/forms/definitions',
    { params: { status: 'published' } },
  )
  if (res.data.ok) {
    const selfKey = props.currentFormKey || ''
    publishedFormOpts.value = res.data.data
      .filter((f) => f.key && f.key !== selfKey)
      .map((f) => ({ label: `${f.name}（${f.key}）`, value: f.key }))
  }
})

function schemaFingerprint(s: FormSchema | undefined): string {
  if (!s) return ''
  return JSON.stringify(s)
}

function emitSchema() {
  const out = JSON.parse(JSON.stringify(schema.value)) as FormSchema
  const parent = props.modelValue
  // 打印 Tab / 工具栏可能直接改父级 schema，回写时保留这些字段
  if (parent?.print) {
    out.print = JSON.parse(JSON.stringify(parent.print))
  }
  if (parent?.title !== undefined) out.title = parent.title
  if (parent?.description !== undefined) out.description = parent.description
  emit('update:modelValue', out)
}

let emitTimer: ReturnType<typeof setTimeout> | null = null

function emitSchemaDebounced() {
  if (emitTimer) clearTimeout(emitTimer)
  emitTimer = setTimeout(() => {
    emitSchema()
    emitTimer = null
  }, 350)
}

/** 父组件 v-model 回写 schema 后，按 id 重新绑定选中字段引用（不刷新属性面板 key，避免输入失焦） */
function resyncSelection() {
  const selId = selected.value?.id
  const colId = detailColSelected.value?.id
  if (!selId) return
  for (const sec of schema.value.sections) {
    for (const f of sec.fields) {
      if (f.id !== selId) continue
      selected.value = f
      selectedSectionId.value = sec.id
      if (colId && f.type === 'detail') {
        const cols = (f.props?.columns as FormFieldDef[]) || []
        detailColSelected.value = cols.find((c) => c.id === colId) || null
      } else if (!colId) {
        detailColSelected.value = null
      }
      return
    }
  }
  selected.value = null
  detailColSelected.value = null
}

let syncingFromParent = false

watch(schema, () => {
  if (syncingFromParent) return
  emitSchemaDebounced()
}, { deep: true })

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    if (schemaFingerprint(v) === schemaFingerprint(schema.value)) return
    syncingFromParent = true
    schema.value = JSON.parse(JSON.stringify(v))
    nextTick(() => {
      ensureSelectedSection()
      resyncSelection()
      syncingFromParent = false
    })
  },
)

onBeforeUnmount(() => {
  if (emitTimer) {
    clearTimeout(emitTimer)
    emitTimer = null
  }
})

function needsKey(type: string) {
  return !['divider', 'text_block', 'section_title', 'leave_calendar'].includes(type)
}

function isCalendarSyncableType(type: string) {
  return ['date', 'datetime', 'date_range'].includes(type)
}

function hasOptions(type: string) {
  return ['select', 'multi_select', 'radio', 'checkbox_group'].includes(type)
}

function isLinkageSource(type: string) {
  return isLinkageSourceType(type)
}

function hasFieldLinkage(field: FormFieldDef) {
  return !!getFieldLinkage(field)?.rules?.length
}

function isLinkageTarget(fieldId: string) {
  return isLinkageTargetField(fieldId, schema.value)
}

function ensureSelectedSection() {
  if (selectedSectionId.value && schema.value.sections.some((s) => s.id === selectedSectionId.value)) {
    return
  }
  selectedSectionId.value = schema.value.sections[0]?.id || ''
}

function findSectionById(id: string | null | undefined): FormSection | undefined {
  if (!id) return undefined
  return schema.value.sections.find((s) => s.id === id)
}

function resolveTargetSection(explicit?: FormSection): FormSection | undefined {
  return explicit || findSectionById(selectedSectionId.value) || schema.value.sections.at(-1)
}

function insertField(type: string, sec: FormSection, index?: number) {
  const f = newField(type)
  f.label = labelForType(type)
  if (!f.span) f.span = { desktop: 12, mobile: 24 }
  const at = index == null ? sec.fields.length : Math.max(0, Math.min(index, sec.fields.length))
  sec.fields.splice(at, 0, f)
  selectedSectionId.value = sec.id
  selectField(f, sec)
  emitSchema()
  return f
}

function addField(type: string) {
  const sec = resolveTargetSection()
  if (!sec) return
  insertField(type, sec)
}

function selectSection(sec: FormSection) {
  selectedSectionId.value = sec.id
  selected.value = null
  detailColSelected.value = null
}

function onPaletteDragStart(e: DragEvent, type: string) {
  e.dataTransfer?.setData(DND_FIELD_TYPE, type)
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'copy'
}

function onFieldDragStart(e: DragEvent, sec: FormSection, field: FormFieldDef) {
  e.dataTransfer?.setData(
    DND_FIELD_MOVE,
    JSON.stringify({ sectionId: sec.id, fieldId: field.id }),
  )
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
  selectField(field, sec)
}

function onDragEnd() {
  dropTarget.value = null
}

function onSectionDragOver(e: DragEvent, sectionId: string) {
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = e.dataTransfer.types.includes(DND_FIELD_MOVE) ? 'move' : 'copy'
  }
  dropTarget.value = { sectionId, index: findSectionById(sectionId)?.fields.length || 0 }
}

function onSectionDragLeave(sectionId: string) {
  if (dropTarget.value?.sectionId === sectionId) dropTarget.value = null
}

function onFieldDragOver(e: DragEvent, sectionId: string, index: number) {
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = e.dataTransfer.types.includes(DND_FIELD_MOVE) ? 'move' : 'copy'
  }
  dropTarget.value = { sectionId, index }
}

function onFieldDragLeave() {
  /* 由 dragenter 到其他 chip 时更新 dropTarget */
}

function onSectionDrop(e: DragEvent, sec: FormSection) {
  dropTarget.value = null
  const type = e.dataTransfer?.getData(DND_FIELD_TYPE)
  if (type) {
    selectSection(sec)
    insertField(type, sec)
    return
  }
  const moveRaw = e.dataTransfer?.getData(DND_FIELD_MOVE)
  if (moveRaw) {
    moveFieldByDrag(moveRaw, sec.id, sec.fields.length)
  }
}

function onFieldDrop(e: DragEvent, sec: FormSection, index: number) {
  dropTarget.value = null
  const type = e.dataTransfer?.getData(DND_FIELD_TYPE)
  if (type) {
    selectSection(sec)
    insertField(type, sec, index)
    return
  }
  const moveRaw = e.dataTransfer?.getData(DND_FIELD_MOVE)
  if (moveRaw) {
    moveFieldByDrag(moveRaw, sec.id, index)
  }
}

function moveFieldByDrag(raw: string, toSectionId: string, toIndex: number) {
  let payload: { sectionId?: string; fieldId?: string }
  try {
    payload = JSON.parse(raw)
  } catch {
    return
  }
  const fromSectionId = payload.sectionId
  const fieldId = payload.fieldId
  if (!fromSectionId || !fieldId) return

  const fromSec = findSectionById(fromSectionId)
  const toSec = findSectionById(toSectionId)
  if (!fromSec || !toSec) return

  const fromIndex = fromSec.fields.findIndex((f) => f.id === fieldId)
  if (fromIndex < 0) return

  const [field] = fromSec.fields.splice(fromIndex, 1)
  let insertAt = Math.max(0, Math.min(toIndex, toSec.fields.length))
  if (fromSectionId === toSectionId && fromIndex < insertAt) insertAt -= 1

  toSec.fields.splice(insertAt, 0, field)
  selectedSectionId.value = toSec.id
  selectField(field, toSec)
  emitSchema()
}

function addSection() {
  const sec: FormSection = {
    id: `section_${Date.now()}`,
    title: t('designer.new_section'),
    collapsed: false,
    fields: [],
  }
  schema.value.sections.push(sec)
  selectSection(sec)
  emitSchema()
}

function selectField(f: FormFieldDef, sec: FormSection) {
  selectedSectionId.value = sec.id
  selected.value = f
  if (!f.span) f.span = { desktop: 12, mobile: 24 }
  detailColSelected.value = null
  propsPanelKey.value += 1
}

function selectDetailCol(col: FormFieldDef) {
  detailColSelected.value = col
  propsPanelKey.value += 1
}

function removeField(sec: { fields: FormFieldDef[] }, fi: number) {
  sec.fields.splice(fi, 1)
  selected.value = null
  detailColSelected.value = null
  emitSchema()
}

function removeSelectedField() {
  if (!selected.value) return
  for (const sec of schema.value.sections) {
    const fi = sec.fields.findIndex((f) => f.id === selected.value!.id)
    if (fi >= 0) {
      removeField(sec, fi)
      return
    }
  }
}

function removeSelectedDetailCol() {
  if (!detailColSelected.value) return
  const ci = detailColumns.value.findIndex((c) => c.id === detailColSelected.value!.id)
  if (ci >= 0) removeDetailCol(ci)
}

function moveField(sec: { fields: FormFieldDef[] }, fi: number, delta: number) {
  const t = fi + delta
  if (t < 0 || t >= sec.fields.length) return
  const arr = sec.fields
  ;[arr[fi], arr[t]] = [arr[t], arr[fi]]
  emitSchema()
}

function removeSection(si: number) {
  if (schema.value.sections.length <= 1) return
  const removed = schema.value.sections[si]
  schema.value.sections.splice(si, 1)
  if (selectedSectionId.value === removed.id) {
    const next = schema.value.sections[Math.min(si, schema.value.sections.length - 1)]
    if (next) selectSection(next)
    else selectedSectionId.value = ''
  }
  if (selected.value && removed.fields.some((f) => f.id === selected.value!.id)) {
    selected.value = null
    detailColSelected.value = null
  }
  emitSchema()
}

function moveSection(si: number, delta: number) {
  const t = si + delta
  if (t < 0 || t >= schema.value.sections.length) return
  const arr = schema.value.sections
  ;[arr[si], arr[t]] = [arr[t], arr[si]]
  emitSchema()
}
</script>

<style scoped>
.form-designer {
  display: grid;
  grid-template-columns: 248px 1fr 560px;
  gap: 12px;
  height: 100%;
  min-height: 480px;
}

.designer-left,
.designer-right {
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  padding: 8px;
  overflow: hidden;
  background: #fff;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.props-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.designer-right :deep(.props-form .arco-form-item) {
  margin-bottom: 0;
}

.designer-right :deep(.props-form .arco-form-item-label-col) {
  padding-bottom: 2px;
}

.designer-right :deep(.props-form .arco-form-item-label) {
  font-size: 12px;
  line-height: 1.2;
}

.props-grid {
  display: grid;
  gap: 4px 12px;
  margin-bottom: 8px;
}

.props-grid.cols-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.props-grid.cols-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.props-item-span-2 {
  grid-column: 1 / -1;
}

.props-item-switch :deep(.arco-form-item-content) {
  min-height: 28px;
  display: flex;
  align-items: center;
}

.props-switches {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 20px;
  margin-bottom: 10px;
  padding: 8px 12px;
  background: #f7f8fa;
  border-radius: 6px;
}

.props-switch-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #4e5969;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.props-section-title {
  font-size: 12px;
  font-weight: 600;
  color: #1d2129;
  margin: 10px 0 6px;
  padding-top: 8px;
  border-top: 1px dashed #e5e6eb;
}

.props-section-title:first-child {
  border-top: none;
  padding-top: 0;
  margin-top: 0;
}

.props-section-title.mt-2 {
  margin-top: 12px;
}

.designer-right :deep(.field-options-panel .arco-form-item) {
  margin-bottom: 6px;
}

.designer-right :deep(.field-options-panel .hint-text) {
  margin: 2px 0 6px;
}

.designer-center {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  background: #f7f8fa;
  overflow: hidden;
}

.panel-title {
  font-weight: 600;
  margin-bottom: 0;
  font-size: 13px;
}

.panel-head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.props-section-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.palette-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin: 0 -2px;
  padding: 0 2px;
}

.palette-section + .palette-section {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f2f3f5;
}

.palette-group-title {
  font-size: 11px;
  color: #86909c;
  margin-bottom: 4px;
  line-height: 1.2;
}

.palette-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
}

.palette-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 2px;
  padding: 5px 2px 4px;
  min-height: 46px;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
}

.palette-tile:hover {
  border-color: rgb(var(--primary-6));
  background: #f7faff;
  box-shadow: 0 1px 4px rgba(22, 93, 255, 0.08);
}

.palette-tile:hover :deep(.field-type-icon) {
  color: rgb(var(--primary-6));
}

.palette-tile:active {
  background: #e8f3ff;
}

.palette-tile-label {
  font-size: 10px;
  line-height: 1.2;
  color: #4e5969;
  text-align: center;
  width: 100%;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  word-break: break-all;
}

.palette-add-section {
  flex-shrink: 0;
  margin-top: 6px;
}


.center-toolbar {
  display: flex;
  gap: 8px;
  padding: 8px;
  background: #fff;
  border-bottom: 1px solid #e5e6eb;
  flex-shrink: 0;
}

.canvas {
  flex: 1;
  overflow: auto;
  padding: 12px;
}

.preview-mobile {
  max-width: 390px;
  margin: 0 auto;
  background: #fff;
  border: 1px dashed #c9cdd4;
  border-radius: 12px;
  min-height: 100%;
}

.canvas-section {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
  border: 2px solid transparent;
  transition: border-color 0.15s, box-shadow 0.15s;
  cursor: pointer;
}

.canvas-section.section-active {
  border-color: rgb(var(--primary-6));
  box-shadow: 0 0 0 1px rgba(var(--primary-6), 0.15);
}

.sec-active-tag {
  flex-shrink: 0;
}

.sec-body {
  min-height: 48px;
}

.sec-drop-empty {
  border: 1px dashed #c9cdd4;
  border-radius: 6px;
  padding: 8px;
  background: #fafafa;
}

.sec-drop-empty.drop-active,
.sec-drop-tail.drop-active {
  border-color: rgb(var(--primary-6));
  background: #e8f3ff;
}

.sec-drop-tail {
  height: 10px;
  margin-top: 4px;
  border-radius: 4px;
  border: 1px dashed transparent;
}

.sec-head {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.sec-title-input {
  flex: 1;
}

.field-chip .linkage-tag {
  margin-left: 4px;
  vertical-align: middle;
  transform: scale(0.92);
}

.field-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid #e5e6eb;
  border-radius: 6px;
  margin-bottom: 6px;
  cursor: grab;
  background: #fafafa;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.field-chip.drop-before {
  box-shadow: inset 0 3px 0 rgb(var(--primary-6));
}

.drag-handle {
  flex-shrink: 0;
  color: #c9cdd4;
  font-size: 12px;
  letter-spacing: -2px;
  user-select: none;
  cursor: grab;
}

.field-chip.active {
  border-color: rgb(var(--primary-6));
  background: #e8f3ff;
}

.type-tag {
  font-size: 10px;
  color: #86909c;
  flex-shrink: 0;
}

.chip-actions {
  margin-left: auto;
}

.col-count {
  font-size: 10px;
  color: #86909c;
}

.hint-text {
  font-size: 12px;
  color: #86909c;
  margin: 0 0 8px;
  line-height: 1.5;
}

.detail-col-chip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid #e5e6eb;
  border-radius: 4px;
  margin-bottom: 4px;
  cursor: pointer;
  font-size: 12px;
}

.detail-col-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-col-chip.active {
  border-color: rgb(var(--primary-6));
  background: #e8f3ff;
}

@media (max-width: 1400px) {
  .form-designer {
    grid-template-columns: 220px 1fr minmax(400px, 480px);
  }

  .props-grid.cols-3 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1100px) {
  .form-designer {
    grid-template-columns: 200px 1fr 360px;
  }

  .palette-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .props-grid.cols-3 {
    grid-template-columns: 1fr;
  }
}
</style>
