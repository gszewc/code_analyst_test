import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

async function mountFileTreeNode(entryOverrides = {}) {
  const { VueQueryPlugin, QueryClient } = await import('@tanstack/vue-query')
  const { default: FileTreeNode } = await import('../../../../src/components/files/FileTreeNode.vue')
  const qc = new QueryClient()
  return mount(FileTreeNode, {
    props: {
      entry: {
        name: 'parser.py',
        path: 'src/parser.py',
        size: 1024,
        is_directory: false,
        ...entryOverrides,
      },
      projectId: 'proj-1',
      selectedPath: '',
    },
    global: {
      plugins: [[VueQueryPlugin, { queryClient: qc }]],
      stubs: { FileTreeNode: true },
    },
  })
}

describe('FileTreeNode — findInGraph emit', () => {
  it('emits findInGraph with path and position when Ctrl+Click on a file', async () => {
    const wrapper = await mountFileTreeNode()
    await wrapper.find('.node-row').trigger('click', { ctrlKey: true, clientX: 120, clientY: 240 })
    const emitted = wrapper.emitted('findInGraph')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toBe('src/parser.py')
    expect(emitted![0][1]).toEqual({ x: 120, y: 240 })
  })

  it('emits findInGraph with position when Meta+Click on a file (macOS)', async () => {
    const wrapper = await mountFileTreeNode()
    await wrapper.find('.node-row').trigger('click', { metaKey: true, clientX: 50, clientY: 80 })
    const emitted = wrapper.emitted('findInGraph')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toBe('src/parser.py')
  })

  it('emits select (not findInGraph) on plain click', async () => {
    const wrapper = await mountFileTreeNode()
    await wrapper.find('.node-row').trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('findInGraph')).toBeFalsy()
  })

  it('does not emit findInGraph when Ctrl+Click on a directory', async () => {
    const wrapper = await mountFileTreeNode({ name: 'src', path: 'src', is_directory: true, size: 0 })
    await wrapper.find('.node-row').trigger('click', { ctrlKey: true })
    expect(wrapper.emitted('findInGraph')).toBeFalsy()
  })
})
