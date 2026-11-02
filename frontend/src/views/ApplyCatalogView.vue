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

    <div v-if="!searchQ && (favItems.length || recentItems.length)" class="catalog-shortcuts">
      <section v-if="favItems.length" class="catalog-shortcut-block">
        <span class="catalog-shortcut-label">{{ labels.favorite }}</span>
        <div class="catalog-chips">
          <button
            v-for="item in favItems"
            :key="`fav-${itemKey(item)}`"
            type="button"
            class="catalog-chip"
            @click="openProcess(item)"
          >
            <ProcessIcon :icon="item.icon" :size="22" />
            <span>{{ item.form_name }}</span>
          </button>
        </div>
      </section>

      <section v-if="recentItems.length" class="catalog-shortcut-block">
        <span class="catalog-shortcut-label">{{ labels.recent }}</span>
        <div class="catalog-chips">
          <button
            v-for="item in recentItems"
            :key="`recent-${itemKey(item)}`"
            type="button"
            class="catalog-chip"
            @click="openProcess(item)"
          >
            <ProcessIcon :icon="item.icon" :size="22" />
            <span>{{ item.form_name }}</span>
          </button>
        </div>
      </section>
    </div>

    <div v-if="loading" class="catalog-skeleton" aria-hidden="true">
      <section v-for="n in 2" :key="`catalog-sk-${n}`" class="sector-block">
        <div class="sector-head">
          <span class="skeleton catalog-sk-sector" />
          <span class="sector-rule" aria-hidden="true" />
        </div>
        <div v-if="viewMode === 'grid'" class="process-grid">
          <div v-for="m in 4" :key="`catalog-sk-card-${n}-${m}`" class="process-card process-card--skeleton">
            <span class="skeleton catalog-sk-icon" />
            <span class="skeleton catalog-sk-line" />
            <span class="skeleton catalog-sk-line catalog-sk-line--short" />
          </div>
        </div>
        <div v-else class="process-list">
          <div v-for="m in 3" :key="`catalog-sk-row-${n}-${m}`" class="process-row process-row--skeleton">
            <span class="skeleton catalog-sk-icon catalog-sk-icon--sm" />
            <span class="catalog-sk-lines">
              <span class="skeleton catalog-sk-line" />
              <span class="skeleton catalog-sk-line catalog-sk-line--short" />
            </span>
          </div>
        </div>
      </section>
    </div>
    <template v-else-if="filteredGroups.length">
        <section v-for="group in filteredGroups" :key="group.sector_id ?? 'other'" class="sector-block">
          <div class="sector-head">
            <h2 class="sector-title">{{ group.sector_name }}</h2>
            <span class="sector-count">{{ group.items.length }}</span>
            <span class="sector-rule" aria-hidden="true" />
          </div>

          <div v-if="viewMode === 'grid'" class="process-grid">
            <div
              v-for="item in group.items"
              :key="`${item.form_key}-${item.workflow_definition_id}`"
              class="process-card"
            >
              <button type="button" class="process-card-main" @click="openProcess(item)">
                <ProcessIcon :icon="item.icon" :size="48" />
                <span class="process-card-name">{{ item.form_name }}</span>
                <span v-if="item.description" class="process-card-desc">{{ item.description }}</span>
              </button>
              <button
                type="button"
                class="process-star"
                :class="{ 'is-active': isFavorite(item) }"
                :title="isFavorite(item) ? labels.unfavorite : labels.favorite"
                :aria-pressed="isFavorite(item)"
                @click.stop="toggleFavorite(item)"
              >
                <icon-star-fill v-if="isFavorite(item)" />
                <icon-star v-else />
              </button>
            </div>
          </div>

          <div v-else class="process-list">
            <div
              v-for="item in group.items"
              :key="`${item.form_key}-${item.workflow_definition_id}`"
              class="process-row"
            >
              <button type="button" class="process-row-main" @click="openProcess(item)">
                <ProcessIcon :icon="item.icon" :size="36" />
                <span class="process-row-body">
                  <span class="process-row-name">{{ item.form_name }}</span>
                  <span v-if="item.description" class="process-row-desc">{{ item.description }}</span>
                </span>
                <icon-right class="process-row-arrow" />
              </button>
              <button
                type="button"
                class="process-star process-star--row"
                :class="{ 'is-active': isFavorite(item) }"
                :title="isFavorite(item) ? labels.unfavorite : labels.favorite"
                :aria-pressed="isFavorite(item)"
                @click.stop="toggleFavorite(item)"
              >
                <icon-star-fill v-if="isFavorite(item)" />
                <icon-star v-else />
              </button>
            </div>
          </div>
        </section>
      </template>
    <a-empty v-if="!loading && !filteredGroups.length" :description="t('apply.catalog_empty')" />
  </PageChrome>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { routerPushWithEmbed } from '@/utils/embedDesktop'
import {
  IconApps,
  IconList,
  IconRight,
  IconStar,
  IconStarFill,
} from '@arco-design/web-vue/es/icon'
import { api, type ApiResponse } from '@/api/client'
import PageChrome from '@/components/layout/PageChrome.vue'
import ProcessIcon from '@/components/apply/ProcessIcon.vue'

const VIEW_KEY = 'tpc_apply_catalog_view'
const RECENT_KEY = 'tpc_apply_catalog_recent'
const FAV_KEY = 'tpc_apply_catalog_favorites'

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

const { t, locale } = useI18n()
const router = useRouter()
const loading = ref(false)
const groups = ref<CatalogGroup[]>([])
const searchQ = ref('')
const viewMode = ref<'grid' | 'list'>(
  (localStorage.getItem(VIEW_KEY) as 'grid' | 'list') || 'grid',
)

const labels = computed(() => {
  const zh = locale.value.startsWith('zh')
  return {
    favorite: zh ? '常用' : 'Favorites',
    unfavorite: zh ? '取消常用' : 'Remove favorite',
    recent: zh ? '最近使用' : 'Recently used',
  }
})

function readKeys(key: string): string[] {
  try {
    const raw = JSON.parse(localStorage.getItem(key) || '[]')
    return Array.isArray(raw) ? raw.filter((x): x is string => typeof x === 'string') : []
  } catch {
    return []
  }
}

const recentKeys = ref<string[]>(readKeys(RECENT_KEY))
const favoriteKeys = ref<string[]>(readKeys(FAV_KEY))

watch(viewMode, (v) => {
  localStorage.setItem(VIEW_KEY, v)
})

const itemKey = (item: CatalogItem) => `${item.form_key}::${item.workflow_definition_id}`

const allItems = computed(() => groups.value.flatMap((g) => g.items))

const itemsByKey = computed(() => {
  const map = new Map<string, CatalogItem>()
  allItems.value.forEach((item) => map.set(itemKey(item), item))
  return map
})

const favItems = computed(() =>
  favoriteKeys.value
    .map((key) => itemsByKey.value.get(key))
    .filter((item): item is CatalogItem => Boolean(item))
    .slice(0, 6),
)

const recentItems = computed(() =>
  recentKeys.value
    .filter((key) => !favoriteKeys.value.includes(key))
    .map((key) => itemsByKey.value.get(key))
    .filter((item): item is CatalogItem => Boolean(item))
    .slice(0, 5),
)

function isFavorite(item: CatalogItem) {
  return favoriteKeys.value.includes(itemKey(item))
}

function toggleFavorite(item: CatalogItem) {
  const key = itemKey(item)
  favoriteKeys.value = favoriteKeys.value.includes(key)
    ? favoriteKeys.value.filter((k) => k !== key)
    : [key, ...favoriteKeys.value].slice(0, 30)
  localStorage.setItem(FAV_KEY, JSON.stringify(favoriteKeys.value))
}

function rememberRecent(item: CatalogItem) {
  const key = itemKey(item)
  recentKeys.value = [key, ...recentKeys.value.filter((k) => k !== key)].slice(0, 10)
  localStorage.setItem(RECENT_KEY, JSON.stringify(recentKeys.value))
}

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
  rememberRecent(item)
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
  padding-bottom: 4rem;
}

.catalog-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--app-space-12);
  margin-bottom: var(--app-space-16);
}

.catalog-search {
  flex: 1;
  min-width: 200px;
  max-width: 360px;
}

.catalog-skeleton {
  pointer-events: none;
}

.catalog-sk-sector {
  width: 96px;
  height: 15px;
}

.process-card--skeleton {
  flex-direction: column;
  align-items: center;
  gap: var(--app-space-10);
  padding: 22px var(--app-space-14) var(--app-space-18);
}

.catalog-sk-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
}

.catalog-sk-line {
  width: 70%;
  height: 12px;
}

.catalog-sk-line--short {
  width: 52%;
  height: 10px;
}

.process-row--skeleton {
  gap: var(--app-space-10);
  padding: var(--app-space-12) var(--app-space-14);
}

.catalog-sk-icon--sm {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
}

.catalog-sk-lines {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: var(--app-space-6);
}

.catalog-sk-lines .catalog-sk-line {
  width: 46%;
}

.catalog-sk-lines .catalog-sk-line--short {
  width: 30%;
}

.catalog-shortcuts {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-10);
  margin-bottom: var(--app-space-24);
  padding: var(--app-space-12) var(--app-space-14);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
}

.catalog-shortcut-block {
  display: flex;
  align-items: flex-start;
  gap: var(--app-space-14);
}

.catalog-shortcut-label {
  flex-shrink: 0;
  padding-top: var(--app-space-4);
  font-size: var(--app-font-xs);
  font-weight: 500;
  color: var(--text-tertiary);
}

.catalog-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--app-space-6);
  min-width: 0;
}

.catalog-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--app-space-8);
  max-width: 220px;
  padding: var(--app-space-4) var(--app-space-10) var(--app-space-4) var(--app-space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  background: var(--surface);
  font-size: var(--app-font-xs);
  font-weight: 500;
  color: var(--text);
  cursor: pointer;
  transition:
    border-color var(--dur-fast) var(--ease-out),
    background-color var(--dur-fast) var(--ease-out);
}

.catalog-chip:hover {
  border-color: var(--brand-border);
  background: var(--brand-softer);
}

.catalog-chip span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sector-block {
  margin-bottom: var(--app-space-24);
}

.sector-head {
  display: flex;
  align-items: center;
  gap: var(--app-space-8);
  margin-bottom: var(--app-space-12);
}

.sector-title {
  margin: 0;
  font-size: var(--app-font-md);
  font-weight: 600;
  color: var(--text);
}

.sector-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 var(--app-space-4);
  border-radius: var(--radius-pill);
  background: var(--surface-muted);
  color: var(--text-tertiary);
  font-size: var(--app-font-10);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.sector-rule {
  flex: 1;
  height: 1px;
  background: var(--divider);
}

.process-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: var(--app-space-10);
}

.process-card {
  position: relative;
  display: flex;
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  transition:
    border-color var(--dur-base) var(--ease-out),
    box-shadow var(--dur-base) var(--ease-out),
    transform var(--dur-base) var(--ease-out);
}

.process-card:hover {
  border-color: var(--brand-border);
  box-shadow: var(--shadow-sm);
  transform: translateY(-2px);
}

.process-card-main {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--app-space-8);
  min-height: 134px;
  padding: var(--app-space-18) var(--app-space-14) var(--app-space-14);
  border: none;
  border-radius: var(--radius-lg);
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.process-card-name {
  font-size: var(--app-font-sm);
  font-weight: 500;
  color: var(--text);
  line-height: 1.35;
}

.process-card-desc {
  display: -webkit-box;
  overflow: hidden;
  font-size: var(--app-font-2xs);
  color: var(--text-tertiary);
  line-height: 1.35;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.process-star {
  position: absolute;
  top: 8px;
  right: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-disabled);
  font-size: var(--app-font-md);
  cursor: pointer;
  opacity: 0;
  transition:
    opacity var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out),
    background-color var(--dur-fast) var(--ease-out);
}

.process-card:hover .process-star,
.process-card:focus-within .process-star,
.process-star.is-active {
  opacity: 1;
}

.process-star:hover {
  background: var(--surface-muted);
  color: var(--warning);
}

.process-star.is-active {
  color: var(--warning);
}

.process-list {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-6);
}

.process-row {
  display: flex;
  align-items: center;
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  transition:
    border-color var(--dur-fast) var(--ease-out),
    background-color var(--dur-fast) var(--ease-out);
}

.process-row:hover {
  border-color: var(--brand-border);
  background: var(--brand-softer);
}

.process-row-main {
  display: flex;
  flex: 1;
  min-width: 0;
  align-items: center;
  gap: var(--app-space-12);
  padding: 11px var(--app-space-12);
  border: none;
  border-radius: var(--radius-lg);
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.process-row-body {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: var(--app-space-2);
}

.process-row-name {
  font-size: var(--app-font-md);
  font-weight: 500;
  color: var(--text);
}

.process-row-desc {
  overflow: hidden;
  font-size: var(--app-font-xs);
  color: var(--text-tertiary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.process-row-arrow {
  flex-shrink: 0;
  color: var(--text-disabled);
  font-size: var(--app-font-xs);
}

.process-star--row {
  position: static;
  margin-right: var(--app-space-8);
  opacity: 0;
}

.process-row:hover .process-star--row,
.process-row:focus-within .process-star--row,
.process-star--row.is-active {
  opacity: 1;
}

@media (max-width: 640px) {
  .process-grid {
    grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  }

  .catalog-shortcut-block {
    flex-direction: column;
    gap: var(--app-space-6);
  }

  .catalog-shortcut-label {
    padding-top: 0;
  }
}
</style>
