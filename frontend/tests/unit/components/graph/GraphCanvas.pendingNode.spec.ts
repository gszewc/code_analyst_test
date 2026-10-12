import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { useGraphStore } from '../../../../src/stores/useGraphStore'

// Module-level mutable state captured by vi.mock factory
const _handlers: { layoutstop: Array<() => void> } = { layoutstop: [] }
const _animate = vi.fn()
const _getElementById = vi.fn()

// Hoisted so beforeEach can re-establish after mockClear()
const _fakeNodeData = {
  id: 'node-123',
  type: 'Class',
  name: 'MyClass',
  source_file: null,
  start_line: null,
  end_line: null,
}
const _fakeNode = {
  length: 1,
  data: vi.fn().mockImplementation((key: string) =>
    key === 'nodeData' ? _fakeNodeData : null
  ),
}

vi.mock('cytoscape', () => {
  _getElementById.mockReturnValue(_fakeNode)
  const nodesResult = {
    forEach: vi.fn(),
    filter: vi.fn().mockReturnValue({ length: 0 }),
    removeClass: vi.fn(),
    not: vi.fn().mockReturnValue({ style: vi.fn() }),
    style: vi.fn(),
  }

  const mockCy = {
    on: vi.fn(),
    one: vi.fn().mockImplementation((event: string, handler: () => void) => {
      if (event === 'layoutstop') _handlers.layoutstop.push(handler)
    }),
    batch: vi.fn().mockImplementation((fn: () => void) => fn()),
    nodes: vi.fn().mockReturnValue(nodesResult),
    elements: vi.fn().mockReturnValue({ remove: vi.fn() }),
    add: vi.fn(),
    layout: vi.fn().mockReturnValue({ run: vi.fn() }),
    animate: _animate,
    getElementById: _getElementById,
    destroy: vi.fn(),
    fit: vi.fn(),
  }

  return {
    default: Object.assign(vi.fn().mockReturnValue(mockCy), { use: vi.fn() }),
  }
})

vi.mock('cytoscape-fcose', () => ({ default: {} }))

describe('GraphCanvas — pending node zoom', () => {
  beforeEach(() => {
    _handlers.layoutstop = []
    _animate.mockClear()
    _getElementById.mockClear()
    _getElementById.mockReturnValue(_fakeNode) // re-establish after mockClear strips it
    setActivePinia(createPinia())
  })

  it('zooms to pending node when layoutstop fires', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const { default: GraphCanvas } = await import('../../../../src/components/graph/GraphCanvas.vue')
    const wrapper = mount(GraphCanvas, {
      props: {
        nodes: [{ id: 'node-123', type: 'Class', name: 'MyClass', source_file: null, start_line: null, end_line: null }],
        relationships: [],
      },
      global: { plugins: [pinia] },
    })

    const store = useGraphStore()
    store.setPendingNode('node-123')

    // Fire the layoutstop handler registered during initCytoscape
    expect(_handlers.layoutstop.length).toBeGreaterThan(0)
    _handlers.layoutstop[0]()

    expect(_animate).toHaveBeenCalledWith(
      expect.objectContaining({
        fit: expect.objectContaining({ padding: 120 }),
        duration: 600,
      })
    )

    wrapper.unmount()
  })

  it('clears pendingNodeId after consuming it', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const { default: GraphCanvas } = await import('../../../../src/components/graph/GraphCanvas.vue')
    const wrapper = mount(GraphCanvas, {
      props: {
        nodes: [{ id: 'node-123', type: 'Class', name: 'MyClass', source_file: null, start_line: null, end_line: null }],
        relationships: [],
      },
      global: { plugins: [pinia] },
    })

    const store = useGraphStore()
    store.setPendingNode('node-123')
    _handlers.layoutstop[0]()

    expect(store.pendingNodeId).toBeNull()

    wrapper.unmount()
  })

  it('does not animate when no pending node is set', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const { default: GraphCanvas } = await import('../../../../src/components/graph/GraphCanvas.vue')
    const wrapper = mount(GraphCanvas, {
      props: {
        nodes: [{ id: 'node-123', type: 'Class', name: 'MyClass', source_file: null, start_line: null, end_line: null }],
        relationships: [],
      },
      global: { plugins: [pinia] },
    })

    _handlers.layoutstop[0]()

    expect(_animate).not.toHaveBeenCalled()

    wrapper.unmount()
  })

  it('does not animate again when layoutstop fires a second time (pendingNodeId already consumed)', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const { default: GraphCanvas } = await import('../../../../src/components/graph/GraphCanvas.vue')
    const wrapper = mount(GraphCanvas, {
      props: {
        nodes: [{ id: 'node-123', type: 'Class', name: 'MyClass', source_file: null, start_line: null, end_line: null }],
        relationships: [],
      },
      global: { plugins: [pinia] },
    })

    const store = useGraphStore()
    store.setPendingNode('node-123')

    // First layoutstop — should zoom
    _handlers.layoutstop[0]()
    expect(_animate).toHaveBeenCalledTimes(1)

    // Simulate second layoutstop (pendingNodeId is now null, so handler exits early)
    _handlers.layoutstop[0]()
    expect(_animate).toHaveBeenCalledTimes(1) // still 1

    wrapper.unmount()
  })
})
