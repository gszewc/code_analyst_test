<script setup lang="ts">
import { computed } from 'vue'
import { PlayIcon, LoaderIcon, AlertCircleIcon } from 'lucide-vue-next'

const props = defineProps<{
  state: 'idle' | 'running' | 'error'
  hasUploads: boolean
}>()

const emit = defineEmits<{
  analyse: []
}>()

const isDisabled = computed(() => props.state === 'running' || !props.hasUploads)

const tooltip = computed(() => {
  if (!props.hasUploads) return 'Upload source code first'
  if (props.state === 'running') return 'Analysis is running'
  return undefined
})
</script>

<template>
  <button
    class="analyse-btn"
    :class="[`state-${state}`, { disabled: isDisabled }]"
    :disabled="isDisabled"
    :title="tooltip"
    @click="emit('analyse')"
  >
    <LoaderIcon
      v-if="state === 'running'"
      :size="16"
      class="spin"
    />
    <AlertCircleIcon
      v-else-if="state === 'error'"
      :size="16"
    />
    <PlayIcon
      v-else
      :size="16"
    />
    <span>{{ state === 'running' ? 'Analysing…' : state === 'error' ? 'Retry Analysis' : 'Analyse' }}</span>
  </button>
</template>

<style scoped>
.analyse-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all var(--transition-fast);
  background: var(--color-accent);
  color: #000;
}

.analyse-btn:hover:not(.disabled) {
  background: var(--color-accent-hover);
}

.analyse-btn.state-running {
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

.analyse-btn.state-error {
  background: var(--color-danger-bg-hover);
  color: var(--color-danger-fg);
  border: 1px solid var(--color-danger-border);
}

.analyse-btn.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
