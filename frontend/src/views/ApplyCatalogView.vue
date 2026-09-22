<template>
  <PageChrome :title="t('menu.apply')" :description="t('apply.catalog_desc')" class="apply-catalog-page">
    <div class="catalog-toolbar">
      <a-input-search
        v-model="searchQ"
        :placeholder="t('apply.catalog_search_ph')"
        allow-clear
        class="catalog-search"
      />
      <a-radio-group v-model="viewMode" type="button" size="small">
        <a-radio value="grid">
          <icon-apps />
        </a-radio>
        <a-radio value="list">
          <icon-list />
        </a-radio>
      </a-radio-group>
    </div>

    <a-spin :loading="loading" class="catalog-spin">
      <template v-if="filteredGroups.length">
        <section v-for="group in filteredGroups" :key="group.sector_id ?? 'other'" class="sector-block">
          <h2 class="sector-title">{{ group.sector_name }}</h2>
          <div v-if="viewMode === 'grid'" class="process-grid">
            <button
              v-for="item in group.items"
              :key="`${item.form_key}-${item.workflow_definition_id}`"
              type="button"
              class="process-card"
              @click="openProcess(item)"
            >
              <ProcessIcon :icon="item.icon" :size="56" />
              <span class="process-card-name">{{ item.form_name }}</span>
              <span v-if="item.description" class="process-card-desc">{{ item.description }}</span>
            </button>
          </div>
          <div v-else class="process-list">
            <button
              v-for="item in group.items"
              :key="`${item.form_key}-${item.workflow_definition_id}`"
              type="button"
              class="process-row"
              @click="openProcess(item)"
            >
              <ProcessIcon :icon="item.icon" :size="40" />
              <div class="process-row-body">
                <span class="process-row-name">{{ item.form_name }}</span>
                <span v-if="item.description" class="process-row-desc">{{ item.description }}</span>
              </div>
              <icon-right class="process-row-arrow" />
            </button>
          </div>
        </section>
      </template>
      <a-empty v-else-if="!loading" :description="t('apply.catalog_empty')" />
    </a-spin>
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { routerPushWithEmbed } from '@/utils/embedDesktop'
import { IconApps, IconList, IconRight } from '@arco-design/web-vue/es/icon'
import { api, type ApiResponse } from '@/api/client'
import PageChrome from '@/components/layout/PageChrome.vue'
import ProcessIcon from '@/components/apply/ProcessIcon.vue'

const VIEW_KEY = 'tpc_apply_catalog_view'

interface CatalogItem {
  form_id: number
  form_key: string
  form_name: string
  workflow_definition_id: number
  workflow_name: string
  description?: string
  icon?: string
}

interface CatalogGroup {
  sector_id: number | null
  sector_name: string
  sector_sort_order?: number
  items: CatalogItem[]
}

const { t } = useI18n()
const router = useRouter()
const loading = ref(false)
const groups = ref<CatalogGroup[]>([])
const searchQ = ref('')
const viewMode = ref<'grid' | 'list'>(
  (localStorage.getItem(VIEW_KEY) as 'grid' | 'list') || 'grid',
)

watch(viewMode, (v) => {
  localStorage.setItem(VIEW_KEY, v)
})

const filteredGroups = computed(() => {
  const q = searchQ.value.trim().toLowerCase()
  if (!q) return groups.value
  return groups.value
    .map((g) => ({
      ...g,
      items: g.items.filter(
        (it) =>
          it.form_name.toLowerCase().includes(q) ||
          (it.description || '').toLowerCase().includes(q),
      ),
    }))
    .filter((g) => g.items.length > 0)
})

function openProcess(item: CatalogItem) {
  routerPushWithEmbed(router, {
    name: 'apply-start',
    query: {
      def: String(item.workflow_definition_id),
      key: item.form_key,
      title: item.form_name,
    },
  })
}

async function loadCatalog() {
  loading.value = true
  try {
    const res = await api.get<ApiResponse<CatalogGroup[]>>('/forms/applications-catalog')
    if (res.data.ok) groups.value = res.data.data
  } finally {
    loading.value = false
  }
}

onMounted(loadCatalog)
</script>

<style scoped>
.apply-catalog-page {
  padding-bottom: 5rem;
}

.catalog-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
}

.catalog-search {
  flex: 1;
  min-width: 200px;
  max-width: 420px;
}

.catalog-spin {
  display: block;
  width: 100%;
}

.sector-block {
  margin-bottom: 28px;
}

.sector-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #1f2329);
  margin: 0 0 12px;
  padding-left: 10px;
  border-left: 3px solid var(--brand, #5034ff);
}

.process-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
}

@media (min-width: 640px) {
  .process-grid {
    grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  }
}

.process-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 10px;
  border: 1px solid var(--border, #e5e6eb);
  border-radius: var(--radius-lg, 12px);
  background: #fff;
  cursor: pointer;
  text-align: center;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.12s;
}

.process-card:hover {
  border-color: var(--brand, #5034ff);
  box-shadow: var(--shadow-sm, 0 2px 8px rgba(0, 0, 0, 0.06));
  transform: translateY(-1px);
}

.process-card-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary, #1f2329);
  line-height: 1.35;
}

.process-card-desc {
  font-size: 0.75rem;
  color: var(--text-tertiary, #9699a6);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.process-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.process-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--border, #e5e6eb);
  border-radius: var(--radius-lg, 12px);
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, background 0.15s;
}

.process-row:hover {
  border-color: var(--brand, #5034ff);
  background: rgba(80, 52, 255, 0.03);
}

.process-row-body {
  flex: 1;
  min-width: 0;
}

.process-row-name {
  display: block;
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-primary, #1f2329);
}

.process-row-desc {
  display: block;
  font-size: 0.8125rem;
  color: var(--text-tertiary, #9699a6);
  margin-top: 2px;
}

.process-row-arrow {
  color: var(--text-tertiary, #9699a6);
  flex-shrink: 0;
}
</style>
