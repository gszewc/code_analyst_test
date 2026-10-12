<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronLeftIcon } from 'lucide-vue-next'
import { PROJECT_SECTIONS } from '@/constants/projectSections'

const props = defineProps<{
  projectId: string
  projectName?: string
  isLoading?: boolean
  isError?: boolean
  activeRouteName?: string
}>()

const tabs = computed(() =>
  PROJECT_SECTIONS.map((section) => ({
    ...section,
    path: `/projects/${props.projectId}/${section.slug}`,
  }))
)

const activeTab = computed(() =>
  tabs.value.find((tab: { routeName: string }) => tab.routeName === props.activeRouteName) ?? tabs.value[0]
)
</script>

<template>
  <header
    class="project-control-bar"
    data-testid="project-control-bar"
  >
    <div class="project-context">
      <RouterLink
        to="/"
        class="back-link"
        data-testid="project-control-back-link"
      >
        <ChevronLeftIcon :size="16" />
      </RouterLink>
      <div
        v-if="isLoading"
        class="header-skeleton"
        data-testid="project-control-loading"
      />
      <h1
        v-else-if="projectName"
        class="project-name"
        :title="projectName"
        data-testid="project-control-project-name"
      >
        {{ projectName }}
      </h1>
      <span
        v-else-if="isError"
        class="header-error"
        data-testid="project-control-error"
      >Project not found</span>
      <span
        v-else
        class="header-empty"
        data-testid="project-control-empty"
      >Unnamed project</span>
    </div>

    <nav
      class="segmented-tabs"
      data-testid="project-control-tabs"
    >
      <RouterLink
        v-for="tab in tabs"
        :key="tab.routeName"
        :to="tab.path"
        class="tab"
        :class="{ active: activeTab?.routeName === tab.routeName }"
        :data-testid="`project-control-tab-${tab.slug}`"
      >
        <component
          :is="tab.icon"
          :size="16"
        />
        {{ tab.name }}
      </RouterLink>
    </nav>
  </header>
</template>

<style scoped>
.project-control-bar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border);
  background: color-mix(in oklab, var(--color-bg-base) 90%, black 10%);
}

.project-context {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.back-link {
  display: flex;
  align-items: center;
  color: var(--color-text-secondary);
  text-decoration: none;
  border: 1px solid var(--color-border);
  width: 28px;
  height: 28px;
  border-radius: 8px;
  justify-content: center;
}

.back-link:hover {
  color: var(--color-text-primary);
  border-color: var(--color-accent-border);
}

.project-name {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
  max-width: min(56vw, 480px);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-skeleton {
  width: 220px;
  height: 16px;
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  animation: pulse 1.5s ease infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.header-error {
  color: var(--color-error);
  font-size: 13px;
}

.header-empty {
  color: var(--color-text-muted);
  font-size: 13px;
}

.segmented-tabs {
  flex-shrink: 0;
  display: flex;
  gap: 3px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 3px;
  background: var(--color-bg-elevated);
}

.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  text-decoration: none;
  border-radius: 8px;
  transition: all var(--transition-fast);
}

.tab:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-overlay);
}

.tab.active {
  color: var(--color-bg-base);
  background: var(--color-accent);
}

@media (max-width: 980px) {
  .project-control-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .project-context {
    width: 100%;
  }

  .segmented-tabs {
    width: 100%;
    justify-content: stretch;
  }

  .tab {
    flex: 1;
    justify-content: center;
  }
}
</style>
