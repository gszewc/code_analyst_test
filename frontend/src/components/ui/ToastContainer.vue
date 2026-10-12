<!-- frontend/src/components/ui/ToastContainer.vue -->
<script setup lang="ts">
import { useToastStore } from '@/stores/useToastStore'
import { XIcon } from 'lucide-vue-next'

const toastStore = useToastStore()
</script>

<template>
  <Teleport to="body">
    <div
      class="toast-container"
      aria-live="polite"
      aria-atomic="false"
    >
      <TransitionGroup
        name="toast"
        tag="div"
        class="toast-list"
      >
        <div
          v-for="toast in toastStore.toasts"
          :key="toast.id"
          class="toast"
          :class="`toast--${toast.variant}`"
          role="status"
        >
          <span class="toast-message">{{ toast.message }}</span>
          <button
            type="button"
            class="toast-close"
            aria-label="Dismiss"
            @click="toastStore.removeToast(toast.id)"
          >
            <XIcon :size="12" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 9999;
  pointer-events: none;
}

.toast-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--color-text-primary);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  pointer-events: all;
  min-width: 220px;
  max-width: 360px;
}

.toast--error {
  border-color: var(--color-error);
  color: var(--color-error);
}

.toast-message {
  flex: 1;
}

.toast-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  padding: 0;
}

.toast-close:hover {
  color: var(--color-text-primary);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
