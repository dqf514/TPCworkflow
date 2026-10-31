import { computed, ref } from 'vue'

type ThemeMode = 'light' | 'dark'

const STORAGE_KEY = 'imc-theme'
const mode = ref<ThemeMode>('light')

function systemPrefersDark() {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
}

function applyTheme(next: ThemeMode, persist = true) {
  mode.value = next
  const root = document.documentElement
  root.dataset.theme = next
  root.style.colorScheme = next
  document.body?.setAttribute('arco-theme', next === 'dark' ? 'dark' : 'light')
  if (!persist) return
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    /* storage unavailable */
  }
}

export function initTheme() {
  let saved: string | null = null
  try {
    saved = localStorage.getItem(STORAGE_KEY)
  } catch {
    saved = null
  }
  const next: ThemeMode = saved === 'dark' || saved === 'light' ? saved : systemPrefersDark() ? 'dark' : 'light'
  applyTheme(next, false)
  if (typeof window !== 'undefined') {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
      let stored: string | null = null
      try {
        stored = localStorage.getItem(STORAGE_KEY)
      } catch {
        stored = null
      }
      if (stored === 'dark' || stored === 'light') return
      applyTheme(event.matches ? 'dark' : 'light')
    })
  }
}

export function useTheme() {
  const isDark = computed(() => mode.value === 'dark')
  function toggleTheme() {
    applyTheme(mode.value === 'dark' ? 'light' : 'dark')
  }
  function setTheme(next: ThemeMode) {
    applyTheme(next)
  }
  return { mode, isDark, toggleTheme, setTheme }
}
