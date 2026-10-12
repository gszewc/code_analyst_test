import { api } from '@/api/client'
import type { GraphNode, NodeType } from '@/api/types'

const DEFAULT_PREFERRED_TYPES: NodeType[] = ['Class', 'Function', 'Method']

export function useNodeLookup() {
  async function findNode(
    projectId: string,
    name: string,
    preferredTypes: NodeType[] = DEFAULT_PREFERRED_TYPES
  ): Promise<GraphNode | null> {
    const response = await api.graph.search(projectId, name, { limit: 20 })
    if (!response.nodes.length) return null

    const exact = response.nodes.filter((n) => n.name === name)
    const candidates = exact.length > 0 ? exact : response.nodes

    return [...candidates].sort((a, b) => {
      const ai = preferredTypes.indexOf(a.type)
      const bi = preferredTypes.indexOf(b.type)
      const diff = (ai === -1 ? Infinity : ai) - (bi === -1 ? Infinity : bi)
      return isNaN(diff) ? 0 : diff
    })[0]
  }

  async function findFileNode(
    projectId: string,
    filepath: string
  ): Promise<GraphNode | null> {
    const filename = filepath.split('/').pop() ?? filepath
    const response = await api.graph.search(projectId, filename, { nodeType: 'File', limit: 50 })
    if (!response.nodes.length) return null
    return response.nodes.find((n) => {
      const sf = n.source_file
      if (!sf) return false
      return sf === filepath || sf.endsWith('/' + filepath)
    }) ?? null
  }

  return { findNode, findFileNode }
}
