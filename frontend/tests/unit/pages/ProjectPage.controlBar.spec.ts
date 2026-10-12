import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
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

function createProjectRouter() {
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

async function mountAt(path: string) {
  const pinia = createPinia()
  setActivePinia(pinia)

  const router = createProjectRouter()
  await router.push(path)
  await router.isReady()

  const wrapper = mount(ProjectPage, {
    global: {
      plugins: [pinia, router],
    },
  })

  return { wrapper, router }
}

describe('ProjectPage control bar', () => {
  beforeEach(() => {
    queryState.data.value = { name: 'Core Services and Extremely Long Project Name For Truncation' }
    queryState.isLoading.value = false
    queryState.isError.value = false
  })

  it('renders the unified control bar and marks Graph as active', async () => {
    const { wrapper } = await mountAt('/projects/p-1/graph')

    expect(wrapper.find('[data-testid="project-control-bar"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="project-control-tab-graph"]').classes()).toContain('active')
    expect(wrapper.get('[data-testid="project-control-project-name"]').attributes('title')).toContain(
      'Core Services'
    )
  })

  it('marks Files as active on files route', async () => {
    const { wrapper } = await mountAt('/projects/p-1/files')
    expect(wrapper.get('[data-testid="project-control-tab-files"]').classes()).toContain('active')
  })
})
