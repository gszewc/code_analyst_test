<script setup lang="ts">
import { computed } from 'vue'
import type { AnalysisJobResponse } from '@/api/types'
import { CheckCircleIcon, XCircleIcon, ClockIcon, LoaderIcon } from 'lucide-vue-next'

const props = defineProps<{
  jobs: AnalysisJobResponse[]
}>()

function formatDuration(job: AnalysisJobResponse): string {
  if (!job.started_at) return '—'
  const end = job.completed_at ? new Date(job.completed_at) : new Date()
  const start = new Date(job.started_at)
  const secs = Math.round((end.getTime() - start.getTime()) / 1000)
  if (secs < 60) return `${secs}s`
  return `${Math.floor(secs / 60)}m ${secs % 60}s`
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}

const statusIcon: Record<string, unknown> = {
  pending: ClockIcon,
  running: LoaderIcon,
  completed: CheckCircleIcon,
  failed: XCircleIcon,
}

const statusClass: Record<string, string> = {
  pending: 'status-pending',
  running: 'status-running',
  completed: 'status-completed',
  failed: 'status-failed',
}
</script>

<template>
  <div class="job-table-wrapper">
    <table
      v-if="jobs.length > 0"
      class="job-table"
    >
      <thead>
        <tr>
          <th>Started</th>
          <th>Duration</th>
          <th>Status</th>
          <th>Error</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="job in jobs"
          :key="job.id"
        >
          <td>{{ formatDate(job.started_at) }}</td>
          <td>{{ formatDuration(job) }}</td>
          <td>
            <span :class="['status-badge', statusClass[job.status]]">
              {{ job.status }}
            </span>
          </td>
          <td class="error-cell">
            {{ job.error_message ?? '—' }}
          </td>
        </tr>
      </tbody>
    </table>
    <p
      v-else
      class="no-jobs"
    >
      No analysis jobs yet
    </p>
  </div>
</template>

<style scoped>
.job-table-wrapper {
  overflow-x: auto;
}

.job-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.job-table th {
  text-align: left;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom: 1px solid var(--color-border);
}

.job-table td {
  padding: 10px 12px;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border-subtle);
}

.error-cell {
  font-family: var(--font-mono);
  font-size: 12px;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-error) !important;
}

.no-jobs {
  font-size: 14px;
  color: var(--color-text-muted);
  padding: 24px 0;
  text-align: center;
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
