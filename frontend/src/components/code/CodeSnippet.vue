<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/api/client'
import { useCodeHighlight } from '@/composables/useCodeHighlight'
import 'highlight.js/styles/github-dark.css'

const props = defineProps<{
  projectId: string
  filepath: string
  startLine: number
  endLine: number
}>()

const { data, isLoading, isError } = useQuery({
  queryKey: computed(() => ['file-content', props.projectId, props.filepath]),
  queryFn: () => api.files.getContent(props.projectId, props.filepath),
  enabled: computed(() => !!props.filepath),
})

const { highlight } = useCodeHighlight()
const highlightedHtml = ref('')

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
  () => [data.value, props.startLine, props.endLine],
  ([fileData]) => {
    if (!fileData) return
    highlightedHtml.value = highlight(
      (fileData as typeof data.value)!.content,
      language.value,
      props.startLine,
      props.endLine,
    )
  },
  { immediate: true }
)
</script>

<template>
  <div class="code-snippet">
    <div
      v-if="isLoading"
      class="snippet-state"
    >
      Loading…
    </div>
    <div
      v-else-if="isError"
      class="snippet-state error"
    >
      Source not available
    </div>
    <div
      v-else
      class="snippet-content"
      v-html="highlightedHtml"
    />
  </div>
</template>

<style scoped>
.code-snippet {
  font-size: 12px;
  background: var(--color-bg-base);
}

.snippet-state {
  padding: 4px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.snippet-state.error { color: var(--color-error); }

.snippet-content :deep(.hljs-table) {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
}

.snippet-content :deep(.line-num) {
  width: 1%;
  min-width: 36px;
  white-space: nowrap;
  text-align: right;
  padding: 0 8px 0 4px;
  user-select: none;
  color: var(--color-text-tertiary, #6e7681);
  opacity: 0.6;
  vertical-align: top;
}

.snippet-content :deep(.line-code) {
  padding-left: 8px;
  white-space: pre;
}
</style>
