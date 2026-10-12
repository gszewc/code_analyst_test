import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { GraphNode } from '@/api/types'

vi.mock('@/api/client', () => ({
  api: {
    graph: {
      search: vi.fn(),
    },
  },
}))

function makeNode(overrides: Partial<GraphNode> & { id: string; type: string; name: string }): GraphNode {
  return {
    source_file: null,
    start_line: null,
    end_line: null,
    ...overrides,
  }
}

describe('useNodeLookup — findNode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns null when search returns no results', async () => {
    const { api } = await import('@/api/client')
    vi.mocked(api.graph.search).mockResolvedValue({ nodes: [], total: 0, query: 'x', limit: 20 })
    const { useNodeLookup } = await import('@/composables/useNodeLookup')
    const { findNode } = useNodeLookup()
    expect(await findNode('p1', 'x')).toBeNull()
  })

  it('prefers exact name match over partial match', async () => {
    const { api } = await import('@/api/client')
    vi.mocked(api.graph.search).mockResolvedValue({
      nodes: [
        makeNode({ id: 'a', type: 'Function', name: 'MyClassHelper' }),
        makeNode({ id: 'b', type: 'Class', name: 'MyClass' }),
      ],
      total: 2,
      query: 'MyClass',
      limit: 20,
    })
    const { useNodeLookup } = await import('@/composables/useNodeLookup')
    const { findNode } = useNodeLookup()
    const result = await findNode('p1', 'MyClass')
    expect(result?.id).toBe('b')
  })

  it('ranks by preferred type order among exact matches', async () => {
    const { api } = await import('@/api/client')
    vi.mocked(api.graph.search).mockResolvedValue({
      nodes: [
        makeNode({ id: 'a', type: 'Method', name: 'process' }),
        makeNode({ id: 'b', type: 'Function', name: 'process' }),
        makeNode({ id: 'c', type: 'Class', name: 'process' }),
      ],
      total: 3,
      query: 'process',
      limit: 20,
    })
    const { useNodeLookup } = await import('@/composables/useNodeLookup')
    const { findNode } = useNodeLookup()
    const result = await findNode('p1', 'process')
    // Default order is ['Class', 'Function', 'Method'] — Class wins
    expect(result?.id).toBe('c')
  })

  it('uses custom preferredTypes when provided', async () => {
    const { api } = await import('@/api/client')
    vi.mocked(api.graph.search).mockResolvedValue({
      nodes: [
        makeNode({ id: 'a', type: 'Class', name: 'run' }),
        makeNode({ id: 'b', type: 'Function', name: 'run' }),
      ],
      total: 2,
      query: 'run',
      limit: 20,
    })
    const { useNodeLookup } = await import('@/composables/useNodeLookup')
    const { findNode } = useNodeLookup()
    const result = await findNode('p1', 'run', ['Function', 'Class'])
    expect(result?.id).toBe('b')
  })

  it('falls back to first result when no exact match exists', async () => {
    const { api } = await import('@/api/client')
    vi.mocked(api.graph.search).mockResolvedValue({
      nodes: [
        makeNode({ id: 'a', type: 'Class', name: 'MyClassExtended' }),
        makeNode({ id: 'b', type: 'Function', name: 'MyClassFactory' }),
      ],
      total: 2,
      query: 'MyClass',
      limit: 20,
    })
    const { useNodeLookup } = await import('@/composables/useNodeLookup')
    const { findNode } = useNodeLookup()
    const result = await findNode('p1', 'MyClass')
    // Class ranks higher in default preferred types
    expect(result?.id).toBe('a')
  })
})

describe('useNodeLookup — findFileNode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns null when search returns no results', async () => {
    const { api } = await import('@/api/client')
    vi.mocked(api.graph.search).mockResolvedValue({ nodes: [], total: 0, query: 'main.py', limit: 50 })
    const { useNodeLookup } = await import('@/composables/useNodeLookup')
    const { findFileNode } = useNodeLookup()
    expect(await findFileNode('p1', 'src/main.py')).toBeNull()
  })

  it('validates source_file ends with full filepath to disambiguate', async () => {
    const { api } = await import('@/api/client')
    vi.mocked(api.graph.search).mockResolvedValue({
      nodes: [
        makeNode({ id: 'a', type: 'File', name: 'main.py', source_file: '/project/utils/main.py' }),
        makeNode({ id: 'b', type: 'File', name: 'main.py', source_file: '/project/core/main.py' }),
      ],
      total: 2,
      query: 'main.py',
      limit: 50,
    })
    const { useNodeLookup } = await import('@/composables/useNodeLookup')
    const { findFileNode } = useNodeLookup()
    const result = await findFileNode('p1', 'core/main.py')
    expect(result?.id).toBe('b')
  })

  it('returns null when no source_file matches the filepath suffix', async () => {
    const { api } = await import('@/api/client')
    vi.mocked(api.graph.search).mockResolvedValue({
      nodes: [
        makeNode({ id: 'a', type: 'File', name: 'main.py', source_file: '/project/utils/main.py' }),
      ],
      total: 1,
      query: 'main.py',
      limit: 50,
    })
    const { useNodeLookup } = await import('@/composables/useNodeLookup')
    const { findFileNode } = useNodeLookup()
    expect(await findFileNode('p1', 'other/main.py')).toBeNull()
  })

  it('searches by filename only (last path segment)', async () => {
    const { api } = await import('@/api/client')
    vi.mocked(api.graph.search).mockResolvedValue({ nodes: [], total: 0, query: 'auth.py', limit: 50 })
    const { useNodeLookup } = await import('@/composables/useNodeLookup')
    const { findFileNode } = useNodeLookup()
    await findFileNode('p1', 'services/auth.py')
    expect(api.graph.search).toHaveBeenCalledWith('p1', 'auth.py', { nodeType: 'File', limit: 50 })
  })
})
