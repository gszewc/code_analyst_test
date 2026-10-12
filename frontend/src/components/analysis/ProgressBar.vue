<script setup lang="ts">
defineProps<{
  progress: number
  currentFile?: string | null
}>()
</script>

<template>
  <div class="progress-bar-wrapper">
    <div class="progress-info">
      <span class="progress-pct">{{ progress }}%</span>
      <span
        v-if="currentFile"
        class="progress-file"
      >{{ currentFile }}</span>
    </div>
    <div class="progress-track">
      <div
        class="progress-fill"
        :style="{ width: `${progress}%` }"
        :class="{ complete: progress >= 100 }"
      />
    </div>
  </div>
</template>

<style scoped>
.progress-bar-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.progress-pct {
  font-weight: 600;
  color: var(--color-accent);
  font-variant-numeric: tabular-nums;
}

.progress-file {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 12px;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-track {
  height: 8px;
  background: var(--color-bg-muted);
  border-radius: 100px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-accent);
  border-radius: 100px;
  transition: width 300ms ease;
}

.progress-fill.complete {
  background: var(--color-success);
}
</style>
