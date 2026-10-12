import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/pages/DashboardPage.vue'),
    },
    {
      path: '/projects/:id',
      name: 'project',
      component: () => import('@/pages/ProjectPage.vue'),
      redirect: (to) => ({ name: 'project-graph', params: to.params }),
      children: [
        {
          path: 'graph',
          name: 'project-graph',
          component: () => import('@/pages/GraphPage.vue'),
        },
        {
          path: 'files',
          name: 'project-files',
          component: () => import('@/pages/FilesPage.vue'),
        },
        {
          path: 'files/:filepath+',
          name: 'project-file-view',
          component: () => import('@/pages/FilesPage.vue'),
        },
        {
          path: 'analysis',
          name: 'project-analysis',
          component: () => import('@/pages/AnalysisPage.vue'),
        },
      ],
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/pages/SettingsPage.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

export default router
