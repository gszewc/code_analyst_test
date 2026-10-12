<script setup lang="ts">
import type { ProjectResponse, AnalysisStatus } from '@/api/types'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { FolderIcon, Trash2Icon, PencilIcon } from 'lucide-vue-next'

const props = defineProps<{
  project: ProjectResponse
  latestStatus?: AnalysisStatus
}>()

const emit = defineEmits<{
  open: [projectId: string]
  rename: [project: ProjectResponse]
  delete: [project: ProjectResponse]
}>()

const statusLabel: Record<string, string> = {
  pending: 'Pending',
  running: 'Running',
  completed: 'Analysed',
  failed: 'Failed',
}

const statusClass: Record<string, string> = {
  pending: 'status-pending',
  running: 'status-running',
  completed: 'status-completed',
  failed: 'status-failed',
}

const formattedDate = computed(() =>
  new Date(props.project.created_at).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
)
</script>

<template>
  <div class="project-card">
    <div class="card-header">
      <RouterLink
        :to="`/projects/${project.id}/graph`"
        class="card-title"
        @click="emit('open', project.id)"
      >
        <FolderIcon :size="16" />
        <span>{{ project.name }}</span>
      </RouterLink>
      <div class="card-actions">
        <button
          class="icon-btn"
          title="Rename"
          @click.stop="emit('rename', project)"
        >
          <PencilIcon :size="14" />
        </button>
        <button
          class="icon-btn danger"
          title="Delete"
          @click.stop="emit('delete', project)"
        >
          <Trash2Icon :size="14" />
        </button>
      </div>
    </div>

    <p
      v-if="project.description"
      class="card-description"
    >
      {{ project.description }}
    </p>
    <p
      v-else
      class="card-description muted"
    >
      No description
    </p>

    <div class="card-footer">
      <span class="card-date">{{ formattedDate }}</span>
      <span
        v-if="latestStatus"
        :class="['status-badge', statusClass[latestStatus] ?? '']"
      >
        {{ statusLabel[latestStatus] ?? latestStatus }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.project-card {
  background-color: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px;
  transition: border-color var(--transition-fast), transform var(--transition-fast);
  cursor: pointer;
}

.project-card:hover {
  border-color: var(--color-accent-border);
  transform: translateY(-1px);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-primary);
  text-decoration: none;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
}

.card-title:hover {
  color: var(--color-accent);
}

.card-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.project-card:hover .card-actions {
  opacity: 1;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.icon-btn:hover {
  background-color: var(--color-bg-overlay);
  color: var(--color-text-primary);
}

.icon-btn.danger:hover {
  background-color: var(--color-danger-bg-hover);
  color: var(--color-error);
}

.card-description {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0 0 12px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-description.muted {
  color: var(--color-text-muted);
  font-style: italic;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-date {
  font-size: 12px;
  color: var(--color-text-muted);
}

.status-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 100px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.status-pending { background: var(--color-status-pending-bg); color: var(--color-status-pending-fg); }
.status-running { background: var(--color-status-running-bg); color: var(--color-status-running-fg); }
.status-completed { background: var(--color-status-completed-bg); color: var(--color-status-completed-fg); }
.status-failed { background: var(--color-status-failed-bg); color: var(--color-status-failed-fg); }
</style>
