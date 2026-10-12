import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import ProjectPage from '@/pages/ProjectPage.vue'

const queryState = {
  data: ref<{ name: string } | undefined>({ name: 'Navigation Test Project' }),
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

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/projects/:id',
        name: 'project',
        component: ProjectPage,
        children: [
          { path: 'graph', name: 'project-graph', component: { template: '<div>graph</div>' } },
          { path: 'files', name: 'project-files', component: { template: '<div>files</div>' } },
          { path: 'analysis', name: 'project-analysis', component: { template: '<div>analysis</div>' } },
        ],
      },
    ],
  })
}

describe('ProjectPage navigation state', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    queryState.isLoading.value = false
    queryState.isError.value = false
  })

  it('keeps active section in sync across Graph, Files, and Analysis routes', async () => {
    const pinia = createPinia()
    const router = makeRouter()

    await router.push('/projects/p-9/graph')
    await router.isReady()

    const wrapper = mount(ProjectPage, {
      global: {
        plugins: [pinia, router],
      },
    })

    expect(wrapper.get('[data-testid="project-control-tab-graph"]').classes()).toContain('active')

    await router.push('/projects/p-9/files')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('[data-testid="project-control-tab-files"]').classes()).toContain('active')

    await router.push('/projects/p-9/analysis')
    await wrapper.vm.$nextTick()
    expect(wrapper.get('[data-testid="project-control-tab-analysis"]').classes()).toContain('active')
  })
})
