<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQueryClient } from '@tanstack/vue-query'
import { useGraphData } from '@/composables/useGraphData'
import { useGraphStore } from '@/stores/useGraphStore'
import GraphCanvas from '@/components/graph/GraphCanvas.vue'
import GraphFilterDock from '@/components/graph/GraphFilterDock.vue'
import GraphStatsOverlay from '@/components/graph/GraphStatsOverlay.vue'
import NodeDetailPanel from '@/components/graph/NodeDetailPanel.vue'
import { AlertTriangleIcon, PlusCircleIcon } from 'lucide-vue-next'

const route = useRoute()
const queryClient = useQueryClient()
const projectId = computed(() => route.params.id as string)
const graphStore = useGraphStore()

const nodeLimit = ref(2000)
const { nodes, relationships, stats, isLoading, totalNodes, nodesQuery, relationshipsQuery } = useGraphData(projectId.value, nodeLimit.value)

const showLargeWarning = computed(() => totalNodes.value > 10_000)
const hasGraphError = computed(() => nodesQuery.isError.value || relationshipsQuery.isError.value)
const showEmptyState = computed(() => !isLoading.value && nodes.value.length === 0)

// Node type counts
const nodeCounts = computed(() => {
  const counts: Record<string, number> = {}
  nodes.value.forEach((n) => {
    counts[n.type] = (counts[n.type] ?? 0) + 1
  })
  return counts
})

async function loadMore() {
  nodeLimit.value += 2000
  queryClient.invalidateQueries({ queryKey: ['projectNodes', projectId.value] })
}

onMounted(async () => {
  if (!graphStore.defaultsFetched) {
    await graphStore.fetchDefaults()
  }
  const nodeId = route.query.nodeId as string | undefined
  if (nodeId && !graphStore.pendingNodeId) {
    graphStore.setPendingNode(nodeId)
  }
})
</script>

<template>
  <div
    class="graph-page"
    data-testid="graph-page"
  >
    <!-- Large graph warning -->
    <div
      v-if="showLargeWarning"
      class="large-warning"
      data-testid="graph-page-warning"
    >
      <AlertTriangleIcon :size="16" />
      Showing first {{ nodeLimit }} of {{ totalNodes.toLocaleString() }} nodes.
      <button
        class="load-more-btn"
        @click="loadMore"
      >
        <PlusCircleIcon :size="14" />
        Load {{ Math.min(2000, totalNodes - nodeLimit) }} more
      </button>
    </div>

    <div
      class="graph-main"
      data-testid="graph-page-main"
    >
      <div class="graph-toolbar">
        <GraphFilterDock :node-counts="nodeCounts" />
      </div>

      <div
        class="canvas-col"
        data-testid="graph-canvas-shell"
      >
        <div
          v-if="isLoading"
          class="canvas-state"
          data-testid="graph-state-loading"
        >
          Loading graph...
        </div>
        <div
          v-else-if="hasGraphError"
          class="canvas-state"
          data-testid="graph-state-error"
        >
          Failed to load graph data
        </div>
        <div
          v-else-if="showEmptyState"
          class="canvas-state"
          data-testid="graph-state-empty"
        >
          No graph data — run analysis first
        </div>
        <GraphCanvas
          v-else
          :nodes="nodes"
          :relationships="relationships"
        />
        <GraphStatsOverlay :stats="stats" />
      </div>
    </div>

    <!-- Node detail slide-over panel -->
    <NodeDetailPanel :project-id="projectId" />
  </div>
</template>

<style scoped>
.graph-page {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  min-height: 0;
  overflow: visible;
  padding: 12px;
  gap: 10px;
}

.large-warning {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: rgba(240, 165, 0, 0.08);
  border-bottom: 1px solid rgba(240, 165, 0, 0.2);
  font-size: 13px;
  color: var(--color-warning);
}

.load-more-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: 1px solid var(--color-accent-border);
  color: var(--color-accent);
  border-radius: var(--radius-md);
  padding: 3px 8px;
  font-size: 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.load-more-btn:hover {
  background: var(--color-accent-muted);
}

.graph-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  gap: 8px;
}

.graph-toolbar {
  position: relative;
  z-index: 25;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  min-height: 32px;
}

.canvas-col {
  flex: 1;
  min-height: 0;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--color-border);
  position: relative;
  background: var(--color-bg-base);
}

.canvas-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-muted);
  font-size: 15px;
}
</style>
