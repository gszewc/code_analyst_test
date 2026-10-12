<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { SettingsIcon } from 'lucide-vue-next'
import { api, ApiRequestError } from '@/api/client'
import type { ASTNodeType, ASTRelationshipType } from '@/api/types'
import { useAnalysisProgress } from '@/composables/useAnalysisProgress'
import AnalyseButton from '@/components/analysis/AnalyseButton.vue'
import ProgressBar from '@/components/analysis/ProgressBar.vue'
import JobHistoryTable from '@/components/analysis/JobHistoryTable.vue'
import AnalysisOptionsDrawer from '@/components/analysis/AnalysisOptionsDrawer.vue'
import DeleteConfirmationModal from '@/components/analysis/DeleteConfirmationModal.vue'

const route = useRoute()
const queryClient = useQueryClient()
const projectId = computed(() => route.params.id as string)

const analysisProgress = useAnalysisProgress(projectId.value)

// Check whether any files have been uploaded
const { data: fileData } = useQuery({
  queryKey: computed(() => ['files', projectId.value]),
  queryFn: () => api.files.list(projectId.value),
  enabled: computed(() => !!projectId.value),
})
const hasUploads = computed(() => (fileData.value?.total ?? 0) > 0)

// Job history
const { data: jobData } = useQuery({
  queryKey: computed(() => ['jobs', projectId.value]),
  queryFn: () => api.analysis.listJobs(projectId.value),
  enabled: computed(() => !!projectId.value),
})
const jobs = computed(() => jobData.value?.jobs ?? [])

// Fetch defaults
const { data: defaults } = useQuery({
  queryKey: ['analysisDefaults'],
  queryFn: () => api.analysis.getDefaults(),
})

// Analysis options state
const drawerOpen = ref(false)
const deleteGraphData = ref(false)
const enabledNodeTypes = ref<ASTNodeType[]>([])
const enabledRelationshipTypes = ref<ASTRelationshipType[]>([])

// Initialize from defaults when they load
watch(
  () => defaults.value,
  (val) => {
    if (val) {
      deleteGraphData.value = val.delete_graph_data
      enabledNodeTypes.value = [...val.enabled_node_types]
      enabledRelationshipTypes.value = [...val.enabled_relationship_types]
    }
  },
  { immediate: true },
)

// Delete confirmation modal
const showDeleteModal = ref(false)
const graphSummaryLoading = ref(false)
const graphSummaryNodes = ref(0)
const graphSummaryRels = ref(0)

// Start mutation
const startError = ref('')
const btnState = computed(() => {
  if (analysisProgress.isRunning.value) return 'running' as const
  if (analysisProgress.isFailed.value) return 'error' as const
  return 'idle' as const
})

async function handleAnalyse() {
  if (deleteGraphData.value) {
    // Fetch graph summary and show confirmation modal
    graphSummaryLoading.value = true
    showDeleteModal.value = true
    try {
      const summary = await api.analysis.getGraphSummary(projectId.value)
      graphSummaryNodes.value = summary.total_nodes
      graphSummaryRels.value = summary.total_relationships
    } catch {
      graphSummaryNodes.value = 0
      graphSummaryRels.value = 0
    } finally {
      graphSummaryLoading.value = false
    }
  } else {
    doStartAnalysis()
  }
}

const startMutation = useMutation({
  mutationFn: () =>
    api.analysis.start(projectId.value, {
      delete_graph_data: deleteGraphData.value,
      enabled_node_types: enabledNodeTypes.value,
      enabled_relationship_types: enabledRelationshipTypes.value,
    }),
  onSuccess: (job) => {
    startError.value = ''
    analysisProgress.start(job)
    queryClient.invalidateQueries({ queryKey: ['jobs', projectId.value] })
  },
  onError: (err) => {
    startError.value = err instanceof ApiRequestError ? err.detail : 'Failed to start analysis'
  },
})

function doStartAnalysis() {
  showDeleteModal.value = false
  startMutation.mutate()
}

// Success toast (simple)
const showSuccessToast = computed(() => analysisProgress.isComplete.value)
</script>

<template>
  <div class="analysis-page">
    <h2 class="section-title">
      Analysis
    </h2>

    <div class="analysis-card">
      <div class="card-row">
        <AnalyseButton
          :state="btnState"
          :has-uploads="hasUploads"
          @analyse="handleAnalyse"
        />
        <button
          class="options-btn"
          title="Configure analysis options"
          @click="drawerOpen = true"
        >
          <SettingsIcon :size="16" />
          <span>Options</span>
        </button>
        <span
          v-if="startError"
          class="inline-error"
        >{{ startError }}</span>
      </div>

      <!-- Progress -->
      <div
        v-if="analysisProgress.isRunning.value"
        class="progress-section"
      >
        <ProgressBar
          :progress="analysisProgress.progress.value"
          :current-file="analysisProgress.currentFile.value"
        />
      </div>

      <!-- Success toast -->
      <div
        v-if="showSuccessToast"
        class="toast success"
      >
        Analysis complete — graph refreshed
      </div>

      <!-- Error -->
      <div
        v-if="analysisProgress.isFailed.value && analysisProgress.errorMessage.value"
        class="error-panel"
      >
        <strong>Analysis failed:</strong> {{ analysisProgress.errorMessage.value }}
      </div>
    </div>

    <!-- Job history -->
    <div class="history-section">
      <h3 class="section-subtitle">
        Job History
      </h3>
      <JobHistoryTable :jobs="jobs" />
    </div>

    <!-- Options drawer -->
    <AnalysisOptionsDrawer
      :open="drawerOpen"
      :delete-graph-data="deleteGraphData"
      :enabled-node-types="enabledNodeTypes"
      :enabled-relationship-types="enabledRelationshipTypes"
      @close="drawerOpen = false"
      @update:delete-graph-data="deleteGraphData = $event"
      @update:enabled-node-types="enabledNodeTypes = $event"
      @update:enabled-relationship-types="enabledRelationshipTypes = $event"
    />

    <!-- Delete confirmation modal -->
    <DeleteConfirmationModal
      :open="showDeleteModal"
      :total-nodes="graphSummaryNodes"
      :total-relationships="graphSummaryRels"
      :loading="graphSummaryLoading"
      @confirm="doStartAnalysis"
      @cancel="showDeleteModal = false"
    />
  </div>
</template>

<style scoped>
.analysis-page {
  flex: 1;
  min-height: 0;
  padding: 16px;
  box-sizing: border-box;
  max-width: 800px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 20px;
}

.section-subtitle {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 12px;
}

.analysis-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.options-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  border: 1px solid var(--color-border);
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.options-btn:hover {
  background: var(--color-border);
  color: var(--color-text-primary);
}

.inline-error {
  font-size: 13px;
  color: var(--color-error);
}

.progress-section {
  padding-top: 4px;
}

.toast {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 13px;
}

.toast.success {
  background: rgba(86, 211, 100, 0.12);
  color: var(--color-success);
  border: 1px solid rgba(86, 211, 100, 0.2);
}

.error-panel {
  background: rgba(248, 81, 73, 0.08);
  border: 1px solid rgba(248, 81, 73, 0.2);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  font-size: 13px;
  color: var(--color-error);
}

.history-section {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
}
</style>
