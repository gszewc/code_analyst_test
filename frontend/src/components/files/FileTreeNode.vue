<script setup lang="ts">
import { ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/api/client'
import type { FileEntry } from '@/api/types'
import { ChevronRightIcon, ChevronDownIcon, FolderIcon, FolderOpenIcon, FileIcon } from 'lucide-vue-next'

const props = defineProps<{
  entry: FileEntry
  projectId: string
  selectedPath?: string
  depth?: number
}>()

const emit = defineEmits<{
  select: [path: string]
  findInGraph: [path: string, position: { x: number; y: number }]
}>()

const isOpen = ref(false)

// Lazy-load children when a directory is expanded
const { data: childData, refetch } = useQuery({
  queryKey: ['files', props.projectId, props.entry.path],
  queryFn: () => api.files.list(props.projectId, props.entry.path),
  enabled: false,
})

async function toggle() {
  if (!props.entry.is_directory) return
  isOpen.value = !isOpen.value
  if (isOpen.value && !childData.value) {
    await refetch()
  }
}

function handleClick(e: MouseEvent) {
  if (props.entry.is_directory) {
    toggle()
    return
  }
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault()
    emit('findInGraph', props.entry.path, { x: e.clientX, y: e.clientY })
    return
  }
  emit('select', props.entry.path)
}
</script>

<template>
  <div
    class="tree-node"
    :style="{ paddingLeft: depth ? '10px' : '0px' }"
  >
    <div
      class="node-row"
      :class="{
        'is-dir': entry.is_directory,
        'is-selected': !entry.is_directory && selectedPath === entry.path,
      }"
      @click="handleClick"
    >
      <!-- Chevron for directories -->
      <span
        v-if="entry.is_directory"
        class="chevron"
      >
        <ChevronDownIcon
          v-if="isOpen"
          :size="12"
        />
        <ChevronRightIcon
          v-else
          :size="12"
        />
      </span>
      <span
        v-else
        class="chevron-spacer"
      />

      <!-- Icon -->
      <component
        :is="entry.is_directory ? (isOpen ? FolderOpenIcon : FolderIcon) : FileIcon"
        :size="14"
        class="node-icon"
      />

      <!-- Name -->
      <span class="node-name">{{ entry.name }}</span>
    </div>

    <!-- Children -->
    <div v-if="isOpen && childData">
      <FileTreeNode
        v-for="child in childData.files"
        :key="child.path"
        :entry="child"
        :project-id="projectId"
        :selected-path="selectedPath"
        :depth="(depth ?? 0) + 1"
        @select="emit('select', $event)"
        @find-in-graph="(path, pos) => emit('findInGraph', path, pos)"
      />
    </div>
  </div>
</template>

<style scoped>
.tree-node {
  user-select: none;
}

.node-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px 3px 4px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background var(--transition-fast);
  border-radius: var(--radius-sm);
  margin: 0 4px;
}

.node-row:hover {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}

.node-row.is-selected {
  background: var(--color-accent-muted);
  color: var(--color-accent);
}

.chevron {
  width: 14px;
  display: flex;
  align-items: center;
  color: var(--color-text-muted);
}

.chevron-spacer {
  width: 14px;
}

.node-icon {
  color: inherit;
  flex-shrink: 0;
}

.node-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: 12px;
}
</style>
