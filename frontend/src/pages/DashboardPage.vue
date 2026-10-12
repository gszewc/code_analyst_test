<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { api, ApiRequestError } from '@/api/client'
import type { ProjectResponse } from '@/api/types'
import { projectCreateSchema, projectUpdateSchema } from '@/schemas/project'
import AppLayout from '@/layouts/AppLayout.vue'
import ProjectCard from '@/components/ui/ProjectCard.vue'
import { useAppStore } from '@/stores/useAppStore'
import { PlusIcon, FolderOpenIcon } from 'lucide-vue-next'

const queryClient = useQueryClient()
const appStore = useAppStore()

// ── Query ──────────────────────────────────────────────────────────────────
const { data, isLoading, isError } = useQuery({
  queryKey: ['projects'],
  queryFn: () => api.projects.list(),
})

const projects = computed(() => data.value?.projects ?? [])

// ── Create dialog ──────────────────────────────────────────────────────────
const showCreateDialog = ref(false)
const createError = ref('')

const { handleSubmit: handleCreate, errors: createErrors, resetForm: resetCreate, defineField: defineCreateField } = useForm({
  validationSchema: toTypedSchema(projectCreateSchema),
})

const [createName, createNameAttrs] = defineCreateField('name')
const [createDesc, createDescAttrs] = defineCreateField('description')

const createMutation = useMutation({
  mutationFn: (data: { name: string; description?: string }) => api.projects.create(data),
  onSuccess: (newProject) => {
    queryClient.setQueryData(['projects'], (old: typeof data.value) => ({
      projects: [newProject, ...(old?.projects ?? [])],
      total: (old?.total ?? 0) + 1,
    }))
    showCreateDialog.value = false
    resetCreate()
    createError.value = ''
  },
  onError: (err) => {
    createError.value = err instanceof ApiRequestError ? err.detail : 'Failed to create project'
  },
})

const onCreateSubmit = handleCreate((values) => {
  createMutation.mutate({ name: values.name, description: values.description || undefined })
})

// ── Rename dialog ──────────────────────────────────────────────────────────
const renamingProject = ref<ProjectResponse | null>(null)
const renameError = ref('')

const { handleSubmit: handleRename, errors: renameErrors, resetForm: resetRename, defineField: defineRenameField, setValues: setRenameValues } = useForm({
  validationSchema: toTypedSchema(projectUpdateSchema),
})

const [renameName, renameNameAttrs] = defineRenameField('name')
const [renameDesc, renameDescAttrs] = defineRenameField('description')

function openRename(project: ProjectResponse) {
  renamingProject.value = project
  setRenameValues({ name: project.name, description: project.description ?? '' })
  renameError.value = ''
}

const renameMutation = useMutation({
  mutationFn: ({ id, name, description }: { id: string; name?: string; description?: string }) =>
    api.projects.update(id, { name, description }),
  onSuccess: (updated) => {
    queryClient.setQueryData(['projects'], (old: typeof data.value) => ({
      ...old,
      projects: old?.projects.map((p) => (p.id === updated.id ? updated : p)) ?? [],
    }))
    renamingProject.value = null
  },
  onError: (err) => {
    renameError.value = err instanceof ApiRequestError ? err.detail : 'Failed to update project'
  },
})

const onRenameSubmit = handleRename((values) => {
  if (!renamingProject.value) return
  renameMutation.mutate({ id: renamingProject.value.id, name: values.name, description: values.description || undefined })
})

// ── Delete dialog ──────────────────────────────────────────────────────────
const deletingProject = ref<ProjectResponse | null>(null)
const deleteError = ref('')

const deleteMutation = useMutation({
  mutationFn: (id: string) => api.projects.delete(id),
  onSuccess: (_, id) => {
    queryClient.setQueryData(['projects'], (old: typeof data.value) => ({
      ...old,
      projects: old?.projects.filter((p) => p.id !== id) ?? [],
      total: Math.max(0, (old?.total ?? 1) - 1),
    }))
    deletingProject.value = null
  },
  onError: (err) => {
    deleteError.value = err instanceof ApiRequestError ? err.detail : 'Failed to delete project'
  },
})

function confirmDelete() {
  if (!deletingProject.value) return
  deleteError.value = ''
  deleteMutation.mutate(deletingProject.value.id)
}

function openDelete(project: ProjectResponse) {
  deletingProject.value = project
  deleteError.value = ''
}

function handleOpenProject(projectId: string) {
  appStore.setActiveProject(projectId)
  appStore.requestSidebarCollapseOnProjectOpen()
}
</script>

<template>
  <AppLayout>
    <div class="page">
      <header class="page-header">
        <div>
          <h1 class="page-title">
            Projects
          </h1>
          <p class="page-subtitle">
            Manage your legacy codebase analysis projects
          </p>
        </div>
        <button
          class="btn-primary"
          @click="showCreateDialog = true"
        >
          <PlusIcon :size="16" />
          New Project
        </button>
      </header>

      <!-- Loading -->
      <div
        v-if="isLoading"
        class="state-message"
      >
        Loading projects…
      </div>

      <!-- Error -->
      <div
        v-else-if="isError"
        class="state-message error"
      >
        Failed to load projects. Check backend connection.
      </div>

      <!-- Empty state -->
      <div
        v-else-if="projects.length === 0"
        class="empty-state"
      >
        <FolderOpenIcon :size="48" />
        <p>No projects yet</p>
        <button
          class="btn-primary"
          @click="showCreateDialog = true"
        >
          Create your first project
        </button>
      </div>

      <!-- Project grid -->
      <div
        v-else
        class="project-grid"
      >
        <ProjectCard
          v-for="(project, idx) in projects"
          :key="project.id"
          :project="project"
          :style="{ animationDelay: `${idx * 40}ms` }"
          class="card-enter"
          @open="handleOpenProject"
          @rename="openRename"
          @delete="openDelete"
        />
      </div>
    </div>

    <!-- Create dialog -->
    <div
      v-if="showCreateDialog"
      class="dialog-backdrop"
      @click.self="showCreateDialog = false"
    >
      <div class="dialog">
        <h2 class="dialog-title">
          New Project
        </h2>
        <form @submit.prevent="onCreateSubmit">
          <div class="field">
            <label
              class="field-label"
              for="create-name"
            >Name *</label>
            <input
              id="create-name"
              v-model="createName"
              v-bind="createNameAttrs"
              class="field-input"
              placeholder="my-legacy-app"
              autocomplete="off"
            >
            <span
              v-if="createErrors.name"
              class="field-error"
            >{{ createErrors.name }}</span>
          </div>
          <div class="field">
            <label
              class="field-label"
              for="create-desc"
            >Description</label>
            <textarea
              id="create-desc"
              v-model="createDesc"
              v-bind="createDescAttrs"
              class="field-input"
              rows="3"
              placeholder="Optional description…"
            />
            <span
              v-if="createErrors.description"
              class="field-error"
            >{{ createErrors.description }}</span>
          </div>
          <div
            v-if="createError"
            class="form-error"
          >
            {{ createError }}
          </div>
          <div class="dialog-footer">
            <button
              type="button"
              class="btn-ghost"
              @click="showCreateDialog = false; resetCreate()"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="btn-primary"
              :disabled="createMutation.isPending.value"
            >
              {{ createMutation.isPending.value ? 'Creating…' : 'Create' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Rename dialog -->
    <div
      v-if="renamingProject"
      class="dialog-backdrop"
      @click.self="renamingProject = null"
    >
      <div class="dialog">
        <h2 class="dialog-title">
          Edit Project
        </h2>
        <form @submit.prevent="onRenameSubmit">
          <div class="field">
            <label
              class="field-label"
              for="rename-name"
            >Name *</label>
            <input
              id="rename-name"
              v-model="renameName"
              v-bind="renameNameAttrs"
              class="field-input"
            >
            <span
              v-if="renameErrors.name"
              class="field-error"
            >{{ renameErrors.name }}</span>
          </div>
          <div class="field">
            <label
              class="field-label"
              for="rename-desc"
            >Description</label>
            <textarea
              id="rename-desc"
              v-model="renameDesc"
              v-bind="renameDescAttrs"
              class="field-input"
              rows="3"
            />
            <span
              v-if="renameErrors.description"
              class="field-error"
            >{{ renameErrors.description }}</span>
          </div>
          <div
            v-if="renameError"
            class="form-error"
          >
            {{ renameError }}
          </div>
          <div class="dialog-footer">
            <button
              type="button"
              class="btn-ghost"
              @click="renamingProject = null"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="btn-primary"
              :disabled="renameMutation.isPending.value"
            >
              {{ renameMutation.isPending.value ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete confirm dialog -->
    <div
      v-if="deletingProject"
      class="dialog-backdrop"
      @click.self="deletingProject = null"
    >
      <div class="dialog">
        <h2 class="dialog-title">
          Delete Project
        </h2>
        <p class="dialog-body">
          Are you sure you want to delete <strong>{{ deletingProject.name }}</strong>? This cannot be undone.
        </p>
        <div
          v-if="deleteError"
          class="form-error"
        >
          {{ deleteError }}
        </div>
        <div class="dialog-footer">
          <button
            type="button"
            class="btn-ghost"
            @click="deletingProject = null"
          >
            Cancel
          </button>
          <button
            class="btn-danger"
            :disabled="deleteMutation.isPending.value"
            @click="confirmDelete"
          >
            {{ deleteMutation.isPending.value ? 'Deleting…' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
.page {
  padding: 32px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 32px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.card-enter {
  animation: cardEnter 300ms ease both;
}

@keyframes cardEnter {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.state-message {
  padding: 48px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 15px;
}

.state-message.error {
  color: var(--color-error);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 80px 32px;
  color: var(--color-text-muted);
}

.empty-state p {
  font-size: 16px;
  margin: 0;
}

/* Dialog */
.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.dialog {
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: 24px;
  width: 100%;
  max-width: 440px;
}

.dialog-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 20px;
}

.dialog-body {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0 0 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

/* Form fields */
.field {
  margin-bottom: 16px;
}

.field-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.field-input {
  width: 100%;
  background: var(--color-bg-overlay);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: 14px;
  padding: 8px 12px;
  outline: none;
  transition: border-color var(--transition-fast);
  font-family: inherit;
  box-sizing: border-box;
  resize: vertical;
}

.field-input:focus {
  border-color: var(--color-accent);
}

.field-error {
  display: block;
  font-size: 12px;
  color: var(--color-error);
  margin-top: 4px;
}

.form-error {
  font-size: 13px;
  color: var(--color-error);
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid rgba(248, 81, 73, 0.2);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  margin-bottom: 16px;
}

/* Buttons */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--color-accent);
  color: #000;
  border: none;
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-ghost:hover {
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
}

.btn-danger {
  background: var(--color-error);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.btn-danger:hover:not(:disabled) {
  opacity: 0.85;
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
