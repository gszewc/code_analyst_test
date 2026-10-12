<script setup lang="ts">
import { computed, ref } from 'vue'
import { api, ApiRequestError } from '@/api/client'
import type { UploadSessionResponse } from '@/api/types'
import { UploadCloudIcon, XCircleIcon } from 'lucide-vue-next'

const props = withDefaults(defineProps<{ projectId: string; compact?: boolean }>(), {
  compact: false,
})
const emit = defineEmits<{
  uploadComplete: [session: UploadSessionResponse]
  error: [message: string]
}>()

const isDragOver = ref(false)
const progress = ref(0)
const uploading = ref(false)
const errorMessage = ref('')

const uploadZoneClasses = computed(() => ({
  dragover: isDragOver.value,
  uploading: uploading.value,
  compact: props.compact,
}))

function isZipFile(file: File): boolean {
  return (
    file.type === 'application/zip' ||
    file.type === 'application/x-zip-compressed' ||
    file.name.toLowerCase().endsWith('.zip')
  )
}

async function handleFile(file: File) {
  if (!isZipFile(file)) {
    errorMessage.value = `"${file.name}" is not a ZIP file. Only .zip archives are accepted.`
    emit('error', errorMessage.value)
    return
  }

  errorMessage.value = ''
  uploading.value = true
  progress.value = 0

  try {
    const session = await api.files.upload(props.projectId, file, (pct) => {
      progress.value = pct
    })
    emit('uploadComplete', session)
  } catch (err) {
    const msg = err instanceof ApiRequestError ? err.detail : 'Upload failed — please try again'
    errorMessage.value = msg
    emit('error', msg)
  } finally {
    uploading.value = false
  }
}

function onDrop(event: DragEvent) {
  isDragOver.value = false
  const file = event.dataTransfer?.files[0]
  if (file) handleFile(file)
}

function onFileInput(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) handleFile(file)
}
</script>

<template>
  <div
    class="upload-zone"
    :class="uploadZoneClasses"
    data-testid="upload-zone"
    @dragover.prevent="isDragOver = true"
    @dragleave="isDragOver = false"
    @drop.prevent="onDrop"
  >
    <input
      id="file-picker"
      type="file"
      accept=".zip"
      class="file-input"
      data-testid="upload-zone-input"
      @change="onFileInput"
    >

    <template v-if="!uploading">
      <div class="upload-inline">
        <UploadCloudIcon
          :size="32"
          class="upload-icon"
        />
        <p
          class="upload-text"
          data-testid="upload-zone-action-text"
        >
          Drag and drop a <strong>.zip</strong> archive here
        </p>
        <p class="upload-sub">
          or
          <label
            for="file-picker"
            class="pick-link"
            data-testid="upload-zone-browse-link"
          >
            browse files
          </label>
        </p>
      </div>
    </template>

    <template v-else>
      <div
        class="progress-container"
        data-testid="upload-zone-progress"
      >
        <p class="progress-label">
          Uploading… {{ progress }}%
        </p>
        <div class="progress-track">
          <div
            class="progress-bar"
            :style="{ width: `${progress}%` }"
          />
        </div>
      </div>
    </template>

    <!-- Error message -->
    <div
      v-if="errorMessage"
      class="upload-error"
      data-testid="upload-zone-error"
    >
      <XCircleIcon :size="14" />
      {{ errorMessage }}
    </div>
  </div>
</template>

<style scoped>
.upload-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: 40px 24px;
  text-align: center;
  transition: all var(--transition-normal);
  cursor: pointer;
  background: var(--color-bg-elevated);
  position: relative;
}

.upload-zone.compact {
  padding: 14px 14px;
  border-radius: var(--radius-md);
}

.upload-zone.dragover {
  border-color: var(--color-accent);
  background: var(--color-accent-muted);
}

.file-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  width: 100%;
  height: 100%;
}

.upload-inline {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.upload-icon {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.upload-zone.compact .upload-icon {
  width: 20px;
  height: 20px;
}

.upload-text {
  font-size: 15px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.upload-zone.compact .upload-text {
  font-size: 13px;
}

.upload-sub {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 0;
  overflow-wrap: anywhere;
  white-space: nowrap;
}

.upload-zone.compact .upload-sub {
  font-size: 12px;
}

.pick-link {
  color: var(--color-accent);
  cursor: pointer;
  text-decoration: underline;
}

.progress-container {
  padding: 8px 0;
}

.progress-label {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0 0 10px;
}

.progress-track {
  background: var(--color-bg-muted);
  border-radius: 100px;
  height: 8px;
  overflow: hidden;
}

.progress-bar {
  background: var(--color-accent);
  height: 100%;
  border-radius: 100px;
  transition: width 200ms ease;
}

.upload-error {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 13px;
  color: var(--color-error);
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  text-align: left;
}

.upload-zone.compact .upload-error {
  font-size: 12px;
  padding: 6px 10px;
}
</style>
