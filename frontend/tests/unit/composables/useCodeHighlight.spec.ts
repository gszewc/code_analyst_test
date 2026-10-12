import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useCodeHighlight } from '../../../src/composables/useCodeHighlight'

// Mock shiki to avoid bundling the full highlighter in tests
vi.mock('shiki', () => ({
  createHighlighter: vi.fn().mockResolvedValue({
    codeToHtml: vi.fn((code: string, opts: { transformers?: unknown[] }) => {
      const lines = code.split('\n')
      const lineHtml = lines
        .map((l, i) => `<span data-line="${i + 1}">${l}</span>`)
        .join('\n')
      return `<pre><code>${lineHtml}</code></pre>`
    }),
    loadLanguage: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@shikijs/transformers', () => ({
  transformerMetaHighlight: vi.fn(),
  transformerNotationWordHighlight: vi.fn(),
}))

describe('useCodeHighlight', () => {
  it('returns highlighted html', async () => {
    const { highlight } = useCodeHighlight()
    const html = await highlight('print("hello")', 'python')
    expect(html).toContain('data-line')
    expect(html).toContain('print')
  })

  it('extracts line range when startLine and endLine provided', async () => {
    const { highlight } = useCodeHighlight()
    const code = 'line1\nline2\nline3\nline4\nline5'
    const html = await highlight(code, 'python', 2, 3)
    // Only lines 2 and 3 should be in the output
    expect(html).toContain('line2')
    expect(html).toContain('line3')
    expect(html).not.toContain('line1')
    expect(html).not.toContain('line4')
  })

  it('applies data-line attributes', async () => {
    const { highlight } = useCodeHighlight()
    const html = await highlight('a = 1\nb = 2', 'python')
    expect(html).toContain('data-line="1"')
    expect(html).toContain('data-line="2"')
  })
})
