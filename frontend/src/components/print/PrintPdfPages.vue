<template>
  <div class="wf-print-pdf-pages">
    <div v-if="loading" class="wf-print-pdf-loading">{{ t('print.pdf_loading') }}</div>
    <div v-else-if="error" class="wf-print-pdf-error">{{ error }}</div>
    <div v-else-if="useEmbedFallback" class="wf-print-pdf-embed">
      <object :data="embedUrl" type="application/pdf" class="wf-print-pdf-embed-obj">
        <iframe :src="embedUrl" class="wf-print-pdf-embed-frame" :title="t('print.attachment_badge')" />
      </object>
      <p class="wf-print-pdf-embed-hint">{{ t('print.pdf_embed_hint') }}</p>
    </div>
    <template v-else>
      <img
        v-for="(src, pageIndex) in pages"
        :key="pageIndex"
        :src="src"
        :alt="t('print.pdf_page_alt', { name: name || '', page: pageIndex + 1 })"
        class="wf-print-att-img wf-print-pdf-page"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { encodeUrlPath } from '@/utils/pdfRender'
import { printT } from '@/utils/printI18n'

const props = defineProps<{
  url: string
  name?: string
}>()

const { t } = useI18n()

const loading = ref(true)
const error = ref('')
const pages = ref<string[]>([])
const useEmbedFallback = ref(false)

const embedUrl = computed(() => encodeUrlPath(props.url))

async function loadPdf() {
  loading.value = true
  error.value = ''
  pages.value = []
  useEmbedFallback.value = false
  if (!props.url) {
    error.value = printT('print.pdf_invalid')
    loading.value = false
    return
  }
  try {
    const { renderPdfToImages } = await import('@/utils/pdfRender')
    pages.value = await renderPdfToImages(props.url)
    if (!pages.value.length) error.value = printT('print.pdf_empty')
  } catch (err) {
    console.warn('[PrintPdfPages] pdf.js 渲染失败，回退 embed 预览', err)
    useEmbedFallback.value = true
    error.value = ''
  } finally {
    loading.value = false
  }
}

onMounted(() => void loadPdf())
watch(() => props.url, () => void loadPdf())
</script>
