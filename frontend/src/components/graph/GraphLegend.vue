<script setup lang="ts">
import { ALL_NODE_TYPES, NODE_TYPE_LABELS, getNodeColor } from '@/constants/nodeColors'
</script>

<template>
  <div class="graph-legend">
    <div class="legend-title">
      Node Types
    </div>
    <div
      v-for="type in ALL_NODE_TYPES"
      :key="type"
      class="legend-item"
    >
      <span
        class="color-chip"
        :style="{ background: getNodeColor(type) }"
      />
      <span class="type-label">{{ NODE_TYPE_LABELS[type] ?? type }}</span>
    </div>
  </div>
</template>

<style scoped>
.graph-legend {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 12px 14px;
  min-width: 140px;
}

.legend-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
}

.color-chip {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.type-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}
</style>
