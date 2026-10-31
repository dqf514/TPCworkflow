import { ref } from 'vue'

const pageTitle = ref('')

export function setPageHeaderTitle(value: string) {
  pageTitle.value = value
}

export function usePageHeaderTitle() {
  return pageTitle
}
