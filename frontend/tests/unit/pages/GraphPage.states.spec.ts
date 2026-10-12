import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import GraphPage from '@/pages/GraphPage.vue'

const mockGraphData = {
  nodes: ref([] as any[]),
  relationships: ref([] as any[]),
  stats: ref(null),
  isLoading: ref(false),
  totalNodes: ref(0),
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

  await router.push('/projects/p-states/graph')
  await router.isReady()

  return mount(GraphPage, {
    global: {
      plugins: [pinia, router],
    },
  })
}

describe('GraphPage states', () => {
  beforeEach(() => {
    mockGraphData.nodes.value = []
    mockGraphData.relationships.value = []
    mockGraphData.isLoading.value = false
    mockGraphData.nodesQuery.isError.value = false
    mockGraphData.relationshipsQuery.isError.value = false
  })

  it('shows loading state while graph data is loading', async () => {
    mockGraphData.isLoading.value = true
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="graph-state-loading"]').exists()).toBe(true)
  })

  it('shows empty state when no nodes are available', async () => {
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="graph-state-empty"]').exists()).toBe(true)
  })

  it('shows error state when graph queries fail', async () => {
    mockGraphData.nodesQuery.isError.value = true
    const wrapper = await mountPage()
    expect(wrapper.find('[data-testid="graph-state-error"]').exists()).toBe(true)
  })
})
