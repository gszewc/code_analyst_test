import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGraphStore } from '../../../src/stores/useGraphStore'
import { ALL_NODE_TYPES } from '../../../src/constants/nodeColors'
import { api } from '../../../src/api/client'

describe('useGraphStore filter logic', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts with all node types visible', () => {
    const store = useGraphStore()
    expect(store.visibleTypes.size).toBe(ALL_NODE_TYPES.length)
    ALL_NODE_TYPES.forEach((t) => expect(store.visibleTypes.has(t)).toBe(true))
  })

  it('toggleType removes a type when visible', () => {
    const store = useGraphStore()
    store.toggleType('Function')
    expect(store.visibleTypes.has('Function')).toBe(false)
  })

  it('toggleType adds a type when hidden', () => {
    const store = useGraphStore()
    store.toggleType('Function')
    store.toggleType('Function')
    expect(store.visibleTypes.has('Function')).toBe(true)
  })

  it('setAllTypes(false) hides all types', () => {
    const store = useGraphStore()
    store.setAllTypes(false)
    expect(store.visibleTypes.size).toBe(0)
  })

  it('setAllTypes(true) shows all types', () => {
    const store = useGraphStore()
    store.setAllTypes(false)
    store.setAllTypes(true)
    expect(store.visibleTypes.size).toBe(ALL_NODE_TYPES.length)
  })

  it('setSearchTerm updates searchTerm', () => {
    const store = useGraphStore()
    store.setSearchTerm('MyClass')
    expect(store.searchTerm).toBe('MyClass')
  })

  it('clearFilters resets all state', () => {
    const store = useGraphStore()
    store.setAllTypes(false)
    store.setSearchTerm('test')
    store.setNeighboursOnly(true)
    store.clearFilters()
    expect(store.visibleTypes.size).toBe(ALL_NODE_TYPES.length)
    expect(store.searchTerm).toBe('')
    expect(store.neighboursOnly).toBe(false)
  })

  it('activeFilterCount is 0 when no filters are active', () => {
    const store = useGraphStore()
    expect(store.activeFilterCount).toBe(0)
  })

  it('activeFilterCount includes hidden node types, search, and neighbours-only', () => {
    const store = useGraphStore()

    store.toggleType('Function')
    store.toggleType('Class')
    store.setSearchTerm('parser')
    store.setNeighboursOnly(true)

    expect(store.activeFilterCount).toBe(4)
  })
})

describe('useGraphStore pendingNodeId', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts as null', () => {
    const store = useGraphStore()
    expect(store.pendingNodeId).toBeNull()
  })

  it('setPendingNode sets the value', () => {
    const store = useGraphStore()
    store.setPendingNode('abc-123')
    expect(store.pendingNodeId).toBe('abc-123')
  })

  it('consumePendingNode returns the value and clears it atomically', () => {
    const store = useGraphStore()
    store.setPendingNode('abc-123')
    const consumed = store.consumePendingNode()
    expect(consumed).toBe('abc-123')
    expect(store.pendingNodeId).toBeNull()
  })

  it('consumePendingNode returns null when nothing is pending', () => {
    const store = useGraphStore()
    expect(store.consumePendingNode()).toBeNull()
  })
})

describe('useGraphStore fetchDefaults', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('starts with defaultsFetched = false', () => {
    const store = useGraphStore()
    expect(store.defaultsFetched).toBe(false)
  })

  it('fetchDefaults updates defaultVisibleTypes and visibleTypes from backend', async () => {
    const mockResponse = {
      graph_default_visible_nodes: ['Class', 'Method', 'Function'],
      analysis_default_enabled_node_types: ['File', 'Class', 'Method', 'Function'],
      enabled_relationship_types: ['CONTAINS'],
      delete_graph_data: false,
    }
    vi.spyOn(api.config, 'getDefaults').mockResolvedValue(mockResponse)

    const store = useGraphStore()
    await store.fetchDefaults()

    expect(store.defaultVisibleTypes).toEqual(new Set(['Class', 'Method', 'Function']))
    expect(store.visibleTypes).toEqual(new Set(['Class', 'Method', 'Function']))
    expect(store.defaultsFetched).toBe(true)
  })

  it('fetchDefaults falls back to ALL_NODE_TYPES on error', async () => {
    vi.spyOn(api.config, 'getDefaults').mockRejectedValue(new Error('Network error'))
    vi.spyOn(console, 'error').mockImplementation(() => {})

    const store = useGraphStore()
    await store.fetchDefaults()

    expect(store.defaultVisibleTypes.size).toBe(ALL_NODE_TYPES.length)
    expect(store.visibleTypes.size).toBe(ALL_NODE_TYPES.length)
    expect(store.defaultsFetched).toBe(true)
  })

  it('clearFilters resets to backend defaults after fetchDefaults', async () => {
    const mockResponse = {
      graph_default_visible_nodes: ['Class', 'Method'],
      analysis_default_enabled_node_types: ['File', 'Class', 'Method'],
      enabled_relationship_types: [],
      delete_graph_data: false,
    }
    vi.spyOn(api.config, 'getDefaults').mockResolvedValue(mockResponse)

    const store = useGraphStore()
    await store.fetchDefaults()

    // Modify filters
    store.toggleType('Function')
    expect(store.visibleTypes.has('Function')).toBe(true)

    // Reset
    store.clearFilters()
    expect(store.visibleTypes).toEqual(new Set(['Class', 'Method']))
    expect(store.visibleTypes.has('Function')).toBe(false)
  })
})
