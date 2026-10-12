import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { buildGraphStylesheet } from '../../../../src/components/graph/graphStylesheet'

function setVar(name: string, value: string) {
  document.documentElement.style.setProperty(name, value)
}
function removeVar(name: string) {
  document.documentElement.style.removeProperty(name)
}

describe('buildGraphStylesheet', () => {
  beforeEach(() => {
    setVar('--color-graph-node-label', '#e8e8e8')
    setVar('--color-graph-edge', '#3a3a3a')
    setVar('--color-graph-edge-text', '#5a5a5a')
    setVar('--color-graph-edge-bg', '#0d0d0d')
    setVar('--color-graph-selected', '#f0a500')
  })

  afterEach(() => {
    ['--color-graph-node-label','--color-graph-edge','--color-graph-edge-text',
     '--color-graph-edge-bg','--color-graph-selected'].forEach(removeVar)
  })

  it('node selector uses CSS var for label color', () => {
    const styles = buildGraphStylesheet()
    const nodeStyle = styles.find((s) => s.selector === 'node')!
    expect(nodeStyle.style.color).toBe('#e8e8e8')
  })

  it('edge selector uses CSS var for line-color', () => {
    const styles = buildGraphStylesheet()
    const edgeStyle = styles.find((s) => s.selector === 'edge')!
    expect(edgeStyle.style['line-color']).toBe('#3a3a3a')
  })

  it('edge selector uses CSS var for text color', () => {
    const styles = buildGraphStylesheet()
    const edgeStyle = styles.find((s) => s.selector === 'edge')!
    expect(edgeStyle.style.color).toBe('#5a5a5a')
  })

  it('edge selector uses CSS var for text background', () => {
    const styles = buildGraphStylesheet()
    const edgeStyle = styles.find((s) => s.selector === 'edge')!
    expect(edgeStyle.style['text-background-color']).toBe('#0d0d0d')
  })

  it('selected node uses CSS var for border color', () => {
    const styles = buildGraphStylesheet()
    const selectedStyle = styles.find((s) => s.selector === 'node:selected')!
    expect(selectedStyle.style['border-color']).toBe('#f0a500')
  })

  it('highlighted edge uses CSS var for line color', () => {
    const styles = buildGraphStylesheet()
    const hlStyle = styles.find((s) => s.selector === 'edge:selected, edge.highlighted')!
    expect(hlStyle.style['line-color']).toBe('#f0a500')
  })
})
