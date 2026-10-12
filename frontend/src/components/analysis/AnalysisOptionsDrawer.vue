<script setup lang="ts">
import { XIcon } from 'lucide-vue-next'
import type { ASTNodeType, ASTRelationshipType } from '@/api/types'

const ALL_NODE_TYPES: ASTNodeType[] = [
  'File', 'Package', 'Class', 'Interface', 'Enum',
  'Function', 'Method', 'Constructor', 'Variable',
  'Import', 'ExternalModule',
]

const ALL_RELATIONSHIP_TYPES: ASTRelationshipType[] = [
  'CONTAINS', 'EXTENDS', 'IMPLEMENTS', 'CALLS',
  'DEPENDS_ON', 'USES', 'IMPORTS',
]

const props = defineProps<{
  open: boolean
  deleteGraphData: boolean
  enabledNodeTypes: ASTNodeType[]
  enabledRelationshipTypes: ASTRelationshipType[]
}>()

const emit = defineEmits<{
  close: []
  'update:deleteGraphData': [value: boolean]
  'update:enabledNodeTypes': [value: ASTNodeType[]]
  'update:enabledRelationshipTypes': [value: ASTRelationshipType[]]
}>()

function toggleNodeType(type: ASTNodeType) {
  const current = [...props.enabledNodeTypes]
  const idx = current.indexOf(type)
  if (idx >= 0) {
    if (current.length > 1) current.splice(idx, 1)
  } else {
    current.push(type)
  }
  emit('update:enabledNodeTypes', current)
}

function toggleRelType(type: ASTRelationshipType) {
  const current = [...props.enabledRelationshipTypes]
  const idx = current.indexOf(type)
  if (idx >= 0) {
    if (current.length > 1) current.splice(idx, 1)
  } else {
    current.push(type)
  }
  emit('update:enabledRelationshipTypes', current)
}
</script>

<template>
  <Transition name="slide">
    <div
      v-if="open"
      class="drawer-overlay"
      @click.self="emit('close')"
    >
      <aside class="drawer">
        <header class="drawer-header">
          <span class="drawer-title">Analysis Options</span>
          <button
            class="close-btn"
            @click="emit('close')"
          >
            <XIcon :size="18" />
          </button>
        </header>

        <div class="drawer-body">
          <!-- Delete toggle -->
          <label class="delete-toggle">
            <input
              type="checkbox"
              :checked="deleteGraphData"
              @change="emit('update:deleteGraphData', ($event.target as HTMLInputElement).checked)"
            >
            <span>Delete existing graph data</span>
          </label>

          <!-- Node types -->
          <section class="type-section">
            <h4 class="type-label">
              Node Types
            </h4>
            <div class="type-grid">
              <label
                v-for="t in ALL_NODE_TYPES"
                :key="t"
                class="type-checkbox"
              >
                <input
                  type="checkbox"
                  :checked="enabledNodeTypes.includes(t)"
                  @change="toggleNodeType(t)"
                >
                <span>{{ t }}</span>
              </label>
            </div>
          </section>

          <!-- Relationship types -->
          <section class="type-section">
            <h4 class="type-label">
              Relationship Types
            </h4>
            <div class="type-grid">
              <label
                v-for="t in ALL_RELATIONSHIP_TYPES"
                :key="t"
                class="type-checkbox"
              >
                <input
                  type="checkbox"
                  :checked="enabledRelationshipTypes.includes(t)"
                  @change="toggleRelType(t)"
                >
                <span>{{ t }}</span>
              </label>
            </div>
          </section>
        </div>
      </aside>
    </div>
  </Transition>
</template>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}

.drawer {
  width: 340px;
  max-width: 90vw;
  background: var(--color-bg-elevated);
  border-left: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  height: 100%;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.3);
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.drawer-title {
  font-weight: 600;
  font-size: 15px;
  color: var(--color-text-primary);
}

.close-btn {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
}

.close-btn:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-muted);
}

.drawer-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.delete-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--color-error);
  cursor: pointer;
}

.delete-toggle input[type='checkbox'] {
  accent-color: var(--color-error);
}

.type-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.type-label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text-secondary);
  letter-spacing: 0.05em;
  margin: 0;
}

.type-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}

.type-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-primary);
  cursor: pointer;
  padding: 4px 0;
}

.type-checkbox input[type='checkbox'] {
  accent-color: var(--color-accent);
}

/* Slide transition */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}
.slide-enter-from .drawer,
.slide-leave-to .drawer {
  transform: translateX(100%);
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
}
</style>
