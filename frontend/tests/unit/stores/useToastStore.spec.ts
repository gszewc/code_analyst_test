import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useToastStore } from '../../../src/stores/useToastStore'

describe('useToastStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('starts with no toasts', () => {
    const store = useToastStore()
    expect(store.toasts).toHaveLength(0)
  })

  it('addToast appends a toast with the given message and variant', () => {
    const store = useToastStore()
    store.addToast('Node not found', 'info')
    expect(store.toasts).toHaveLength(1)
    expect(store.toasts[0].message).toBe('Node not found')
    expect(store.toasts[0].variant).toBe('info')
  })

  it('removeToast removes toast by id', () => {
    const store = useToastStore()
    store.addToast('hello', 'info')
    const id = store.toasts[0].id
    store.removeToast(id)
    expect(store.toasts).toHaveLength(0)
  })

  it('auto-dismisses toast after 3500ms', () => {
    const store = useToastStore()
    store.addToast('auto dismiss', 'info')
    expect(store.toasts).toHaveLength(1)
    vi.advanceTimersByTime(3500)
    expect(store.toasts).toHaveLength(0)
  })

  it('does not dismiss toast before 3500ms', () => {
    const store = useToastStore()
    store.addToast('still here', 'info')
    vi.advanceTimersByTime(3499)
    expect(store.toasts).toHaveLength(1)
  })

  it('addToast defaults variant to info', () => {
    const store = useToastStore()
    store.addToast('default variant')
    expect(store.toasts[0].variant).toBe('info')
  })
})
