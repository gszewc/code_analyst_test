<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/api/client'
import { useAppStore } from '@/stores/useAppStore'
import AppLayout from '@/layouts/AppLayout.vue'
import ProjectControlBar from '@/components/project/ProjectControlBar.vue'

const route = useRoute()
const appStore = useAppStore()
const projectId = computed(() => route.params.id as string)

const { data: project, isLoading, isError } = useQuery({
  queryKey: computed(() => ['project', projectId.value]),
  queryFn: () => api.projects.get(projectId.value),
  enabled: computed(() => !!projectId.value),
})

watch(projectId, (id) => appStore.setActiveProject(id ?? null), { immediate: true })

const activeTabRouteName = computed(() => String(route.name ?? 'project-graph'))
</script>

<template>
  <AppLayout>
    <div class="project-outer">
      <ProjectControlBar
        :project-id="projectId"
        :project-name="project?.name"
        :is-loading="isLoading"
        :is-error="isError"
        :active-route-name="activeTabRouteName"
      />

      <!-- Routed tab content -->
      <div class="tab-content">
        <router-view />
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.project-outer {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.tab-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: auto;
  min-height: 0;
}
</style>
