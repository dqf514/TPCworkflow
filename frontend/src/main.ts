import { createApp } from 'vue'
import ArcoVue from '@arco-design/web-vue'
import '@arco-design/web-vue/dist/arco.css'
import App from './App.vue'
import router from './router'
import { applyLocalBundleMessages, i18n, loadLocaleMessages } from './plugins/i18n'
import { pinia } from './stores'
import './styles/main.css'
import './styles/form-fill.css'
import './styles/print.css'
import { isEmbedDesktopActive, markEmbedDesktopSession, syncEmbedDesktopDocumentClass } from './utils/embedDesktop'
import { installA11yDomEnhancements } from './utils/a11yDom'
import { initTheme } from './composables/useTheme'

async function bootstrap() {
  initTheme()
  if (isEmbedDesktopActive()) {
    markEmbedDesktopSession()
    syncEmbedDesktopDocumentClass(true)
  }
  // 隐私模式下 localStorage 可能抛错，取不到语言就用默认中文
  let saved = 'zh-CN'
  try {
    saved = localStorage.getItem('locale') || 'zh-CN'
  } catch (e) {
    console.warn('[main] read locale failed', e)
  }
  // 词典加载失败不能白屏：退回本地兜底包继续启动
  try {
    await loadLocaleMessages(saved)
  } catch (e) {
    console.warn('[main] load locale messages failed', e)
    applyLocalBundleMessages(saved)
  }
  const app = createApp(App)
  app.use(pinia)
  app.use(router)
  app.use(i18n)
  app.use(ArcoVue)
  app.mount('#app')
  // 补齐 label ↔ 控件 的程序化关联与表格表头语义（Arco 2.57 不提供）
  installA11yDomEnhancements()
}

bootstrap()
