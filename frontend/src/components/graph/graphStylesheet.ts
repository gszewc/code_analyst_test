function cssVar(name: string): string {
  if (typeof document === 'undefined') return ''
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export function buildGraphStylesheet() {
  return [
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)',
        label: 'data(label)',
        color: cssVar('--color-graph-node-label'),
        'font-size': '12px',
        'font-family': '"JetBrains Mono", monospace',
        'text-valign': 'bottom',
        'text-margin-y': '4px',
        'text-halign': 'center',
        width: 20,
        height: 20,
        'border-width': 0,
      },
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 2,
        'border-color': cssVar('--color-graph-selected'),
        width: 24,
        height: 24,
      },
    },
    {
      selector: 'node.dimmed',
      style: {
        opacity: 0.2,
      },
    },
    {
      selector: 'edge',
      style: {
        width: 1,
        'line-color': cssVar('--color-graph-edge'),
        'target-arrow-color': cssVar('--color-graph-edge'),
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'font-size': '9px',
        color: cssVar('--color-graph-edge-text'),
        'text-background-color': cssVar('--color-graph-edge-bg'),
        'text-background-opacity': 0.9,
        'text-background-padding': '2px',
      },
    },
    {
      selector: 'edge:selected, edge.highlighted',
      style: {
        label: 'data(label)',
        'line-color': cssVar('--color-graph-selected'),
        'target-arrow-color': cssVar('--color-graph-selected'),
        width: 2,
      },
    },
  ]
}
