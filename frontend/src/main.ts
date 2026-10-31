import { createApp } from 'vue'
import ArcoVue from '@arco-design/web-vue'
import '@arco-design/web-vue/dist/arco.css'
import App from './App.vue'
import router from './router'
import { i18n, loadLocaleMessages } from './plugins/i18n'
import { pinia } from './stores'
import './styles/main.css'
import './styles/form-fill.css'
import './styles/print.css'
import { isEmbedDesktopActive, markEmbedDesktopSession, syncEmbedDesktopDocumentClass } from './utils/embedDesktop'
import { initTheme } from './composables/useTheme'

async function bootstrap() {
  initTheme()
  if (isEmbedDesktopActive()) {
    markEmbedDesktopSession()
    syncEmbedDesktopDocumentClass(true)
  }
  const saved = localStorage.getItem('locale') || 'zh-CN'
  await loadLocaleMessages(saved)
  const app = createApp(App)
  app.use(pinia)
  app.use(router)
  app.use(i18n)
  app.use(ArcoVue)
  app.mount('#app')
}

bootstrap()
