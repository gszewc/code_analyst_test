import hljs from 'highlight.js/lib/core'

// Register languages
import python from 'highlight.js/lib/languages/python'
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'
import json from 'highlight.js/lib/languages/json'
import yaml from 'highlight.js/lib/languages/yaml'
import bash from 'highlight.js/lib/languages/bash'
import markdown from 'highlight.js/lib/languages/markdown'
import java from 'highlight.js/lib/languages/java'
import go from 'highlight.js/lib/languages/go'
import rust from 'highlight.js/lib/languages/rust'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import ruby from 'highlight.js/lib/languages/ruby'

hljs.registerLanguage('python', python)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('vue', xml)
hljs.registerLanguage('css', css)
hljs.registerLanguage('json', json)
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('java', java)
hljs.registerLanguage('go', go)
hljs.registerLanguage('rust', rust)
hljs.registerLanguage('c', c)
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('ruby', ruby)

const registeredLangs = new Set(hljs.listLanguages())

/**
 * Split highlighted HTML by newlines, closing and re-opening any
 * open <span> tags at line boundaries so each line is self-contained.
 */
function splitLines(html: string): string[] {
  const lines = html.split('\n')
  const openSpans: string[] = []
  const result: string[] = []

  for (const line of lines) {
    // Prepend any spans that were open from the previous line
    let patched = openSpans.join('') + line

    // Track open/close spans to know what carries over
    const openRe = /<span[^>]*>/g
    const closeRe = /<\/span>/g
    let m: RegExpExecArray | null

    // Count opens and closes on the original line (not patched)
    const opens: string[] = []
    while ((m = openRe.exec(line)) !== null) opens.push(m[0])
    const closes = (line.match(closeRe) || []).length

    // Update the running stack: closes pop from the end, opens push
    for (let i = 0; i < closes && openSpans.length > 0; i++) openSpans.pop()
    for (const tag of opens) openSpans.push(tag)

    // Close any still-open spans at end of this line
    patched += '</span>'.repeat(openSpans.length)

    result.push(patched)
  }

  return result
}

export function useCodeHighlight() {
  function highlight(
    code: string,
    lang: string,
    startLine?: number,
    endLine?: number,
  ): string {
    let sourceCode = code
    const lineOffset = startLine ?? 1

    if (startLine !== undefined && endLine !== undefined) {
      const codeLines = code.split('\n')
      sourceCode = codeLines.slice(startLine - 1, endLine).join('\n')
    }

    let highlighted: string
    if (registeredLangs.has(lang)) {
      highlighted = hljs.highlight(sourceCode, { language: lang }).value
    } else {
      highlighted = hljs.highlightAuto(sourceCode).value
    }

    const lines = splitLines(highlighted)
    const rows = lines.map((lineHtml, i) => {
      const lineNum = lineOffset + i
      return `<tr data-line="${lineNum}"><td class="line-num">${lineNum}</td><td class="line-code">${lineHtml}</td></tr>`
    })

    return `<table class="hljs-table"><tbody>${rows.join('')}</tbody></table>`
  }

  return { highlight }
}
