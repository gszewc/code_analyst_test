import { createPinia } from 'pinia'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { createRouter, createMemoryHistory } from 'vue-router'

export function createProjectRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: { template: '<div>dashboard</div>' } },
      {
        path: '/projects/:id',
        name: 'project',
        component: { template: '<router-view />' },
        children: [
          { path: 'graph', name: 'project-graph', component: { template: '<div>graph</div>' } },
          { path: 'files', name: 'project-files', component: { template: '<div>files</div>' } },
          { path: 'analysis', name: 'project-analysis', component: { template: '<div>analysis</div>' } },
          { path: 'files/:filepath+', name: 'project-file-view', component: { template: '<div>file</div>' } },
        ],
      },
    ],
  })
}

export function createProjectPagePlugins() {
  const pinia = createPinia()
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return {
    pinia,
    queryClient,
    vueQueryPlugin: [VueQueryPlugin, { queryClient }] as const,
  }
}
