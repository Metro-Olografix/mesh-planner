import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'bootstrap/dist/css/bootstrap.min.css'
import App from './App.vue'
import router from './router'
import { initAuth, hasCustomFavicon } from './auth'

initAuth().then(() => {
  if (hasCustomFavicon()) {
    const link = document.querySelector<HTMLLinkElement>("link[rel='icon']")
      ?? document.createElement('link')
    link.rel = 'icon'
    link.href = '/api/custom/favicon'
    document.head.appendChild(link)
  }

  const app = createApp(App)
  app.use(createPinia())
  app.use(router)
  app.mount('#app')
})
