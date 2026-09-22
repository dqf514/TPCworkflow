<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { FormFieldDef } from '@/types/form'

const props = defineProps<{ field: FormFieldDef }>()
const { t } = useI18n()

function ensureProps() {
  if (!props.field.props) props.field.props = {}
  const p = props.field.props
  if (!Array.isArray(p.formKeys)) p.formKeys = ['auto']
  if (!Array.isArray(p.periodFieldKeys)) p.periodFieldKeys = ['leave_period', 'date_range']
  if (p.leaveTypeFieldKey == null) p.leaveTypeFieldKey = 'leave_type'
  if (p.includeRunning == null) p.includeRunning = false
  if (p.showReason == null) p.showReason = false
  if (p.height == null) p.height = 520
}

ensureProps()

const formKeysText = computed({
  get: () => ((props.field.props?.formKeys as string[]) || []).join(','),
  set: (v: string) => {
    ensureProps()
    props.field.props!.formKeys = v
      .split(/[,，\s]+/)
      .map((x) => x.trim())
      .filter(Boolean)
  },
})

const periodKeysText = computed({
  get: () => ((props.field.props?.periodFieldKeys as string[]) || []).join(','),
  set: (v: string) => {
    ensureProps()
    props.field.props!.periodFieldKeys = v
      .split(/[,，\s]+/)
      .map((x) => x.trim())
      .filter(Boolean)
  },
})

const leaveTypeFieldKey = computed({
  get: () => String(props.field.props?.leaveTypeFieldKey || 'leave_type'),
  set: (v: string) => {
    ensureProps()
    props.field.props!.leaveTypeFieldKey = v.trim() || 'leave_type'
  },
})

const includeRunning = computed({
  get: () => props.field.props?.includeRunning === true,
  set: (v: boolean) => {
    ensureProps()
    props.field.props!.includeRunning = v
  },
})

const showReason = computed({
  get: () => props.field.props?.showReason === true,
  set: (v: boolean) => {
    ensureProps()
    props.field.props!.showReason = v
  },
})

const height = computed({
  get: () => Number(props.field.props?.height ?? 520),
  set: (v: number) => {
    ensureProps()
    props.field.props!.height = Math.min(900, Math.max(320, Number(v) || 520))
  },
})
</script>

<template>
  <div>
    <div class="props-section-title">{{ t('designer.leave_calendar_props') }}</div>
    <p class="hint-text">{{ t('designer.leave_calendar_hint') }}</p>
    <a-form-item :label="t('designer.leave_calendar_form_keys')" class="props-item">
      <a-input v-model="formKeysText" :placeholder="t('designer.leave_calendar_form_keys_ph')" />
    </a-form-item>
    <a-form-item :label="t('designer.leave_calendar_period_keys')" class="props-item">
      <a-input v-model="periodKeysText" :placeholder="t('designer.leave_calendar_period_keys_ph')" />
    </a-form-item>
    <a-form-item :label="t('designer.leave_calendar_type_key')" class="props-item">
      <a-input v-model="leaveTypeFieldKey" />
    </a-form-item>
    <a-form-item :label="t('designer.leave_calendar_height')" class="props-item">
      <a-input-number v-model="height" :min="320" :max="900" :step="20" />
    </a-form-item>
    <div class="props-switches">
      <label class="props-switch-cell">
        <span>{{ t('designer.leave_calendar_include_running') }}</span>
        <a-switch v-model="includeRunning" size="small" />
      </label>
      <label class="props-switch-cell">
        <span>{{ t('designer.leave_calendar_show_reason') }}</span>
        <a-switch v-model="showReason" size="small" />
      </label>
    </div>
  </div>
</template>
