import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import type { FileEntry, FileListResponse } from '../../../src/api/types'

// ── Alias-path fixture helpers ────────────────────────────────────────────
//
// The backend exposes symlinked dirs/files as regular FileEntry objects with
// no special metadata (alias identity is preserved in the `path` field only).
// These factories build representative data shapes for linked-directory
// scenarios so that T014 / T015 tests can stay DRY.

/** A directory entry whose path is an alias into a symlinked subtree. */
export function makeLinkedDirEntry(
  name: string,
  path?: string,
): FileEntry {
  return {
    name,
    path: path ?? name,
    size: 0,
    is_directory: true,
  }
}

/** A file entry reachable through an alias path (one or more symlink hops). */
export function makeAliasFileEntry(
  name: string,
  path?: string,
  size = 512,
): FileEntry {
  return {
    name,
    path: path ?? name,
    size,
    is_directory: false,
  }
}

/**
 * A mock FileListResponse for the children of a linked directory.
 * Pass an explicit `files` array or omit for a single default Python file.
 */
export function makeLinkedDirListing(
  dirPath: string,
  files?: FileEntry[],
): FileListResponse {
  const children: FileEntry[] =
    files ??
    [makeAliasFileEntry('utils.py', `${dirPath}/utils.py`)]
  return { files: children, total: children.length }
}

// ── Existing tests ────────────────────────────────────────────────────────

// Minimal stub for FileTreeNode since it uses recursive components
// We test the expand/collapse logic here
describe('FileTree expand/collapse', () => {
  it('emits select when a file node is clicked', async () => {
    const { VueQueryPlugin, QueryClient } = await import('@tanstack/vue-query')
    const FileTreeNode = (await import('../../../src/components/files/FileTreeNode.vue')).default

    const qc = new QueryClient()
    const wrapper = mount(FileTreeNode, {
      props: {
        entry: {
          name: 'main.py',
          path: 'src/main.py',
          size: 1024,
          is_directory: false,
        },
        projectId: 'proj-1',
        selectedPath: '',
      },
      global: {
        plugins: [[VueQueryPlugin, { queryClient: qc }]],
        stubs: {
          FileTreeNode: true,
        },
      },
    })

    await wrapper.find('.node-row').trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')?.[0]).toEqual(['src/main.py'])
  })

  it('does not emit select when a directory node is clicked', async () => {
    const { VueQueryPlugin, QueryClient } = await import('@tanstack/vue-query')
    const FileTreeNode = (await import('../../../src/components/files/FileTreeNode.vue')).default

    const qc = new QueryClient()
    const wrapper = mount(FileTreeNode, {
      props: {
        entry: {
          name: 'src',
          path: 'src',
          size: 0,
          is_directory: true,
        },
        projectId: 'proj-1',
        selectedPath: '',
      },
      global: {
        plugins: [[VueQueryPlugin, { queryClient: qc }]],
        stubs: { FileTreeNode: true },
      },
    })

    await wrapper.find('.node-row').trigger('click')
    expect(wrapper.emitted('select')).toBeFalsy()
  })
})
