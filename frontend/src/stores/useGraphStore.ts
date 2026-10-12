import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { GraphNode, NodeType } from '@/api/types'
import { ALL_NODE_TYPES } from '@/constants/nodeColors'
import { api } from '@/api/client'
import { useToastStore } from '@/stores/useToastStore'

export const useGraphStore = defineStore('graph', () => {
  const selectedNode = ref<GraphNode | null>(null)
  const defaultVisibleTypes = ref<Set<string>>(new Set(ALL_NODE_TYPES))
  const visibleTypes = ref<Set<string>>(new Set(ALL_NODE_TYPES))
  const searchTerm = ref('')
  const neighboursOnly = ref(false)
  const selectedNodeId = ref<string | null>(null)
  const pendingNodeId = ref<string | null>(null)
  const defaultsFetched = ref(false)

  // Filter state
  const activeFilters = computed(() => ({
    visibleTypes: visibleTypes.value,
    searchTerm: searchTerm.value,
    neighboursOnly: neighboursOnly.value,
  }))

  const activeFilterCount = computed(() => {
    const hiddenTypeCount = ALL_NODE_TYPES.length - visibleTypes.value.size
    const hasSearch = searchTerm.value.trim().length > 0 ? 1 : 0
    const neighbourFilter = neighboursOnly.value ? 1 : 0
    return hiddenTypeCount + hasSearch + neighbourFilter
  })

  async function fetchDefaults(): Promise<void> {
    const toastStore = useToastStore()
    try {
      const response = await api.config.getDefaults()
      const defaults = new Set<string>(response.graph_default_visible_nodes)
      defaultVisibleTypes.value = defaults
      visibleTypes.value = new Set(defaults)
    } catch (error) {
      console.error('Failed to load default node visibility config:', error)
      defaultVisibleTypes.value = new Set(ALL_NODE_TYPES)
      visibleTypes.value = new Set(ALL_NODE_TYPES)
      toastStore.addToast('Could not load default filter config. Showing all node types.', 'error')
    } finally {
      defaultsFetched.value = true
    }
  }

  function selectNode(node: GraphNode | null) {
    selectedNode.value = node
    selectedNodeId.value = node?.id ?? null
  }

  function toggleType(type: string) {
    const next = new Set(visibleTypes.value)
    if (next.has(type)) {
      next.delete(type)
    } else {
      next.add(type)
    }
    visibleTypes.value = next
  }

  function setAllTypes(visible: boolean) {
    visibleTypes.value = visible ? new Set(ALL_NODE_TYPES) : new Set()
  }

  function setSearchTerm(term: string) {
    searchTerm.value = term
  }

  function setNeighboursOnly(value: boolean) {
    neighboursOnly.value = value
  }

  function clearFilters() {
    visibleTypes.value = new Set(defaultVisibleTypes.value)
    searchTerm.value = ''
    neighboursOnly.value = false
  }

  function setPendingNode(id: string): void {
    pendingNodeId.value = id
  }

  function consumePendingNode(): string | null {
    const id = pendingNodeId.value
    pendingNodeId.value = null
    return id
  }

  return {
    selectedNode,
    defaultVisibleTypes,
    visibleTypes,
    searchTerm,
    neighboursOnly,
    selectedNodeId,
    pendingNodeId,
    defaultsFetched,
    activeFilters,
    activeFilterCount,
    fetchDefaults,
    selectNode,
    toggleType,
    setAllTypes,
    setSearchTerm,
    setNeighboursOnly,
    clearFilters,
    setPendingNode,
    consumePendingNode,
  }
})
