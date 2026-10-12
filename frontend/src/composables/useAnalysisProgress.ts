import { ref, onUnmounted } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { api } from '@/api/client'
import type { AnalysisJobResponse, ProgressEvent, CompleteEvent } from '@/api/types'

export function useAnalysisProgress(projectId: string) {
  const progress = ref(0)
  const currentFile = ref<string | null>(null)
  const isRunning = ref(false)
  const isComplete = ref(false)
  const isFailed = ref(false)
  const errorMessage = ref<string | null>(null)

  let eventSource: EventSource | null = null
  let pollInterval: ReturnType<typeof setInterval> | null = null
  let currentJobId: string | null = null

  const queryClient = useQueryClient()

  function stopAll() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  function startPolling(jobId: string) {
    stopAll()
    pollInterval = setInterval(async () => {
      try {
        const job = await api.analysis.getJob(jobId)
        handleJobUpdate(job)
      } catch {
        // tolerate poll errors
      }
    }, 2000)
  }

  function handleJobUpdate(job: AnalysisJobResponse) {
    progress.value = job.progress ?? progress.value
    if (job.status === 'completed') {
      handleComplete({ job_id: job.id, status: 'completed', error_message: null, node_count: 0, relationship_count: 0 })
    } else if (job.status === 'failed') {
      handleComplete({ job_id: job.id, status: 'failed', error_message: job.error_message, node_count: 0, relationship_count: 0 })
    }
  }

  function handleComplete(event: CompleteEvent) {
    stopAll()
    isRunning.value = false
    progress.value = 100
    currentFile.value = null

    if (event.status === 'completed') {
      isComplete.value = true
    } else {
      isFailed.value = true
      errorMessage.value = event.error_message
    }

    // Invalidate graph queries to trigger refresh
    queryClient.invalidateQueries({ queryKey: ['projectNodes', projectId] })
    queryClient.invalidateQueries({ queryKey: ['projectStats', projectId] })
    queryClient.invalidateQueries({ queryKey: ['jobs', projectId] })
  }

  function startSSE(jobId: string) {
    const url = api.analysis.streamUrl(jobId)
    eventSource = new EventSource(url)

    eventSource.addEventListener('progress', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as ProgressEvent
        progress.value = data.percentage
        currentFile.value = data.current_file
      } catch {
        // ignore parse errors
      }
    })

    eventSource.addEventListener('complete', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as CompleteEvent
        handleComplete(data)
      } catch {
        // ignore parse errors
      }
    })

    eventSource.addEventListener('error', () => {
      // SSE connection failed — fall back to polling
      if (eventSource) {
        eventSource.close()
        eventSource = null
      }
      if (currentJobId) startPolling(currentJobId)
    })
  }

  // Handle page visibility changes to reconnect SSE
  function onVisibilityChange() {
    if (document.visibilityState === 'visible' && isRunning.value && currentJobId) {
      if (!eventSource && !pollInterval) {
        startSSE(currentJobId)
      }
    }
  }

  document.addEventListener('visibilitychange', onVisibilityChange)

  function start(job: AnalysisJobResponse) {
    stopAll()
    currentJobId = job.id
    isRunning.value = true
    isComplete.value = false
    isFailed.value = false
    errorMessage.value = null
    progress.value = 0
    currentFile.value = null

    startSSE(job.id)
  }

  onUnmounted(() => {
    stopAll()
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })

  return {
    progress,
    currentFile,
    isRunning,
    isComplete,
    isFailed,
    errorMessage,
    start,
    stop: stopAll,
  }
}
