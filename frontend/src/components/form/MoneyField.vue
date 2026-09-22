<template>
  <div
    class="money-field"
    :class="{
      'money-field--compact': compact,
      'money-field--inline': inline,
      'money-field--readonly': readonly,
    }"
  >
    <div class="money-grid">
      <div class="money-cell">
        <label class="money-label">币种</label>
        <a-select
          :model-value="state.currency"
          :options="currencyOpts"
          :disabled="readonly"
          allow-search
          size="small"
          placeholder="币种"
          @update:model-value="onCurrency"
        />
      </div>
      <div class="money-cell">
        <label class="money-label">金额</label>
        <a-input-number
          :model-value="state.amount"
          :disabled="readonly"
          :precision="2"
          :min="0"
          class="w-full"
          placeholder="0.00"
          size="small"
          @update:model-value="onAmount"
        />
      </div>
      <div class="money-cell">
        <label class="money-label">兑换率</label>
        <a-input-number
          :model-value="state.exchange_rate"
          :disabled="readonly"
          :precision="6"
          :min="0"
          class="w-full"
          size="small"
          @change="onExchangeRate"
        />
      </div>
      <div class="money-cell money-cell-rmb">
        <label class="money-label">金额（人民币）</label>
        <a-input-number
          :model-value="state.rmb_amount"
          :precision="2"
          disabled
          class="w-full"
          size="small"
        />
      </div>
    </div>
    <p v-if="!readonly" class="money-hint">
      默认采用系统汇率，可手动调整；与系统汇率差异超过 20% 时需确认
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Modal } from '@arco-design/web-vue'
import {
  applyMoneyPatch,
  currencyOptions,
  exchangeRateDeviationRatio,
  exchangeRateExceedsThreshold,
  getRateForCurrency,
  loadExchangeRates,
  normalizeMoneyValue,
  type ExchangeRateRow,
  type MoneyValue,
} from '@/composables/useMoneyField'

const props = withDefaults(
  defineProps<{
    modelValue?: unknown
    readonly?: boolean
    compact?: boolean
    inline?: boolean
  }>(),
  { readonly: false, compact: false, inline: false },
)

const emit = defineEmits<{ 'update:modelValue': [MoneyValue] }>()

const state = reactive<MoneyValue>(normalizeMoneyValue(props.modelValue))
const rates = ref<ExchangeRateRow[]>([])
const systemExchangeRate = ref(getRateForCurrency(state.currency))

const currencyOpts = computed(() => currencyOptions(rates.value))

function syncSystemRate(code: string) {
  systemExchangeRate.value = getRateForCurrency(code)
}

function emitState() {
  emit('update:modelValue', { ...state })
}

function onCurrency(code: string) {
  Object.assign(state, applyMoneyPatch(state, { currency: code }))
  syncSystemRate(code)
  emitState()
}

function onExchangeRate(val: number | undefined) {
  if (props.readonly) return
  const prev = state.exchange_rate
  if (val == null || Number.isNaN(Number(val)) || Number(val) < 0) return

  const nextRate = Number(val)
  if (nextRate === prev) return

  const systemRate = systemExchangeRate.value
  if (exchangeRateExceedsThreshold(nextRate, systemRate)) {
    const deviationPct = (exchangeRateDeviationRatio(nextRate, systemRate) * 100).toFixed(1)
    Modal.confirm({
      title: '确认兑换率',
      content: `您输入的兑换率 ${nextRate} 与系统汇率 ${systemRate} 相差 ${deviationPct}%，超过 20%。确定使用该汇率折算人民币金额吗？`,
      okText: '确定使用',
      cancelText: '取消',
      onOk: () => {
        Object.assign(state, applyMoneyPatch(state, { exchange_rate: nextRate }))
        emitState()
      },
      onCancel: () => {
        Object.assign(state, applyMoneyPatch(state, { exchange_rate: prev }))
        emitState()
      },
    })
    return
  }

  Object.assign(state, applyMoneyPatch(state, { exchange_rate: nextRate }))
  emitState()
}

function onAmount(val: number | undefined) {
  Object.assign(
    state,
    applyMoneyPatch(state, { amount: val == null ? null : Number(val) }),
  )
  emitState()
}

watch(
  () => props.modelValue,
  (v) => {
    Object.assign(state, normalizeMoneyValue(v, state.exchange_rate))
  },
  { deep: true },
)

onMounted(async () => {
  rates.value = await loadExchangeRates()
  const normalized = normalizeMoneyValue(props.modelValue)
  Object.assign(state, applyMoneyPatch(normalized, { currency: normalized.currency }))
  syncSystemRate(state.currency)
})
</script>

<style scoped>
.money-field {
  width: 100%;
}

.money-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.money-field--compact .money-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.money-field--inline .money-grid {
  display: grid;
  grid-template-columns: 112px 88px 64px 80px;
  align-items: center;
  gap: 6px;
}

.money-field--inline .money-cell {
  min-width: 0;
}

.money-field--inline .money-label {
  display: none;
}

.money-field--inline .money-hint {
  display: none;
}

@media (max-width: 640px) {
  .money-grid {
    grid-template-columns: 1fr;
  }

  .money-field--compact .money-grid {
    grid-template-columns: 1fr;
  }

  .money-field--inline .money-grid {
    grid-template-columns: 1fr 1fr;
  }

  .money-field--inline .money-label {
    display: block;
  }
}

.money-label {
  display: block;
  font-size: 13px;
  color: #646a73;
  margin-bottom: 4px;
  font-weight: 500;
}

.money-cell-rmb :deep(.arco-input-number) {
  background: #f5f6f7 !important;
  border-color: #e5e6eb !important;
}

.money-hint {
  margin: 8px 0 0;
  font-size: 13px;
  color: #646a73;
  line-height: 1.5;
}

.money-field--readonly :deep(.arco-input-number-input) {
  text-align: right;
}
</style>
