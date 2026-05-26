import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import { buildRoutes } from './config/routeComponents'
import App from './App.vue'
import 'katex/dist/katex.min.css'
import './styles/main.css'

// 在 Router 安装之前恢复动态路由，避免 "No match found" 警告
try {
  const saved = localStorage.getItem('menus')
  if (saved) {
    const menus = JSON.parse(saved)
    if (menus?.length) {
      const routes = buildRoutes(menus)
      routes.forEach(r => router.addRoute('Root', r))
    }
  }
} catch { /* ignore */ }

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
