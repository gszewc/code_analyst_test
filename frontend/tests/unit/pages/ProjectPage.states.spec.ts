import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import ProjectPage from '@/pages/ProjectPage.vue'

const queryState = {
  data: ref<{ name: string } | undefined>(undefined),
  isLoading: ref(false),
  isError: ref(false),
}

vi.mock('@tanstack/vue-query', () => ({
  useQuery: vi.fn(() => queryState),
}))

vi.mock('@/layouts/AppLayout.vue', () => ({
  default: {
    template: '<div><slot /></div>',
  },
}))

async function mountPage() {
  const pinia = createPinia()
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/projects/:id',
        name: 'project',
        component: ProjectPage,
        children: [
          { path: 'graph', name: 'project-graph', component: { template: '<div>graph</div>' } },
        ],
      },
    ],
  })

  await router.push('/projects/p-state/graph')
  await router.isReady()

  return mount(ProjectPage, {
    global: {
      plugins: [pinia, router],
    },
  })
}

describe('ProjectPage states', () => {
  beforeEach(() => {
    queryState.data.value = undefined
    queryState.isLoading.value = false
    queryState.isError.value = false
  })

  it('shows loading state while project query is loading', async () => {
    queryState.isLoading.value = true
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="project-control-loading"]').exists()).toBe(true)
  })

  it('shows error state when project query fails', async () => {
    queryState.isError.value = true
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="project-control-error"]').exists()).toBe(true)
  })

  it('shows empty fallback state when project is missing without error', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="project-control-empty"]').exists()).toBe(true)
  })
})
