<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import type { GraphNode } from '@/api/types'
import { getNodeColor } from '@/constants/nodeColors'
import { useGraphStore } from '@/stores/useGraphStore'
import { useAppStore } from '@/stores/useAppStore'
import { api, ApiRequestError } from '@/api/client'
import CodeSnippet from '@/components/code/CodeSnippet.vue'
import { XIcon, ExternalLinkIcon, ClipboardIcon, CheckIcon, SparklesIcon } from 'lucide-vue-next'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{
  projectId: string
}>()

const graphStore = useGraphStore()
const appStore = useAppStore()
const router = useRouter()

const node = computed(() => graphStore.selectedNode)
const isOpen = computed(() => !!node.value)

function close() {
  graphStore.selectNode(null)
}

// AI docs generation
const docsHtml = ref('')
const isGenerating = ref(false)
const docsError = ref('')
const copied = ref(false)
const docsRawMarkdown = ref('')

watch(node, () => {
  docsHtml.value = ''
  docsError.value = ''
  docsRawMarkdown.value = ''
})

const canGenerateDocs = computed(() =>
  node.value && ['Class', 'Function', 'Method'].includes(node.value.type)
)

async function generateDocs() {
  if (!node.value) return
  isGenerating.value = true
  docsError.value = ''
  docsHtml.value = ''
  docsRawMarkdown.value = ''
  try {
    const result = await api.llm.generateNodeDocs(props.projectId, node.value.id)
    docsRawMarkdown.value = result.content
    docsHtml.value = DOMPurify.sanitize(await marked.parse(result.content))
  } catch (err) {
    if (err instanceof ApiRequestError && err.status === 408) {
      docsError.value = 'Request timed out — the LLM took too long. Try again.'
    } else {
      docsError.value = err instanceof ApiRequestError ? err.detail : 'Failed to generate docs'
    }
  } finally {
    isGenerating.value = false
  }
}

async function copyDocs() {
  if (!docsRawMarkdown.value) return
  await navigator.clipboard.writeText(docsRawMarkdown.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function goToFile() {
  if (!node.value?.source_file) return
  router.push({
    name: 'project-file-view',
    params: { id: props.projectId, filepath: node.value.source_file },
    query: node.value.start_line ? { line: node.value.start_line } : {},
  })
}

const nodeColor = computed(() => node.value ? getNodeColor(node.value.type) : '#808080')
</script>

<template>
  <Teleport to="body">
    <transition name="slide">
      <div
        v-if="isOpen && node"
        class="panel-backdrop"
        @click.self="close"
      >
        <aside class="detail-panel">
          <!-- Header -->
          <div class="panel-header">
            <div
              class="node-type-badge"
              :style="{ background: `${nodeColor}22`, color: nodeColor, borderColor: `${nodeColor}44` }"
            >
              {{ node.type }}
            </div>
            <button
              class="close-btn"
              @click="close"
            >
              <XIcon :size="16" />
            </button>
          </div>

          <!-- Node info -->
          <div class="panel-body">
            <h3 class="node-name">
              {{ node.name }}
            </h3>

            <div
              v-if="node.source_file"
              class="info-row"
            >
              <span class="info-label">File</span>
              <button
                class="file-link"
                @click="goToFile"
              >
                {{ node.source_file }}
                <ExternalLinkIcon :size="12" />
              </button>
            </div>

            <div
              v-if="node.start_line"
              class="info-row"
            >
              <span class="info-label">Lines</span>
              <span class="info-value">{{ node.start_line }}–{{ node.end_line ?? node.start_line }}</span>
            </div>

            <!-- Metrics -->
            <div
              v-if="(node as Record<string, unknown>).loc || (node as Record<string, unknown>).complexity"
              class="metrics-row"
            >
              <div
                v-if="(node as Record<string, unknown>).loc"
                class="metric"
              >
                <span class="metric-value">{{ (node as Record<string, unknown>).loc as number }}</span>
                <span class="metric-label">LOC</span>
              </div>
              <div
                v-if="(node as Record<string, unknown>).complexity"
                class="metric"
              >
                <span class="metric-value">{{ (node as Record<string, unknown>).complexity as number }}</span>
                <span class="metric-label">Complexity</span>
              </div>
            </div>

            <!-- Code snippet -->
            <div
              v-if="node.source_file && node.start_line"
              class="snippet-section"
            >
              <CodeSnippet
                :project-id="projectId"
                :filepath="node.source_file"
                :start-line="node.start_line"
                :end-line="node.end_line ?? node.start_line"
              />
            </div>

            <!-- AI docs -->
            <div
              v-if="canGenerateDocs"
              class="docs-section"
            >
              <div class="docs-header">
                <span class="docs-title">AI Documentation</span>
                <div class="docs-actions">
                  <button
                    v-if="docsHtml"
                    class="icon-action"
                    :title="copied ? 'Copied!' : 'Copy markdown'"
                    @click="copyDocs"
                  >
                    <CheckIcon
                      v-if="copied"
                      :size="14"
                    />
                    <ClipboardIcon
                      v-else
                      :size="14"
                    />
                  </button>
                  <button
                    class="docs-btn"
                    :disabled="isGenerating || !appStore.isLLMConfigured"
                    :title="!appStore.isLLMConfigured ? 'Configure LLM in Settings' : undefined"
                    @click="generateDocs"
                  >
                    <SparklesIcon :size="14" />
                    {{ isGenerating ? 'Generating…' : docsHtml ? 'Regenerate' : 'Generate docs' }}
                  </button>
                </div>
              </div>

              <div
                v-if="docsHtml"
                class="docs-content"
                v-html="docsHtml"
              />
              <div
                v-if="docsError"
                class="docs-error"
              >
                {{ docsError }}
                <button
                  class="retry-link"
                  @click="generateDocs"
                >
                  Retry
                </button>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.panel-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  pointer-events: none;
  display: flex;
  justify-content: flex-end;
}

.detail-panel {
  width: 380px;
  max-width: 90vw;
  height: 100vh;
  background: var(--color-bg-panel);
  border-left: 1px solid var(--color-border);
  overflow-y: auto;
  pointer-events: all;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border-subtle);
  position: sticky;
  top: 0;
  background: var(--color-bg-panel);
  z-index: 1;
}

.node-type-badge {
  font-size: 12px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 100px;
  border: 1px solid;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.close-btn:hover {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}

.panel-body {
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.node-name {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  word-break: break-all;
}

.info-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.info-label {
  font-size: 12px;
  color: var(--color-text-muted);
  min-width: 44px;
  padding-top: 2px;
}

.info-value {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.file-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--color-accent);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  text-align: left;
  word-break: break-all;
}

.file-link:hover {
  text-decoration: underline;
}

.metrics-row {
  display: flex;
  gap: 16px;
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: var(--color-bg-overlay);
  border-radius: var(--radius-md);
  padding: 8px 14px;
  min-width: 60px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
}

.metric-label {
  font-size: 12px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.snippet-section {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  max-height: 300px;
  overflow-y: auto;
}

.docs-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.docs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.docs-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.docs-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.docs-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  background: var(--color-accent-muted);
  color: var(--color-accent);
  border: 1px solid var(--color-accent-border);
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.docs-btn:hover:not(:disabled) {
  background: var(--color-accent);
  color: #000;
}

.docs-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.icon-action {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.icon-action:hover {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}

.docs-content {
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.docs-content :deep(h1),
.docs-content :deep(h2),
.docs-content :deep(h3) {
  color: var(--color-text-primary);
  font-family: var(--font-display);
  margin: 12px 0 6px;
}

.docs-content :deep(code) {
  font-family: var(--font-mono);
  background: var(--color-bg-overlay);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}

.docs-content :deep(pre code) {
  background: none;
  padding: 0;
}

.docs-content :deep(pre) {
  background: var(--color-bg-overlay);
  padding: 12px;
  border-radius: var(--radius-md);
  overflow-x: auto;
  font-size: 12px;
}

.docs-error {
  font-size: 13px;
  color: var(--color-error);
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.retry-link {
  background: none;
  border: none;
  color: var(--color-accent);
  font-size: 13px;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
  margin-left: auto;
}

/* Slide transition */
.slide-enter-active {
  transition: transform 250ms ease;
}
.slide-leave-active {
  transition: transform 200ms ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
