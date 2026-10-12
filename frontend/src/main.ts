import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
import router from './router'
import App from './App.vue'
import './assets/main.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
})

const app = createApp(App)

app.use(createPinia())
app.use(VueQueryPlugin, { queryClient })
app.use(router)

// Run startup health check and LLM config after app mounts
router.isReady().then(async () => {
  const { useAppStore } = await import('./stores/useAppStore')
  const appStore = useAppStore()
  await appStore.checkHealth()
  await appStore.loadLLMConfig()
})

app.mount('#app')
