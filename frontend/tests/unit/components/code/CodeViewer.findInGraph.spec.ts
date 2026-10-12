import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'

vi.mock('../../../../src/api/client', () => ({
  api: {
    files: {
      getContent: vi.fn().mockResolvedValue({ content: 'class MyClass:\n  pass' }),
    },
  },
}))

vi.mock('../../../../src/composables/useCodeHighlight', () => ({
  useCodeHighlight: () => ({
    highlight: (code: string) => `<table class="hljs-table"><tr><td class="line-code">${code}</td></tr></table>`,
  }),
}))

vi.mock('highlight.js/styles/github-dark.css', () => ({}))

async function mountCodeViewer() {
  const { default: CodeViewer } = await import('../../../../src/components/code/CodeViewer.vue')
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return mount(CodeViewer, {
    props: { projectId: 'p1', filepath: 'main.py' },
    global: { plugins: [[VueQueryPlugin, { queryClient: qc }]] },
  })
}

describe('CodeViewer — findInGraph emit', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('emits findInGraph with selected text and position on Ctrl+Click', async () => {
    vi.spyOn(window, 'getSelection').mockReturnValue({
      toString: () => 'MyClass',
    } as Selection)

    const wrapper = await mountCodeViewer()
    // Wait for query to resolve
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    await wrapper.find('.code-container').trigger('click', { ctrlKey: true, clientX: 100, clientY: 200 })

    const emitted = wrapper.emitted('findInGraph')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toBe('MyClass')
    expect(emitted![0][1]).toEqual({ x: 100, y: 200 })
  })

  it('emits findInGraph on Meta+Click (macOS Cmd+Click)', async () => {
    vi.spyOn(window, 'getSelection').mockReturnValue({
      toString: () => 'MyClass',
    } as Selection)

    const wrapper = await mountCodeViewer()
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    await wrapper.find('.code-container').trigger('click', { metaKey: true, clientX: 50, clientY: 80 })

    const emitted = wrapper.emitted('findInGraph')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toBe('MyClass')
  })

  it('does not emit findInGraph on plain click', async () => {
    const wrapper = await mountCodeViewer()
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    await wrapper.find('.code-container').trigger('click')
    expect(wrapper.emitted('findInGraph')).toBeFalsy()
  })

  it('does not emit findInGraph when selection contains whitespace', async () => {
    vi.spyOn(window, 'getSelection').mockReturnValue({
      toString: () => 'my class',
    } as Selection)

    const wrapper = await mountCodeViewer()
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    await wrapper.find('.code-container').trigger('click', { ctrlKey: true })
    expect(wrapper.emitted('findInGraph')).toBeFalsy()
  })

  it('does not emit findInGraph when selection is empty', async () => {
    vi.spyOn(window, 'getSelection').mockReturnValue({
      toString: () => '',
    } as Selection)

    const wrapper = await mountCodeViewer()
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    await wrapper.find('.code-container').trigger('click', { ctrlKey: true })
    expect(wrapper.emitted('findInGraph')).toBeFalsy()
  })
})
