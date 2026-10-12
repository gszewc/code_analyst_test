<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/api/client'
import { useCodeHighlight } from '@/composables/useCodeHighlight'
import 'highlight.js/styles/github-dark.css'

const props = defineProps<{
  projectId: string
  filepath: string
  scrollToLine?: number
}>()

const emit = defineEmits<{
  findInGraph: [name: string, position: { x: number; y: number }]
}>()

const MAX_SIZE = 1_048_576 // 1 MB

const { data, isLoading, isError } = useQuery({
  queryKey: computed(() => ['file-content', props.projectId, props.filepath]),
  queryFn: () => api.files.getContent(props.projectId, props.filepath),
  enabled: computed(() => !!props.filepath),
})

const { highlight } = useCodeHighlight()
const highlightedHtml = ref<string>('')
const containerRef = ref<HTMLElement | null>(null)

const isTooLarge = computed(() =>
  data.value ? data.value.content.length > MAX_SIZE : false
)

const language = computed(() => {
  const ext = props.filepath.split('.').pop()?.toLowerCase() ?? ''
  const langMap: Record<string, string> = {
    py: 'python', js: 'javascript', ts: 'typescript',
    vue: 'vue', html: 'html', css: 'css', json: 'json',
    md: 'markdown', yaml: 'yaml', yml: 'yaml',
    sh: 'bash', txt: 'text',
  }
  return langMap[ext] ?? 'text'
})

watch(
  () => [data.value, props.filepath] as const,
  async ([fileData]) => {
    if (!fileData || isTooLarge.value) {
      highlightedHtml.value = ''
      return
    }
    highlightedHtml.value = highlight(fileData.content, language.value)
    await nextTick()
    goToLine(props.scrollToLine)
  },
  { immediate: true }
)

watch(() => props.scrollToLine, goToLine)

function goToLine(line: number | undefined) {
  if (!line || !containerRef.value) return
  const lineEl = containerRef.value.querySelector(`[data-line="${line}"]`) as HTMLElement | null
  lineEl?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

function handleCodeClick(e: MouseEvent) {
  if (!(e.ctrlKey || e.metaKey)) return
  const selection = window.getSelection()
  if (!selection) return
  const text = selection.toString().trim()
  if (!text || /\s/.test(text)) return
  e.preventDefault()
  emit('findInGraph', text, { x: e.clientX, y: e.clientY })
}
</script>

<template>
  <div class="code-viewer">
    <div class="viewer-bar">
      <span class="filepath">{{ filepath }}</span>
    </div>

    <div
      v-if="isLoading"
      class="viewer-state"
    >
      Loading…
    </div>
    <div
      v-else-if="isError"
      class="viewer-state error"
    >
      File not found or unavailable
    </div>
    <div
      v-else-if="isTooLarge"
      class="viewer-state warning"
    >
      File is too large to display (> 1 MB)
    </div>

    <div
      v-else
      ref="containerRef"
      class="code-container"
      @click="handleCodeClick"
      v-html="highlightedHtml"
    />
  </div>
</template>

<style scoped>
.code-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-base);
}

.viewer-bar {
  padding: 8px 16px;
  background: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border-subtle);
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
}

.filepath {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.viewer-state {
  padding: 24px;
  font-size: 14px;
  color: var(--color-text-muted);
}

.viewer-state.error { color: var(--color-error); }
.viewer-state.warning { color: var(--color-warning); }

.code-container {
  overflow: auto;
  flex: 1;
}

.code-container :deep(.hljs-table) {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.5;
}

.code-container :deep(.line-num) {
  width: 1%;
  min-width: 40px;
  white-space: nowrap;
  text-align: right;
  padding: 0 12px 0 8px;
  user-select: none;
  color: var(--color-text-tertiary, #6e7681);
  opacity: 0.6;
  vertical-align: top;
  border-right: 1px solid var(--color-border-subtle);
}

.code-container :deep(.line-code) {
  padding-left: 12px;
  white-space: pre;
}
</style>
