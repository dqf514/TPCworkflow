<template>
  <div class="formula-designer">
    <div class="props-section-title">{{ t('designer.formula_props') }}</div>
    <p class="hint-text">{{ introText }}</p>

    <div class="formula-toolbar">
      <span class="formula-toolbar-label">{{ t('designer.formula_insert_func') }}</span>
      <a-space wrap :size="4">
        <a-button
          v-for="item in funcSnippets"
          :key="item.label"
          size="mini"
          type="outline"
          @click="insertAtCursor(item.insert)"
        >
          {{ item.label }}
        </a-button>
        <a-button
          v-for="op in operatorSnippets"
          :key="op"
          size="mini"
          type="text"
          @click="insertAtCursor(op)"
        >
          {{ op }}
        </a-button>
      </a-space>
    </div>

    <div class="formula-field">
      <label class="formula-label">{{ t('designer.formula_insert_ref') }}</label>
      <a-select
        v-model="refPick"
        :options="refSelectOpts"
        allow-search
        allow-clear
        :placeholder="refPlaceholder"
        @change="onRefPick"
      />
      <p v-if="!refSelectOpts.length" class="hint-text hint-warn">{{ t('designer.formula_no_refs') }}</p>
    </div>

    <div class="formula-field">
      <label class="formula-label">{{ t('designer.formula_expression') }}</label>
      <a-textarea
        ref="exprRef"
        v-model="expression"
        :auto-size="{ minRows: 3, maxRows: 8 }"
        :placeholder="t('designer.formula_expression_ph')"
        class="formula-expr"
      />
    </div>

    <div class="props-grid cols-2 formula-meta">
      <div class="formula-field">
        <label class="formula-label">{{ t('designer.formula_precision') }}</label>
        <a-input-number v-model="precision" :min="0" :max="8" />
      </div>
      <div class="formula-field">
        <label class="formula-label">{{ t('designer.formula_preview_label') }}</label>
        <div class="formula-preview" :class="{ empty: !expression.trim(), error: previewIsError }">
          {{ previewText }}
        </div>
      </div>
    </div>

    <div class="formula-syntax">
      <div class="formula-syntax-title">{{ t('designer.formula_syntax_title') }}</div>
      <ul class="formula-syntax-list">
        <li v-for="(line, idx) in syntaxLines" :key="idx">{{ line }}</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { FormFieldDef, FormSchema } from '@/types/form'
import {
  collectFormulaRefOptions,
  evaluateFormFormula,
  formatFormulaResult,
} from '@/utils/formFormula'

const props = defineProps<{
  field: FormFieldDef
  schema: FormSchema
  /** 明细表 key；传入时按明细行公式模式处理引用与预览 */
  detailKey?: string
}>()

const { t, locale } = useI18n()

const exprRef = ref<{ $el?: HTMLElement } | null>(null)
const refPick = ref<string | undefined>()

const detailRowMode = computed(() => !!props.detailKey)

const introText = computed(() =>
  detailRowMode.value ? t('designer.formula_detail_intro') : t('designer.formula_intro'),
)

const funcSnippets = [
  { label: 'SUM', insert: 'SUM()' },
  { label: 'AVG', insert: 'AVG()' },
  { label: 'MIN', insert: 'MIN()' },
  { label: 'MAX', insert: 'MAX()' },
  { label: 'ROUND', insert: 'ROUND(, 2)' },
]

const operatorSnippets = ['+', '-', '*', '/', '(', ')']

const syntaxLines = computed(() => {
  if (String(locale.value).startsWith('zh')) {
    if (detailRowMode.value) {
      return [
        '引用本行其他列：$' + '{列key}',
        '四则运算：+ - * / 与括号',
        '示例：$' + '{单价} * $' + '{数量}；ROUND($' + '{金额}, 2)',
      ]
    }
    return [
      '主表字段：$' + '{字段key}',
      '明细列汇总：$' + '{明细key.列key}（自动按行求和）',
      '函数：SUM / AVG / MIN / MAX / ROUND',
      '示例：SUM($' + '{expense_items.amount})；$' + '{price} * $' + '{qty}',
    ]
  }
  if (detailRowMode.value) {
    return [
      'Sibling columns: $' + '{colKey}',
      'Operators: + - * / and parentheses',
      'Example: $' + '{unit_price} * $' + '{qty}; ROUND($' + '{amount}, 2)',
    ]
  }
  return [
    'Main field: $' + '{fieldKey}',
    'Detail column sum: $' + '{detailKey.colKey}',
    'Functions: SUM / AVG / MIN / MAX / ROUND',
    'Example: SUM($' + '{items.amount}); $' + '{price} * $' + '{qty}',
  ]
})

function ensureProps() {
  if (!props.field.props) props.field.props = {}
  if (props.field.props.expression === undefined) props.field.props.expression = ''
  if (props.field.props.precision === undefined) props.field.props.precision = 2
  props.field.readonly = true
}

watch(() => props.field, ensureProps, { immediate: true })

const expression = computed({
  get: () => String(props.field.props?.expression || ''),
  set: (v: string) => {
    ensureProps()
    props.field.props!.expression = v
  },
})

const precision = computed({
  get: () => Number(props.field.props?.precision ?? 2),
  set: (v: number) => {
    ensureProps()
    props.field.props!.precision = v
  },
})

const flatRefOpts = computed(() =>
  collectFormulaRefOptions(props.schema, {
    excludeKey: detailRowMode.value ? undefined : props.field.key,
    detailOnly: detailRowMode.value,
    detailKey: props.detailKey,
  }),
)

const refSelectOpts = computed(() => {
  const flat = flatRefOpts.value.map((o) => ({
    label: o.label,
    value: o.insert,
  }))
  if (detailRowMode.value || flat.length <= 8) return flat

  const main = flat.filter((o) => !String(o.value).includes('.'))
  const detail = flat.filter((o) => String(o.value).includes('.'))
  const groups: { label: string; options: { label: string; value: string }[] }[] = []
  if (main.length) groups.push({ label: t('designer.formula_ref_main'), options: main })
  if (detail.length) groups.push({ label: t('designer.formula_ref_detail'), options: detail })
  return groups.length ? groups : flat
})

const refPlaceholder = computed(() =>
  flatRefOpts.value.length ? t('designer.formula_insert_ref_ph') : t('designer.formula_no_refs'),
)

function buildSampleContext(expr: string) {
  const model: Record<string, unknown> = {}
  let detailRow: Record<string, unknown> = {}
  const tokens = expr.match(/\$\{([^}]+)\}/g) || []
  for (const token of tokens) {
    const ref = token.slice(2, -1).trim()
    if (!ref) continue
    if (ref.includes('.')) {
      const [detailKey, colKey] = ref.split('.', 2)
      if (!model[detailKey]) {
        detailRow = { [colKey]: 1 }
        model[detailKey] = [detailRow]
      } else if (Array.isArray(model[detailKey]) && (model[detailKey] as Record<string, unknown>[])[0]) {
        ;((model[detailKey] as Record<string, unknown>[])[0] as Record<string, unknown>)[colKey] = 1
        detailRow = (model[detailKey] as Record<string, unknown>[])[0] as Record<string, unknown>
      }
      continue
    }
    if (detailRowMode.value) {
      detailRow[ref] = 1
      if (props.detailKey) {
        if (!model[props.detailKey]) model[props.detailKey] = [detailRow]
        else if (Array.isArray(model[props.detailKey])) {
          ;((model[props.detailKey] as Record<string, unknown>[])[0] as Record<string, unknown>)[ref] = 1
        }
      }
    } else {
      model[ref] = 1
    }
  }
  if (detailRowMode.value && props.detailKey && !model[props.detailKey]) {
    model[props.detailKey] = [detailRow]
  }
  return { model, detailRow }
}

const previewIsError = computed(() => {
  const expr = expression.value.trim()
  if (!expr) return false
  const { model, detailRow } = buildSampleContext(expr)
  const val = evaluateFormFormula(expr, {
    model,
    schema: props.schema,
    detailRow: detailRowMode.value ? detailRow : undefined,
    detailKey: props.detailKey,
  })
  return val == null
})

const previewText = computed(() => {
  const expr = expression.value.trim()
  if (!expr) return t('designer.formula_preview_empty')
  const { model, detailRow } = buildSampleContext(expr)
  const val = evaluateFormFormula(expr, {
    model,
    schema: props.schema,
    detailRow: detailRowMode.value ? detailRow : undefined,
    detailKey: props.detailKey,
  })
  if (val == null) return t('designer.formula_preview_error')
  const formatted = formatFormulaResult(val, props.field)
  return t('designer.formula_preview_sample', { value: String(formatted) })
})

function getTextarea(): HTMLTextAreaElement | null {
  const root = exprRef.value?.$el as HTMLElement | undefined
  if (!root) return null
  if (root.tagName === 'TEXTAREA') return root as HTMLTextAreaElement
  return root.querySelector('textarea')
}

function insertAtCursor(text: string) {
  const current = expression.value
  const ta = getTextarea()
  if (!ta) {
    expression.value = current + text
    return
  }
  const start = ta.selectionStart ?? current.length
  const end = ta.selectionEnd ?? start
  expression.value = current.slice(0, start) + text + current.slice(end)
  nextTick(() => {
    ta.focus()
    let cursor = start + text.length
    if (text.endsWith('()')) cursor = start + text.length - 1
    else if (text.startsWith('ROUND(')) cursor = start + 'ROUND('.length
    ta.setSelectionRange(cursor, cursor)
  })
}

function onRefPick(value: string | number | boolean | Record<string, unknown> | undefined) {
  const token = String(value || '')
  if (token) insertAtCursor(token)
  nextTick(() => {
    refPick.value = undefined
  })
}
</script>

<style scoped>
.formula-designer {
  margin-top: 4px;
}

.formula-toolbar {
  margin-bottom: 10px;
}

.formula-toolbar-label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--color-text-3);
}

.formula-field {
  margin-bottom: 10px;
}

.formula-label {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--color-text-2);
}

.formula-expr :deep(textarea) {
  font-family: 'Consolas', 'Ubuntu Mono', 'Courier New', monospace;
  font-size: 13px;
}

.formula-meta {
  margin-top: 4px;
}

.formula-preview {
  min-height: 32px;
  padding: 6px 10px;
  border-radius: 4px;
  background: var(--color-fill-2);
  font-family: 'Consolas', 'Ubuntu Mono', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.4;
  word-break: break-all;
}

.formula-preview.empty {
  color: var(--color-text-3);
}

.formula-preview.error {
  color: rgb(var(--danger-6));
  background: rgba(var(--danger-6), 0.08);
}

.formula-syntax {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 4px;
  background: var(--color-fill-1);
  border: 1px solid var(--color-border-2);
}

.formula-syntax-title {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-2);
}

.formula-syntax-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text-3);
}

.hint-warn {
  margin-top: 4px;
  color: rgb(var(--warning-6));
}
</style>
