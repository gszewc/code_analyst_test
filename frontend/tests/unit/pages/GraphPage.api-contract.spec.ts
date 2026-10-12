import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import GraphPage from '@/pages/GraphPage.vue'

const invalidateQueries = vi.fn()
const useGraphDataMock = vi.fn()

const mockGraphData = {
  nodes: ref([{ id: 'n-1', type: 'Class', name: 'A', source_file: null, start_line: null, end_line: null }]),
  relationships: ref([]),
  stats: ref(null),
  isLoading: ref(false),
  totalNodes: ref(20_500),
  nodesQuery: { isError: ref(false) },
  relationshipsQuery: { isError: ref(false) },
}

vi.mock('@/composables/useGraphData', () => ({
  useGraphData: (...args: unknown[]) => {
    useGraphDataMock(...args)
    return mockGraphData
  },
}))

vi.mock('@tanstack/vue-query', () => ({
  useQueryClient: vi.fn(() => ({ invalidateQueries })),
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

  await router.push('/projects/p-api/graph')
  await router.isReady()

  return mount(GraphPage, {
    global: {
      plugins: [pinia, router],
    },
  })
}

describe('GraphPage API contract behavior', () => {
  beforeEach(() => {
    invalidateQueries.mockReset()
    useGraphDataMock.mockReset()
    mockGraphData.totalNodes.value = 20_500
    mockGraphData.nodes.value = [
      { id: 'n-1', type: 'Class', name: 'A', source_file: null, start_line: null, end_line: null },
    ]
    mockGraphData.isLoading.value = false
    mockGraphData.nodesQuery.isError.value = false
    mockGraphData.relationshipsQuery.isError.value = false
  })

  it('calls useGraphData with route project id and default node limit', async () => {
    await mountPage()

    expect(useGraphDataMock).toHaveBeenCalledWith('p-api', 2000)
  })

  it('keeps project node query invalidation key shape when loading more', async () => {
    const wrapper = await mountPage()

    await wrapper.get('.load-more-btn').trigger('click')

    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['projectNodes', 'p-api'] })
  })
})
