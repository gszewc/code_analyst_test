<script setup lang="ts">
import { computed } from 'vue'
import type { ProjectStatsResponse } from '@/api/types'

const props = defineProps<{
  stats?: ProjectStatsResponse | null
}>()

const hasStats = computed(() =>
  !!props.stats && Number.isFinite(props.stats.node_count) && Number.isFinite(props.stats.relationship_count)
)
</script>

<template>
  <div
    v-if="hasStats"
    class="stats-overlay"
    data-testid="graph-stats-overlay"
  >
    <div
      class="chip"
      data-testid="graph-stats-node-count"
    >
      <strong>{{ props.stats!.node_count.toLocaleString() }}</strong>
      <span>Nodes</span>
    </div>
    <div
      class="chip"
      data-testid="graph-stats-edge-count"
    >
      <strong>{{ props.stats!.relationship_count.toLocaleString() }}</strong>
      <span>Edges</span>
    </div>
  </div>
</template>

<style scoped>
.stats-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  display: inline-flex;
  gap: 8px;
  pointer-events: none;
  z-index: 15;
}

.chip {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: color-mix(in oklab, var(--color-bg-base) 86%, black 14%);
  color: var(--color-text-secondary);
  font-size: 12px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.chip strong {
  font-size: 13px;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
}
</style>
