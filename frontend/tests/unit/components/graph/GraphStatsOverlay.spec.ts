import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import GraphStatsOverlay from '@/components/graph/GraphStatsOverlay.vue'

describe('GraphStatsOverlay', () => {
  it('renders node and edge chips when stats are available', () => {
    const wrapper = mount(GraphStatsOverlay, {
      props: {
        stats: {
          project_id: 'p-1',
          node_count: 1203,
          relationship_count: 450,
        },
      },
    })

    expect(wrapper.find('[data-testid="graph-stats-overlay"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="graph-stats-node-count"]').text()).toContain('1,203')
    expect(wrapper.get('[data-testid="graph-stats-edge-count"]').text()).toContain('450')
  })

  it('is hidden when stats are not available', () => {
    const wrapper = mount(GraphStatsOverlay, {
      props: {
        stats: null,
      },
    })

    expect(wrapper.find('[data-testid="graph-stats-overlay"]').exists()).toBe(false)
  })
})
