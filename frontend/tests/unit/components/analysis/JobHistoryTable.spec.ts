import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import JobHistoryTable from '../../../../src/components/analysis/JobHistoryTable.vue'
import type { AnalysisJobResponse } from '../../../../src/api/types'

function makeJob(status: AnalysisJobResponse['status']): AnalysisJobResponse {
  return {
    id: `job-${status}`,
    project_id: 'p1',
    status,
    progress: null,
    error_message: null,
    started_at: null,
    completed_at: null,
  }
}

describe('JobHistoryTable status badges', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it.each([
    ['pending', 'status-pending'],
    ['running', 'status-running'],
    ['completed', 'status-completed'],
    ['failed', 'status-failed'],
  ] as const)('job with status "%s" renders badge with class "%s"', (status, expectedClass) => {
    const wrapper = mount(JobHistoryTable, {
      props: { jobs: [makeJob(status)] },
    })
    expect(wrapper.find(`.${expectedClass}`).exists()).toBe(true)
  })
})
