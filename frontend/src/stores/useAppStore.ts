import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import type { SidebarState } from '@/types/sidebar'

export const useAppStore = defineStore('app', () => {
  const backendReachable = ref<boolean>(true)
  const activeProjectId = ref<string | null>(null)
  const isLLMConfigured = ref<boolean>(false)
  const sidebarState = ref<SidebarState>('extended')
  const shouldCollapseSidebarOnProjectOpen = ref<boolean>(false)

  const isBackendUnreachable = computed(() => !backendReachable.value)
  const isSidebarCollapsed = computed(() => sidebarState.value === 'collapsed')

  async function checkHealth(): Promise<void> {
    try {
      const health = await api.health.check()
      backendReachable.value = health.status !== 'unhealthy'
    } catch {
      backendReachable.value = false
    }
  }

  async function loadLLMConfig(): Promise<void> {
    try {
      const config = await api.llm.getConfig()
      isLLMConfigured.value = config.is_configured
    } catch {
      isLLMConfigured.value = false
    }
  }

  function setActiveProject(id: string | null): void {
    activeProjectId.value = id
  }

  function setBackendReachable(reachable: boolean): void {
    backendReachable.value = reachable
  }

  function setLLMConfigured(configured: boolean): void {
    isLLMConfigured.value = configured
  }

  function toggleSidebar(): void {
    sidebarState.value = sidebarState.value === 'extended' ? 'collapsed' : 'extended'
  }

  function collapseSidebar(): void {
    sidebarState.value = 'collapsed'
  }

  function expandSidebar(): void {
    sidebarState.value = 'extended'
  }

  function requestSidebarCollapseOnProjectOpen(): void {
    shouldCollapseSidebarOnProjectOpen.value = true
  }

  function clearSidebarCollapseOnProjectOpen(): void {
    shouldCollapseSidebarOnProjectOpen.value = false
  }

  return {
    backendReachable,
    activeProjectId,
    isLLMConfigured,
    sidebarState,
    shouldCollapseSidebarOnProjectOpen,
    isBackendUnreachable,
    isSidebarCollapsed,
    checkHealth,
    loadLLMConfig,
    setActiveProject,
    setBackendReachable,
    setLLMConfigured,
    toggleSidebar,
    collapseSidebar,
    expandSidebar,
    requestSidebarCollapseOnProjectOpen,
    clearSidebarCollapseOnProjectOpen,
  }
})
