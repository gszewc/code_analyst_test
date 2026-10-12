import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import GraphPage from '@/pages/GraphPage.vue'

const mockGraphData = {
  nodes: ref([{ id: 'n-1', type: 'Class', name: 'A', source_file: null, start_line: null, end_line: null }]),
  relationships: ref([]),
  stats: ref(null),
  isLoading: ref(false),
  totalNodes: ref(12),
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
    global: {
      plugins: [pinia, router],
    },
  })
}

describe('GraphPage layout behavior', () => {
  const thisFile = fileURLToPath(import.meta.url)
  const thisDir = thisFile.slice(0, thisFile.lastIndexOf('/'))

  beforeEach(() => {
    mockGraphData.nodes.value = [
      { id: 'n-1', type: 'Class', name: 'A', source_file: null, start_line: null, end_line: null },
    ]
    mockGraphData.relationships.value = []
    mockGraphData.isLoading.value = false
    mockGraphData.nodesQuery.isError.value = false
    mockGraphData.relationshipsQuery.isError.value = false
  })

  it('renders the flex-fill graph shell and canvas area', async () => {
    const wrapper = await mountPage()

    expect(wrapper.find('[data-testid="graph-page-main"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="graph-canvas-shell"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="graph-canvas"]').exists()).toBe(true)
  })

  it('does not use viewport subtraction calc rules in GraphPage styles', () => {
    const source = readFileSync(resolve(thisDir, '../../../src/pages/GraphPage.vue'), 'utf8')
    expect(source).not.toContain('calc(100vh -')
  })
})
