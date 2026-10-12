<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import cytoscape, { type Core, type NodeSingular } from 'cytoscape'
// @ts-ignore — no official type declarations for cytoscape-fcose
import fcose from 'cytoscape-fcose'
import type { GraphNode, GraphRelationship } from '@/api/types'
import { getNodeColor } from '@/constants/nodeColors'
import { useGraphStore } from '@/stores/useGraphStore'
import { buildGraphStylesheet } from './graphStylesheet'

cytoscape.use(fcose)

const props = defineProps<{
  nodes: GraphNode[]
  relationships: GraphRelationship[]
}>()

const graphStore = useGraphStore()
const containerRef = ref<HTMLElement | null>(null)
let cy: Core | null = null

// Build Cytoscape elements from props
function buildElements() {
  const nodeEls = props.nodes.map((n) => ({
    data: {
      id: n.id,
      label: n.name,
      type: n.type,
      color: getNodeColor(n.type),
      nodeData: n,
    },
  }))

  const edgeEls = props.relationships.map((r, idx) => ({
    data: {
      id: `e-${r.source_id}-${r.target_id}-${idx}`,
      source: r.source_id,
      target: r.target_id,
      label: r.type,
    },
  }))

  return [...nodeEls, ...edgeEls]
}


function registerPendingNodeHandler() {
  if (!cy) return
  cy.one('layoutstop', () => {
    if (!cy) return
    const nodeId = graphStore.consumePendingNode()
    if (!nodeId) return
    const cyNode = cy.getElementById(nodeId)
    if (!cyNode || cyNode.length === 0) return
    graphStore.selectNode(cyNode.data('nodeData') as GraphNode)
    cy.animate({
      fit: { eles: cyNode, padding: 120 },
      duration: 600,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any)
  })
}

function initCytoscape() {
  if (!containerRef.value) return

  cy = cytoscape({
    container: containerRef.value,
    elements: buildElements(),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    style: buildGraphStylesheet() as any,
    layout: {
      name: 'fcose',
      animate: true,
      animationDuration: 800,
      quality: 'default',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any,
    maxZoom: 5,
    minZoom: 0.05,
  })

  // Node click handler
  cy.on('tap', 'node', (event) => {
    const node = (event.target as NodeSingular).data('nodeData') as GraphNode
    graphStore.selectNode(node)
  })

  // Edge hover — show label on hover
  cy.on('mouseover', 'edge', (event) => {
    event.target.addClass('highlighted')
  })
  cy.on('mouseout', 'edge', (event) => {
    event.target.removeClass('highlighted')
  })

  // Background tap deselects
  cy.on('tap', (event) => {
    if (event.target === cy) {
      graphStore.selectNode(null)
    }
  })

  registerPendingNodeHandler()
  applyFilters()
}

function applyFilters() {
  if (!cy) return
  const { visibleTypes, searchTerm, neighboursOnly } = graphStore.activeFilters
  cy.batch(() => {
    // Visibility by type
    cy!.nodes().forEach((node) => {
      const type = node.data('type') as string
      if (visibleTypes.has(type)) {
        node.removeClass('hidden').style('display', 'element')
      } else {
        node.style('display', 'none')
      }
    })

    // Search dimming
    if (searchTerm) {
      const lc = searchTerm.toLowerCase()
      cy!.nodes().forEach((node) => {
        const label = (node.data('label') as string).toLowerCase()
        if (!label.includes(lc)) {
          node.addClass('dimmed')
        } else {
          node.removeClass('dimmed')
        }
      })
    } else {
      cy!.nodes().removeClass('dimmed')
    }

    // Neighbours only
    if (neighboursOnly && graphStore.selectedNodeId) {
      const selectedCyNode = cy!.getElementById(graphStore.selectedNodeId)
      if (selectedCyNode.length > 0) {
        const neighbourhood = selectedCyNode.closedNeighborhood()
        cy!.nodes().not(neighbourhood).style('display', 'none')
        neighbourhood.nodes().style('display', 'element')
      }
    }
  })

  // Fit to search result
  if (searchTerm) {
    const lc = searchTerm.toLowerCase()
    const matches = cy!.nodes().filter(
      (n) => !(n.data('label') as string).toLowerCase().includes(lc) === false
    )
    if (matches.length > 0) {
      cy!.fit(matches, 50)
    }
  }
}

onMounted(() => {
  initCytoscape()
})

onBeforeUnmount(() => {
  cy?.destroy()
  cy = null
})

// Watch for filter changes from store
watch(() => graphStore.activeFilters, applyFilters, { deep: true })

// Watch for data changes and reload
watch(
  () => [props.nodes, props.relationships],
  () => {
    if (!cy) return
    cy.elements().remove()
    cy.add(buildElements())
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const layout = cy.layout({ name: 'fcose', animate: true } as any)
    registerPendingNodeHandler()
    layout.run()
    applyFilters()
  },
  { deep: false }
)
</script>

<template>
  <div
    ref="containerRef"
    class="graph-canvas"
  />
</template>

<style scoped>
.graph-canvas {
  width: 100%;
  height: 100%;
  background-color: var(--color-bg-base);
  background-image: radial-gradient(circle, var(--color-graph-grid) 1px, transparent 1px);
  background-size: 20px 20px;
}
</style>
