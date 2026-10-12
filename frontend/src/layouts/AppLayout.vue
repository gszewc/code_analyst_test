<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAppStore } from '@/stores/useAppStore'
import { ActivityIcon, FolderIcon, SettingsIcon, CodeIcon, ChevronLeftIcon, ChevronRightIcon } from 'lucide-vue-next'
import ToastContainer from '@/components/ui/ToastContainer.vue'

const appStore = useAppStore()
const route = useRoute()
const showBanner = computed(() => appStore.isBackendUnreachable)
const projectId = computed(() => route.params.id as string | undefined)
const isSidebarCollapsed = computed(() => appStore.isSidebarCollapsed)
const toggleLabel = computed(() => (isSidebarCollapsed.value ? 'Expand sidebar' : 'Collapse sidebar'))

function toggleSidebar(): void {
  appStore.toggleSidebar()
}

watch(
  () => route.fullPath,
  () => {
    if (!appStore.shouldCollapseSidebarOnProjectOpen) {
      return
    }

    if (route.path.startsWith('/projects/')) {
      appStore.collapseSidebar()
      appStore.clearSidebarCollapseOnProjectOpen()
    }
  }
)
</script>

<template>
  <div class="app-shell">
    <!-- Backend unreachable banner -->
    <div
      v-if="showBanner"
      class="error-banner"
    >
      <span>⚠ Backend unreachable — check that the API server is running</span>
    </div>

    <!-- Sidebar -->
    <aside
      class="sidebar"
      :class="isSidebarCollapsed ? 'is-collapsed' : 'is-extended'"
      data-testid="sidebar"
    >
      <div class="sidebar-header">
        <RouterLink
          to="/"
          class="logo"
          :title="isSidebarCollapsed ? 'CodeMiner' : undefined"
          aria-label="CodeMiner"
          data-testid="nav-item-codeminer"
        >
          <CodeIcon :size="22" />
          <span
            v-if="!isSidebarCollapsed"
            class="logo-text"
            data-testid="nav-label-codeminer"
          >CodeMiner</span>
          <span
            v-else
            class="nav-tooltip"
            data-testid="nav-tooltip-codeminer"
          >CodeMiner</span>
        </RouterLink>

        <button
          type="button"
          class="sidebar-toggle"
          :aria-label="toggleLabel"
          :title="toggleLabel"
          data-testid="sidebar-toggle"
          @click="toggleSidebar"
        >
          <ChevronRightIcon
            v-if="isSidebarCollapsed"
            :size="16"
          />
          <ChevronLeftIcon
            v-else
            :size="16"
          />
        </button>
      </div>

      <nav class="sidebar-nav">
        <RouterLink
          to="/"
          class="nav-item"
          :class="{ active: route.name === 'dashboard' }"
          :title="isSidebarCollapsed ? 'Project' : undefined"
          aria-label="Project"
          data-testid="nav-item-project"
        >
          <FolderIcon :size="18" />
          <span
            v-if="!isSidebarCollapsed"
            class="nav-label"
            data-testid="nav-label-project"
          >Project</span>
          <span
            v-else
            class="nav-tooltip"
            data-testid="nav-tooltip-project"
          >Project</span>
        </RouterLink>

        <template v-if="projectId">
          <RouterLink
            :to="`/projects/${projectId}/graph`"
            class="nav-item"
            :class="{ active: route.name === 'project-graph' }"
            :title="isSidebarCollapsed ? 'Graph' : undefined"
            aria-label="Graph"
            data-testid="nav-item-graph"
          >
            <ActivityIcon :size="18" />
            <span
              v-if="!isSidebarCollapsed"
              class="nav-label"
              data-testid="nav-label-graph"
            >Graph</span>
            <span
              v-else
              class="nav-tooltip"
              data-testid="nav-tooltip-graph"
            >Graph</span>
          </RouterLink>
        </template>

        <RouterLink
          to="/settings"
          class="nav-item"
          :class="{ active: route.name === 'settings' }"
          :title="isSidebarCollapsed ? 'Settings' : undefined"
          aria-label="Settings"
          data-testid="nav-item-settings"
        >
          <SettingsIcon :size="18" />
          <span
            v-if="!isSidebarCollapsed"
            class="nav-label"
            data-testid="nav-label-settings"
          >Settings</span>
          <span
            v-else
            class="nav-tooltip"
            data-testid="nav-tooltip-settings"
          >Settings</span>
        </RouterLink>
      </nav>
    </aside>

    <!-- Main content -->
    <main
      class="main-content"
      :class="{ 'is-sidebar-collapsed': isSidebarCollapsed }"
      data-testid="main-content"
    >
      <slot />
    </main>

    <!-- Toast notifications -->
    <ToastContainer />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background-color: var(--color-bg-base);
}

.error-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background-color: var(--color-error);
  color: white;
  padding: 8px 16px;
  font-size: 13px;
  text-align: center;
}

.sidebar {
  width: var(--sidebar-width-expanded);
  flex-shrink: 0;
  background-color: var(--color-bg-elevated);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  transition: width var(--sidebar-transition);
}

.sidebar.is-collapsed {
  width: var(--sidebar-width-collapsed);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 20px 16px 16px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.sidebar.is-collapsed .sidebar-header {
  padding: 16px 10px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  color: var(--color-accent);
  text-decoration: none;
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.logo:hover {
  color: var(--color-accent-hover);
}

.sidebar-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  min-height: 32px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-panel);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.sidebar-toggle:hover {
  color: var(--color-text-primary);
  border-color: var(--color-accent-border);
}

.sidebar-nav {
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: all var(--transition-fast);
}

.nav-item:hover {
  background-color: var(--color-bg-overlay);
  color: var(--color-text-primary);
}

.nav-item.active {
  background-color: var(--color-accent-muted);
  color: var(--color-accent);
}

.sidebar.is-collapsed .nav-item {
  justify-content: center;
  padding: 10px 8px;
}

.nav-tooltip {
  position: absolute;
  left: calc(100% + 10px);
  top: 50%;
  transform: translateY(-50%) translateX(-4px);
  opacity: 0;
  pointer-events: none;
  white-space: nowrap;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  background-color: var(--tooltip-bg);
  color: var(--tooltip-text);
  border: 1px solid var(--color-border);
  box-shadow: var(--tooltip-shadow);
  font-size: 12px;
  z-index: 12;
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.sidebar.is-collapsed .nav-item:hover .nav-tooltip,
.sidebar.is-collapsed .nav-item:focus-visible .nav-tooltip,
.sidebar.is-collapsed .logo:hover .nav-tooltip,
.sidebar.is-collapsed .logo:focus-visible .nav-tooltip {
  opacity: 1;
  transform: translateY(-50%) translateX(0);
}

.main-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 100vh;
  height: 100vh;
  overflow-y: auto;
  min-width: 0;
  transition: width var(--sidebar-transition);
}
</style>
