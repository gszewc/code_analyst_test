<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { api } from '@/api/client'
import type { FileEntry, UploadSessionResponse } from '@/api/types'
import UploadZone from '@/components/files/UploadZone.vue'
import FileTreeNode from '@/components/files/FileTreeNode.vue'
import CodeViewer from '@/components/code/CodeViewer.vue'
import { FolderIcon, CheckCircleIcon, XCircleIcon } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useGraphStore } from '@/stores/useGraphStore'
import { useNodeLookup } from '@/composables/useNodeLookup'
import { useToast } from '@/composables/useToast'
import ContextMenu from '@/components/ui/ContextMenu.vue'
import type { ContextMenuItem } from '@/components/ui/ContextMenu.vue'

const route = useRoute()
const queryClient = useQueryClient()
const projectId = computed(() => route.params.id as string)
const routeFilepath = computed(() => {
  const fp = route.params.filepath
  return Array.isArray(fp) ? fp.join('/') : fp ?? ''
})
const routeLine = computed(() => {
  const l = route.query.line
  return l ? parseInt(String(l), 10) : undefined
})

const selectedFile = ref<string>(routeFilepath.value)
const uploadSessions = ref<UploadSessionResponse[]>([])
const uploadError = ref('')
const lastUpload = ref<UploadSessionResponse | null>(null)

const router = useRouter()
const graphStore = useGraphStore()
const { findNode, findFileNode } = useNodeLookup()
const { showToast } = useToast()

const contextMenuVisible = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextMenuItems = ref<ContextMenuItem[]>([])

watch(routeFilepath, (fp) => { selectedFile.value = fp })

// File list query
const { data: fileData, isLoading: filesLoading } = useQuery({
  queryKey: computed(() => ['files', projectId.value]),
  queryFn: () => api.files.list(projectId.value),
  enabled: computed(() => !!projectId.value),
})

const files = computed(() => fileData.value?.files ?? [])

function handleUploadComplete(session: UploadSessionResponse) {
  uploadSessions.value.push(session)
  lastUpload.value = session
  uploadError.value = ''
  queryClient.invalidateQueries({ queryKey: ['files', projectId.value] })
}

function selectFile(path: string) {
  selectedFile.value = path
}

async function handleFileFindInGraph(filepath: string, position: { x: number; y: number }) {
  contextMenuVisible.value = false
  contextMenuX.value = position.x
  contextMenuY.value = position.y
  contextMenuItems.value = [
    {
      label: 'Find in Graph',
      action: async () => {
        const node = await findFileNode(projectId.value, filepath)
        if (!node) {
          showToast(`No graph node found for "${filepath}"`, 'info')
          return
        }
        graphStore.setPendingNode(node.id)
        router.push({
          name: 'project-graph',
          params: { id: projectId.value },
          query: { nodeId: node.id },
        })
      },
    },
  ]
  contextMenuVisible.value = true
}

async function handleCodeFindInGraph(name: string, position: { x: number; y: number }) {
  contextMenuVisible.value = false
  contextMenuX.value = position.x
  contextMenuY.value = position.y
  contextMenuItems.value = [
    {
      label: `Find "${name}" in Graph`,
      action: async () => {
        const node = await findNode(projectId.value, name)
        if (!node) {
          showToast(`No graph node found for "${name}"`, 'info')
          return
        }
        graphStore.setPendingNode(node.id)
        router.push({
          name: 'project-graph',
          params: { id: projectId.value },
          query: { nodeId: node.id },
        })
      },
    },
  ]
  contextMenuVisible.value = true
}

// ── Resizable tree panel ──────────────────────────────────────────────────
const MIN_WIDTH = 180
const MAX_WIDTH = 500
const treePanelWidth = ref(260)
const isResizing = ref(false)

function onResizeStart(e: MouseEvent) {
  e.preventDefault()
  isResizing.value = true
  const startX = e.clientX
  const startWidth = treePanelWidth.value

  function onMouseMove(ev: MouseEvent) {
    const delta = ev.clientX - startX
    treePanelWidth.value = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth + delta))
  }

  function onMouseUp() {
    isResizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

onBeforeUnmount(() => {
  isResizing.value = false
})
</script>

<template>
  <div
    class="files-page"
    :class="{ 'is-resizing': isResizing }"
  >
    <!-- Upload section -->
    <div
      class="upload-section"
      :style="{ maxHeight: '150px' }"
      data-testid="upload-panel"
      data-upload-mode="compact"
    >
      <div
        class="upload-panel-body"
        data-testid="upload-panel-body"
      >
        <UploadZone
          :project-id="projectId"
          compact
          @upload-complete="handleUploadComplete"
          @error="uploadError = $event"
        />
        <div
          v-if="lastUpload && lastUpload.file_count > 0"
          class="upload-success"
          data-testid="upload-panel-status"
        >
          <CheckCircleIcon :size="14" />
          Uploaded {{ lastUpload.file_count }} file{{ lastUpload.file_count !== 1 ? 's' : '' }}
        </div>
        <div
          v-if="lastUpload && lastUpload.file_count === 0"
          class="upload-warning"
          data-testid="upload-panel-status"
        >
          <XCircleIcon :size="14" />
          ZIP uploaded but no parseable files were found
        </div>
      </div>
    </div>

    <!-- File browser -->
    <div
      class="browser-layout"
      data-testid="files-browser-layout"
    >
      <!-- Tree sidebar -->
      <aside
        class="tree-panel"
        :style="{ width: `${treePanelWidth}px` }"
      >
        <div class="tree-header">
          <FolderIcon :size="14" />
          <span>Files</span>
        </div>
        <div
          v-if="filesLoading"
          class="tree-loading"
        >
          Loading…
        </div>
        <div
          v-else-if="files.length === 0"
          class="tree-empty"
        >
          No files yet — upload a ZIP above
        </div>
        <div
          v-else
          class="tree-list"
        >
          <FileTreeNode
            v-for="entry in files"
            :key="entry.path"
            :entry="entry"
            :selected-path="selectedFile"
            :project-id="projectId"
            @select="selectFile"
            @find-in-graph="(path, pos) => handleFileFindInGraph(path, pos)"
          />
        </div>
      </aside>

      <!-- Resize handle -->
      <div
        class="resize-handle"
        @mousedown="onResizeStart"
      />

      <!-- Code viewer -->
      <div class="viewer-panel">
        <CodeViewer
          v-if="selectedFile"
          :project-id="projectId"
          :filepath="selectedFile"
          :scroll-to-line="routeLine"
          @find-in-graph="(name, pos) => handleCodeFindInGraph(name, pos)"
        />
        <div
          v-else
          class="viewer-empty"
        >
          Select a file from the tree to view its contents
        </div>
      </div>
    </div>

    <ContextMenu
      v-if="contextMenuVisible"
      :x="contextMenuX"
      :y="contextMenuY"
      :items="contextMenuItems"
      @close="contextMenuVisible = false"
    />
  </div>
</template>

<style scoped>
.files-page {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: 16px;
  gap: 20px;
  box-sizing: border-box;
}

.files-page.is-resizing {
  user-select: none;
  cursor: col-resize;
}

.upload-section {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 12px 12px;
  overflow: hidden;
  max-height: 100px;
  transition: max-height var(--transition-normal), min-height var(--transition-normal), padding var(--transition-normal);
}

.upload-panel-body {
  display: grid;
  gap: 4px;
}

.upload-success {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 0;
  font-size: 13px;
  color: var(--color-success);
}

.upload-warning {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 0;
  font-size: 13px;
  color: var(--color-warning);
}

.browser-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  min-height: 400px;
}

.tree-panel {
  flex-shrink: 0;
  background: var(--color-bg-elevated);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.tree-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  border-bottom: 1px solid var(--color-border-subtle);
}

.tree-loading, .tree-empty {
  padding: 16px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.tree-list {
  padding: 4px 0;
  overflow-y: auto;
  flex: 1;
}

.resize-handle {
  width: 4px;
  flex-shrink: 0;
  cursor: col-resize;
  background: var(--color-border);
  transition: background var(--transition-fast);
}

.resize-handle:hover,
.is-resizing .resize-handle {
  background: var(--color-accent);
}

.viewer-panel {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: var(--color-bg-base);
}

.viewer-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-muted);
  font-size: 14px;
}

@media (max-width: 1280px) {
  .files-page {
    gap: 16px;
    padding: 14px;
  }

  .upload-section {
    padding: 12px 14px;
  }
}

@media (max-height: 760px) {
  .browser-layout {
    min-height: 360px;
  }
}
</style>
