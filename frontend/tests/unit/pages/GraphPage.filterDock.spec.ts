import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import GraphPage from '@/pages/GraphPage.vue'

const mockGraphData = {
  nodes: ref([{ id: 'n-1', type: 'Class', name: 'A', source_file: null, start_line: null, end_line: null }]),
  relationships: ref([]),
  stats: ref(null),
  isLoading: ref(false),
  totalNodes: ref(100),
  nodesQuery: { isError: ref(false) },
  relationshipsQuery: { isError: ref(false) },
}

vi.mock('@/composables/useGraphData', () => ({
  useGraphData: vi.fn(() => mockGraphData),
}))

vi.mock('@tanstack/vue-query', () => ({
  useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
}))

vi.mock('@/components/graph/GraphCanvas.vue', () => ({
  default: {
    template: '<div data-testid="graph-canvas">canvas</div>',
  },
}))

vi.mock('@/components/graph/NodeDetailPanel.vue', () => ({
  default: {
    template: '<div data-testid="node-detail-panel" />',
  },
}))

async function mountPage() {
  const pinia = createPinia()
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/projects/:id/graph', name: 'project-graph', component: GraphPage }],
  })

  await router.push('/projects/p-1/graph')
  await router.isReady()

  return mount(GraphPage, {
    attachTo: document.body,
    global: {
      plugins: [pinia, router],
    },
  })
}

describe('GraphPage filter dock integration', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
  })

  it('keeps canvas shell stable while toggling filter dock', async () => {
    const wrapper = await mountPage()

    const shell = wrapper.get('[data-testid="graph-canvas-shell"]')
    const beforeClasses = shell.attributes('class')

    await wrapper.get('[data-testid="filter-dock-toggle"]').trigger('click')
    expect(wrapper.find('[data-testid="filter-dock-panel"]').exists()).toBe(true)

    const afterClasses = wrapper.get('[data-testid="graph-canvas-shell"]').attributes('class')
    expect(afterClasses).toBe(beforeClasses)
  })
})
