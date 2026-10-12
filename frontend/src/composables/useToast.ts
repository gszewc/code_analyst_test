import { useToastStore } from '@/stores/useToastStore'
import type { Toast } from '@/stores/useToastStore'

export function useToast() {
  const toastStore = useToastStore()

  function showToast(message: string, variant: Toast['variant'] = 'info'): void {
    toastStore.addToast(message, variant)
  }

  return { showToast }
}
