<template>
  <div class="related-form-field">
    <div v-if="selected.length" class="related-list">
      <div v-for="(item, idx) in selected" :key="item.instance_id" class="related-item">
        <div class="related-item-main">
          <span class="related-title">{{ item.title }}</span>
          <span v-if="item.started_at" class="related-meta">{{ formatDateTime(item.started_at) }}</span>
          <a-tag v-if="item.status" size="small">{{ statusLabel(item) }}</a-tag>
        </div>
        <a-space v-if="!readonly">
          <a-button type="text" size="mini" @click="openDetail(item)">查看</a-button>
          <a-button type="text" size="mini" status="danger" @click="removeAt(idx)">移除</a-button>
        </a-space>
        <a-button v-else type="text" size="mini" @click="openDetail(item)">查看</a-button>
      </div>
    </div>
    <p v-else-if="readonly" class="text-gray-400 text-sm">未关联申请单</p>
    <a-button
      v-if="!readonly && canAddMore"
      type="outline"
      long
      class="related-pick-btn"
      :disabled="!allowedKeys.length"
      @click="pickerOpen = true"
    >
      {{ allowedKeys.length ? '选择关联申请单' : '请先在字段属性中配置可关联范围' }}
    </a-button>

    <a-modal
      v-model:visible="pickerOpen"
      title="选择关联申请单"
      :width="560"
      @ok="confirmPick"
      @cancel="pickerOpen = false"
    >
      <a-input-search
        v-model="searchQ"
        placeholder="搜索流程名称"
        allow-clear
        class="mb-3"
      />
      <a-spin :loading="loading">
        <a-radio-group v-if="!multiple" v-model="pickId" direction="vertical" class="w-full">
          <a-radio
            v-for="opt in filteredOptions"
            :key="opt.instance_id"
            :value="opt.instance_id"
            class="related-radio"
          >
            <span>{{ opt.title }}</span>
            <span class="text-xs text-gray-500 ml-2">{{ formatDateTime(opt.started_at) }}</span>
          </a-radio>
        </a-radio-group>
        <a-checkbox-group v-else v-model="pickIds" direction="vertical" class="w-full">
          <a-checkbox
            v-for="opt in filteredOptions"
            :key="opt.instance_id"
            :value="opt.instance_id"
            class="related-radio"
          >
            <span>{{ opt.title }}</span>
            <span class="text-xs text-gray-500 ml-2">{{ formatDateTime(opt.started_at) }}</span>
          </a-checkbox>
        </a-checkbox-group>
        <a-empty v-if="!loading && !filteredOptions.length" description="没有可关联的已提交申请" />
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { api, type ApiResponse } from '@/api/client'
import { formatInstanceStatus } from '@/composables/useWorkflowLabels'
import type { RelatedFormValue } from '@/types/form'
import { formatDateTime } from '@/utils/dateTime'

const { t } = useI18n()

const props = withDefaults(
  defineProps<{
    modelValue?: RelatedFormValue | RelatedFormValue[] | null
    relatedFormKeys?: string[]
    multiple?: boolean
    readonly?: boolean
  }>(),
  { relatedFormKeys: () => [], multiple: false, readonly: false },
)

const emit = defineEmits<{ 'update:modelValue': [RelatedFormValue | RelatedFormValue[] | null] }>()

const router = useRouter()
const pickerOpen = ref(false)
const loading = ref(false)
const searchQ = ref('')
const options = ref<RelatedFormValue[]>([])
const pickId = ref<number>()
const pickIds = ref<number[]>([])

const allowedKeys = computed(() => props.relatedFormKeys?.filter(Boolean) || [])

const selected = computed((): RelatedFormValue[] => {
  const v = props.modelValue
  if (!v) return []
  if (Array.isArray(v)) return v
  return [v]
})

const canAddMore = computed(() => props.multiple || selected.value.length === 0)

const filteredOptions = computed(() => {
  const q = searchQ.value.trim().toLowerCase()
  const picked = new Set(selected.value.map((x) => x.instance_id))
  return options.value.filter((o) => {
    if (picked.has(o.instance_id)) return false
    if (!q) return true
    return (o.title || '').toLowerCase().includes(q)
  })
})

function statusLabel(item: RelatedFormValue) {
  return formatInstanceStatus(item.status, t, item.current_node_label)
}

async function loadOptions() {
  if (!allowedKeys.value.length) {
    options.value = []
    return
  }
  loading.value = true
  try {
    const res = await api.get<ApiResponse<RelatedFormValue[]>>('/forms/linkable-instances', {
      params: { form_keys: allowedKeys.value.join(',') },
    })
    if (res.data.ok) options.value = res.data.data
  } finally {
    loading.value = false
  }
}

watch(pickerOpen, (v) => {
  if (v) {
    pickId.value = undefined
    pickIds.value = []
    searchQ.value = ''
    loadOptions()
  }
})

function confirmPick() {
  const toAdd: RelatedFormValue[] = []
  if (props.multiple) {
    for (const id of pickIds.value) {
      const o = options.value.find((x) => x.instance_id === id)
      if (o) toAdd.push(o)
    }
    emit('update:modelValue', [...selected.value, ...toAdd])
  } else {
    const o = options.value.find((x) => x.instance_id === pickId.value)
    emit('update:modelValue', o || null)
  }
  pickerOpen.value = false
}

function removeAt(idx: number) {
  if (props.multiple) {
    const next = [...selected.value]
    next.splice(idx, 1)
    emit('update:modelValue', next.length ? next : null)
  } else {
    emit('update:modelValue', null)
  }
}

function openDetail(item: RelatedFormValue) {
  const ref = item.public_uuid
  if (!ref) return
  const r = router.resolve({ name: 'instance-detail', params: { uuid: ref } })
  window.open(r.href, '_blank')
}
</script>

<style scoped>
.related-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.related-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--border, #e6e9ef);
  border-radius: var(--radius-sm, 8px);
  background: var(--surface, #fff);
}

.related-item-main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.related-title {
  font-weight: 500;
  color: var(--text, #323338);
}

.related-meta {
  font-size: 0.75rem;
  color: var(--text-tertiary, #9699a6);
}

.related-pick-btn {
  margin-top: 4px;
}

.related-radio {
  width: 100%;
  margin-bottom: 8px;
}
</style>
