<template>
  <div class="date-range-field" :class="{ 'is-readonly': readonly, 'is-half': halfDay }">
    <div class="date-range-row">
      <div class="date-range-side">
        <a-date-picker
          :model-value="start"
          value-format="YYYY-MM-DD"
          class="date-range-picker"
          :disabled="readonly"
          :placeholder="t('apply.date_start')"
          @update:model-value="onStart"
        />
        <a-radio-group
          v-if="halfDay"
          :model-value="startHalf"
          type="button"
          size="small"
          class="date-range-half"
          :disabled="readonly"
          @update:model-value="onStartHalf"
        >
          <a-radio value="am">{{ t('apply.half_am') }}</a-radio>
          <a-radio value="pm">{{ t('apply.half_pm') }}</a-radio>
        </a-radio-group>
      </div>
      <span class="date-range-sep">{{ t('apply.date_range_to') }}</span>
      <div class="date-range-side">
        <a-date-picker
          :model-value="end"
          value-format="YYYY-MM-DD"
          class="date-range-picker"
          :disabled="readonly"
          :placeholder="t('apply.date_end')"
          @update:model-value="onEnd"
        />
        <a-radio-group
          v-if="halfDay"
          :model-value="endHalf"
          type="button"
          size="small"
          class="date-range-half"
          :disabled="readonly"
          @update:model-value="onEndHalf"
        >
          <a-radio value="am">{{ t('apply.half_am') }}</a-radio>
          <a-radio value="pm">{{ t('apply.half_pm') }}</a-radio>
        </a-radio-group>
      </div>
    </div>
    <div v-if="days != null" class="date-range-days">
      {{ daysHint }}
    </div>
    <div v-else-if="invalid" class="date-range-error">
      {{ t('apply.date_range_invalid') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  buildDateRangeValue,
  countSkippedDays,
  parseDateRange,
  type HalfDay,
} from '@/utils/dateRangeValue'

const props = withDefaults(
  defineProps<{
    modelValue?: unknown
    halfDay?: boolean
    countWorkdays?: boolean
    offDays?: string[]
    makeupWorkdays?: string[]
    regionName?: string
    readonly?: boolean
  }>(),
  {
    halfDay: false,
    countWorkdays: false,
    offDays: () => [],
    makeupWorkdays: () => [],
    regionName: '',
    readonly: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
}>()

const { t } = useI18n()

const parsed = computed(() => parseDateRange(props.modelValue))
const start = computed(() => parsed.value?.start || '')
const end = computed(() => parsed.value?.end || '')
const startHalf = computed<HalfDay>(() => parsed.value?.startHalf || 'am')
const endHalf = computed<HalfDay>(() => parsed.value?.endHalf || 'pm')

function asYmdList(raw: unknown): string[] {
  if (Array.isArray(raw)) return raw.map(String)
  if (raw && typeof raw === 'object' && Array.isArray((raw as { value?: unknown }).value)) {
    return ((raw as { value: unknown[] }).value).map(String)
  }
  return []
}

const offDaysList = computed(() => asYmdList(props.offDays))
const makeupWorkdaysList = computed(() => asYmdList(props.makeupWorkdays))

const workdayOpts = computed(() => ({
  countWorkdays: props.countWorkdays,
  offDays: offDaysList.value,
  makeupWorkdays: makeupWorkdaysList.value,
}))

const built = computed(() => {
  if (!start.value || !end.value) return null
  return buildDateRangeValue(start.value, end.value, {
    halfDay: props.halfDay,
    startHalf: startHalf.value,
    endHalf: endHalf.value,
    ...workdayOpts.value,
  })
})

const days = computed(() => built.value?.days ?? null)
const invalid = computed(() => !!(start.value && end.value && built.value == null))
const skipped = computed(() =>
  props.countWorkdays && start.value && end.value
    ? countSkippedDays(start.value, end.value, workdayOpts.value)
    : 0,
)

const daysHint = computed(() => {
  if (days.value == null) return ''
  if (props.countWorkdays && skipped.value > 0) {
    return t('apply.date_range_days_work', {
      n: days.value,
      skip: skipped.value,
      region: props.regionName || t('apply.holiday_region_default'),
    })
  }
  if (props.countWorkdays && days.value === 0) {
    return t('apply.date_range_days_zero')
  }
  return t('apply.date_range_days', { n: days.value })
})

function emitRange(nextStart: string, nextEnd: string, nextStartHalf: HalfDay, nextEndHalf: HalfDay) {
  if (!nextStart && !nextEnd) {
    emit('update:modelValue', null)
    return
  }
  const value = buildDateRangeValue(nextStart, nextEnd, {
    halfDay: props.halfDay,
    startHalf: nextStartHalf,
    endHalf: nextEndHalf,
    ...workdayOpts.value,
  })
  if (value) {
    emit('update:modelValue', value)
    return
  }
  emit('update:modelValue', {
    start: nextStart,
    end: nextEnd,
    ...(props.halfDay ? { startHalf: nextStartHalf, endHalf: nextEndHalf } : {}),
  })
}

function onStart(v: string | undefined) {
  const next = String(v || '')
  emitRange(next, end.value || next, startHalf.value, endHalf.value)
}

function onEnd(v: string | undefined) {
  const next = String(v || '')
  emitRange(start.value || next, next, startHalf.value, endHalf.value)
}

function onStartHalf(v: string | number | boolean) {
  emitRange(start.value, end.value, (v as HalfDay) || 'am', endHalf.value)
}

function onEndHalf(v: string | number | boolean) {
  emitRange(start.value, end.value, startHalf.value, (v as HalfDay) || 'pm')
}

watch(
  () => [props.countWorkdays, offDaysList.value.join(','), makeupWorkdaysList.value.join(',')].join('|'),
  () => {
    if (props.readonly || !start.value || !end.value) return
    emitRange(start.value, end.value, startHalf.value, endHalf.value)
  },
)
</script>

<style scoped>
.date-range-field {
  width: 100%;
  min-width: 0;
}

.date-range-row {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 8px 10px;
}

.date-range-side {
  flex: 1 1 180px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.date-range-picker {
  width: 100%;
}

.date-range-sep {
  align-self: center;
  color: var(--color-text-3, #86909c);
  font-size: 13px;
  flex: 0 0 auto;
}

.date-range-half {
  width: 100%;
  display: inline-flex;
}

.date-range-half :deep(.arco-radio-button) {
  flex: 1;
  justify-content: center;
  min-height: 36px;
  text-align: center;
}

.date-range-days {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-2, #4e5969);
}

.date-range-error {
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-danger-6, #f53f3f);
}

@media (max-width: 640px) {
  .date-range-sep {
    width: 100%;
    text-align: center;
    line-height: 1;
  }

  .date-range-half :deep(.arco-radio-button) {
    min-height: 44px;
  }
}
</style>
