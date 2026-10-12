import type { NodeType } from '@/api/types'

export const NODE_TYPE_CSS_VARS: Record<string, string> = {
  File: '--color-node-file',
  Package: '--color-node-package',
  Class: '--color-node-class',
  Interface: '--color-node-interface',
  Enum: '--color-node-enum',
  Function: '--color-node-function',
  Method: '--color-node-method',
  Constructor: '--color-node-constructor',
  Variable: '--color-node-variable',
  Import: '--color-node-import',
  ExternalModule: '--color-node-external-module',
} satisfies Partial<Record<NodeType, string>>

export const ALL_NODE_TYPES = Object.keys(NODE_TYPE_CSS_VARS) as NodeType[]

export const NODE_TYPE_LABELS: Record<string, string> = {
  File: 'File',
  Package: 'Package',
  Class: 'Class',
  Interface: 'Interface',
  Enum: 'Enum',
  Function: 'Function',
  Method: 'Method',
  Constructor: 'Constructor',
  Variable: 'Variable',
  Import: 'Import',
  ExternalModule: 'External Module',
}

export function getNodeColor(type: string): string {
  if (typeof document === 'undefined') return '#808080'
  const varName = NODE_TYPE_CSS_VARS[type] ?? '--color-node-default'
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim() || '#808080'
}
