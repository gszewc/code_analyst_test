import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast {
  id: number
  message: string
  variant: 'info' | 'error'
}

export const useToastStore = defineStore('toast', () => {
  let _nextId = 0
  const toasts = ref<Toast[]>([])

  function addToast(message: string, variant: Toast['variant'] = 'info'): void {
    const id = _nextId++
    toasts.value.push({ id, message, variant })
    setTimeout(() => removeToast(id), 3500)
  }

  function removeToast(id: number): void {
    const idx = toasts.value.findIndex((t) => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  return { toasts, addToast, removeToast }
})
