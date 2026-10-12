<script setup lang="ts">
import { ref, watch } from 'vue'
import { useGraphStore } from '@/stores/useGraphStore'
import { ALL_NODE_TYPES, NODE_TYPE_LABELS, getNodeColor } from '@/constants/nodeColors'
import { SearchIcon, UsersIcon } from 'lucide-vue-next'

const props = defineProps<{
  nodeCounts?: Record<string, number>
}>()

const graphStore = useGraphStore()
const localSearch = ref(graphStore.searchTerm)

// Debounce search
let debounceTimer: ReturnType<typeof setTimeout>
watch(localSearch, (val) => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => graphStore.setSearchTerm(val), 200)
})
</script>

<template>
  <div class="filter-panel">
    <!-- Search -->
    <div class="filter-section">
      <div class="search-box">
        <SearchIcon
          :size="14"
          class="search-icon"
        />
        <input
          v-model="localSearch"
          type="text"
          placeholder="Search nodes…"
          class="search-input"
          data-testid="graph-filter-search"
        >
      </div>
    </div>

    <!-- Node types -->
    <div class="filter-section">
      <div class="filter-section-title">
        Node Types
      </div>
      <div
        v-for="type in ALL_NODE_TYPES"
        :key="type"
        class="type-row"
        :data-testid="`filter-row-${type}`"
        @click="graphStore.toggleType(type)"
      >
        <span
          class="color-chip"
          :style="{ background: graphStore.visibleTypes.has(type) ? getNodeColor(type) : 'transparent', borderColor: getNodeColor(type) }"
        />
        <span class="type-name">{{ NODE_TYPE_LABELS[type] ?? type }}</span>
        <span
          v-if="nodeCounts?.[type]"
          class="type-count"
        >{{ nodeCounts[type] }}</span>
      </div>
    </div>

    <!-- Neighbours -->
    <div class="filter-section">
      <label class="toggle-row">
        <UsersIcon :size="14" />
        <span>Neighbours only</span>
        <input
          type="checkbox"
          :checked="graphStore.neighboursOnly"
          class="toggle-input"
          data-testid="graph-filter-neighbours-only"
          @change="graphStore.setNeighboursOnly(($event.target as HTMLInputElement).checked)"
        >
      </label>
    </div>

    <button
      class="clear-btn"
      data-testid="graph-filter-reset"
      @click="graphStore.clearFilters(); localSearch = ''"
    >
      Reset filters
    </button>
  </div>
</template>

<style scoped>
.filter-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 14px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  min-width: 180px;
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 8px;
  color: var(--color-text-muted);
  pointer-events: none;
}

.search-input {
  width: 100%;
  background: var(--color-bg-overlay);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: 13px;
  padding: 6px 8px 6px 28px;
  outline: none;
  box-sizing: border-box;
}

.search-input:focus {
  border-color: var(--color-accent);
}

.type-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 2px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}

.type-row:hover {
  background: var(--color-bg-overlay);
}

.color-chip {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1.5px solid;
  flex-shrink: 0;
  transition: background var(--transition-fast);
}

.type-name {
  flex: 1;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.type-count {
  font-size: 12px;
  color: var(--color-text-muted);
  font-variant-numeric: tabular-nums;
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.toggle-input {
  margin-left: auto;
  cursor: pointer;
  accent-color: var(--color-accent);
}

.clear-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  font-size: 12px;
  padding: 5px 10px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.clear-btn:hover {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}
</style>
