import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import GraphFilterDock from '@/components/graph/GraphFilterDock.vue'

describe('GraphFilterDock', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.sessionStorage.clear()
  })

  it('is closed by default', () => {
    const wrapper = mount(GraphFilterDock)
    expect(wrapper.find('[data-testid="filter-dock-panel"]').exists()).toBe(false)
  })

  it('opens from trigger and closes on Escape', async () => {
    const wrapper = mount(GraphFilterDock)

    await wrapper.get('[data-testid="filter-dock-toggle"]').trigger('click')
    expect(wrapper.find('[data-testid="filter-dock-panel"]').exists()).toBe(true)

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="filter-dock-panel"]').exists()).toBe(false)
  })

  it('closes when clicking outside the dock', async () => {
    const wrapper = mount(GraphFilterDock, {
      attachTo: document.body,
    })

    await wrapper.get('[data-testid="filter-dock-toggle"]').trigger('click')
    expect(wrapper.find('[data-testid="filter-dock-panel"]').exists()).toBe(true)

    document.body.click()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="filter-dock-panel"]').exists()).toBe(false)
  })
})
