import { describe, it, expect, beforeEach } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import { useAppStore } from '@/stores/useAppStore'

const ShellHost = defineComponent({
  components: { AppLayout },
  template: '<AppLayout><div>slot</div></AppLayout>',
})

type MountedShell = {
  wrapper: VueWrapper
  appStore: ReturnType<typeof useAppStore>
  router: ReturnType<typeof createRouter>
}

async function mountShell(startPath = '/'): Promise<MountedShell> {
  const pinia = createPinia()
  setActivePinia(pinia)

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: { template: '<div>dashboard</div>' } },
      { path: '/projects/:id/graph', name: 'project-graph', component: { template: '<div>graph</div>' } },
      { path: '/settings', name: 'settings', component: { template: '<div>settings</div>' } },
    ],
  })

  await router.push(startPath)
  await router.isReady()

  const wrapper = mount(ShellHost, {
    global: {
      plugins: [pinia, router],
    },
  })

  return { wrapper, appStore: useAppStore(), router }
}

describe('AppLayout sidebar behavior', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts in extended state on fresh mount', async () => {
    const { wrapper } = await mountShell('/')

    const sidebar = wrapper.get('[data-testid="sidebar"]')
    expect(sidebar.classes()).toContain('is-extended')
    expect(wrapper.find('[data-testid="nav-label-project"]').exists()).toBe(true)
  })

  it('toggles between extended and collapsed from header control', async () => {
    const { wrapper } = await mountShell('/')

    const toggle = wrapper.get('[data-testid="sidebar-toggle"]')

    await toggle.trigger('click')
    expect(wrapper.get('[data-testid="sidebar"]').classes()).toContain('is-collapsed')

    await toggle.trigger('click')
    expect(wrapper.get('[data-testid="sidebar"]').classes()).toContain('is-extended')
  })

  it('hides inline labels and keeps icon navigation when collapsed', async () => {
    const { wrapper } = await mountShell('/')

    await wrapper.get('[data-testid="sidebar-toggle"]').trigger('click')

    expect(wrapper.find('[data-testid="nav-label-project"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="nav-label-settings"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="nav-item-project"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="nav-item-settings"]').exists()).toBe(true)
  })

  it('provides tooltip labels and a11y metadata in collapsed state', async () => {
    const { wrapper } = await mountShell('/')

    await wrapper.get('[data-testid="sidebar-toggle"]').trigger('click')

    const projectNav = wrapper.get('[data-testid="nav-item-project"]')
    expect(projectNav.attributes('aria-label')).toBe('Project')
    expect(projectNav.attributes('title')).toBe('Project')

    await projectNav.trigger('focus')
    await nextTick()

    expect(wrapper.find('[data-testid="nav-tooltip-project"]').exists()).toBe(true)
  })

  it('consumes project-open collapse intent once after project route transition', async () => {
    const { wrapper, appStore, router } = await mountShell('/')

    appStore.requestSidebarCollapseOnProjectOpen()
    expect(appStore.shouldCollapseSidebarOnProjectOpen).toBe(true)

    await router.push('/projects/p-123/graph')
    await nextTick()

    expect(wrapper.get('[data-testid="sidebar"]').classes()).toContain('is-collapsed')
    expect(appStore.shouldCollapseSidebarOnProjectOpen).toBe(false)
  })

  it('does not auto-collapse on unrelated route changes without project-open intent', async () => {
    const { wrapper, router } = await mountShell('/')

    await router.push('/projects/p-123/graph')
    await nextTick()

    expect(wrapper.get('[data-testid="sidebar"]').classes()).toContain('is-extended')
  })
})
