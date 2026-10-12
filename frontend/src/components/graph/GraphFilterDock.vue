<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { SlidersHorizontalIcon, XIcon } from 'lucide-vue-next'
import GraphFilterPanel from '@/components/graph/GraphFilterPanel.vue'
import { useGraphStore } from '@/stores/useGraphStore'

const props = defineProps<{
  nodeCounts?: Record<string, number>
}>()

const graphStore = useGraphStore()
const isOpen = ref(false)
const sessionKey = 'graph-filter-dock-open'
const dockRoot = ref<HTMLElement | null>(null)

const activeFilterCount = computed(() => graphStore.activeFilterCount)

function closeDock() {
  isOpen.value = false
}

function toggleDock() {
  isOpen.value = !isOpen.value
}

function onEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    closeDock()
  }
}

function onWindowClick(event: MouseEvent) {
  if (!isOpen.value || !dockRoot.value) {
    return
  }

  const target = event.target as Node | null
  if (target && !dockRoot.value.contains(target)) {
    closeDock()
  }
}

onMounted(() => {
  if (typeof window === 'undefined') {
    return
  }

  const persisted = window.sessionStorage.getItem(sessionKey)
  isOpen.value = persisted === '1'

  window.addEventListener('keydown', onEscape)
  window.addEventListener('click', onWindowClick, true)
})

onBeforeUnmount(() => {
  if (typeof window === 'undefined') {
    return
  }

  window.removeEventListener('keydown', onEscape)
  window.removeEventListener('click', onWindowClick, true)
})

watch(isOpen, (value: boolean) => {
  if (typeof window === 'undefined') {
    return
  }

  window.sessionStorage.setItem(sessionKey, value ? '1' : '0')
})
</script>

<template>
  <div
    ref="dockRoot"
    class="filter-dock-root"
  >
    <button
      class="filter-trigger"
      type="button"
      data-testid="filter-dock-toggle"
      :aria-expanded="isOpen"
      @click="toggleDock"
    >
      <SlidersHorizontalIcon :size="14" />
      <span>Filters</span>
      <span
        v-if="activeFilterCount > 0"
        class="filter-count"
        data-testid="filter-dock-count"
      >
        {{ activeFilterCount }}
      </span>
    </button>

    <div
      v-if="isOpen"
      class="filter-backdrop"
      data-testid="filter-dock-backdrop"
    >
      <aside
        class="filter-panel-wrap"
        data-testid="filter-dock-panel"
      >
        <header class="filter-panel-header">
          <h3>Filters</h3>
          <button
            type="button"
            class="close-btn"
            aria-label="Close filters"
            @click="closeDock"
          >
            <XIcon :size="14" />
          </button>
        </header>

        <GraphFilterPanel :node-counts="props.nodeCounts" />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.filter-dock-root {
  position: relative;
  z-index: 20;
}

.filter-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: color-mix(in oklab, var(--color-bg-elevated) 88%, white 12%);
  color: var(--color-text-primary);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: pointer;
}

.filter-trigger:hover {
  border-color: var(--color-accent-border);
}

.filter-count {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  background: var(--color-accent);
  color: white;
}

.filter-backdrop {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: 40;
  width: min(360px, calc(100vw - 36px));
}

.filter-panel-wrap {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: color-mix(in oklab, var(--color-bg-base) 88%, black 12%);
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.25);
  padding: 12px;
}

.filter-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.filter-panel-header h3 {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.close-btn {
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  cursor: pointer;
}

.close-btn:hover {
  color: var(--color-text-primary);
}

@media (max-width: 960px) {
  .filter-backdrop {
    position: fixed;
    inset: 0;
    width: 100%;
    background: rgba(0, 0, 0, 0.2);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 64px 16px 16px;
  }

  .filter-panel-wrap {
    width: min(420px, 100%);
  }
}
</style>
