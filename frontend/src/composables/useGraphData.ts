import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/api/client'

export function useGraphData(projectId: string, nodeLimit = 2000) {
  const nodesQuery = useQuery({
    queryKey: computed(() => ['projectNodes', projectId]),
    queryFn: () => api.graph.listNodes(projectId, { limit: nodeLimit }),
    enabled: !!projectId,
    staleTime: 60_000,
  })

  const relationshipsQuery = useQuery({
    queryKey: computed(() => ['projectRelationships', projectId]),
    queryFn: () => api.graph.listRelationships(projectId, undefined, undefined, { limit: 10_000 }),
    enabled: !!projectId,
    staleTime: 60_000,
  })

  const statsQuery = useQuery({
    queryKey: computed(() => ['projectStats', projectId]),
    queryFn: () => api.graph.stats(projectId),
    enabled: !!projectId,
    staleTime: 60_000,
  })

  const nodes = computed(() => nodesQuery.data.value?.nodes ?? [])
  const relationships = computed(() => relationshipsQuery.data.value?.relationships ?? [])
  const stats = computed(() => statsQuery.data.value)
  const isLoading = computed(
    () => nodesQuery.isLoading.value || relationshipsQuery.isLoading.value
  )
  const totalNodes = computed(() => nodesQuery.data.value?.total ?? 0)

  return {
    nodes,
    relationships,
    stats,
    isLoading,
    totalNodes,
    nodesQuery,
    relationshipsQuery,
    statsQuery,
  }
}
