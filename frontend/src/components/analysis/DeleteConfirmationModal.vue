<script setup lang="ts">
import { AlertTriangleIcon } from 'lucide-vue-next'

defineProps<{
  open: boolean
  totalNodes: number
  totalRelationships: number
  loading: boolean
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="modal-overlay"
        @click.self="emit('cancel')"
      >
        <div
          class="modal"
          role="dialog"
          aria-modal="true"
        >
          <header class="modal-header">
            <AlertTriangleIcon
              :size="22"
              class="warning-icon"
            />
            <span class="modal-title">Delete Graph Data?</span>
          </header>

          <p class="modal-desc">
            This will permanently delete all graph data for this project before
            running the new analysis.
          </p>

          <div
            v-if="!loading"
            class="counts-box"
          >
            <div class="count-row">
              <span>Nodes to be deleted:</span>
              <span class="count-value">{{ totalNodes }}</span>
            </div>
            <div class="count-row">
              <span>Relationships to be deleted:</span>
              <span class="count-value">{{ totalRelationships }}</span>
            </div>
          </div>
          <div
            v-else
            class="counts-box loading"
          >
            Loading counts...
          </div>

          <p class="irreversible-warning">
            This action is irreversible.
          </p>

          <footer class="modal-actions">
            <button
              class="btn btn-cancel"
              @click="emit('cancel')"
            >
              Cancel
            </button>
            <button
              class="btn btn-danger"
              :disabled="loading"
              @click="emit('confirm')"
            >
              Delete &amp; Analyse
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  max-width: 420px;
  width: 90vw;
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.warning-icon {
  color: var(--color-accent);
}

.modal-title {
  font-weight: 700;
  font-size: 16px;
  color: var(--color-accent);
}

.modal-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin: 0 0 14px;
}

.counts-box {
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  padding: 12px;
  margin-bottom: 14px;
}

.counts-box.loading {
  color: var(--color-text-secondary);
  font-size: 13px;
  text-align: center;
}

.count-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-danger-fg-muted);
}

.count-row + .count-row {
  margin-top: 4px;
}

.count-value {
  font-weight: 600;
  color: var(--color-error);
}

.irreversible-warning {
  font-size: 12px;
  color: var(--color-error);
  margin: 0 0 18px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn {
  padding: 8px 20px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.btn-cancel {
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

.btn-cancel:hover {
  background: var(--color-border);
}

.btn-danger {
  background: #993333;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #b33;
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
