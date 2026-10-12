import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { getNodeColor, NODE_TYPE_CSS_VARS, ALL_NODE_TYPES } from '../../../src/constants/nodeColors'

// jsdom honours inline style.setProperty for CSS custom properties
function setVar(name: string, value: string) {
  document.documentElement.style.setProperty(name, value)
}
function removeVar(name: string) {
  document.documentElement.style.removeProperty(name)
}

describe('getNodeColor', () => {
  beforeEach(() => {
    setVar('--color-node-file', '#79c0ff')
    setVar('--color-node-package', '#e0a020')
    setVar('--color-node-class', '#58a6ff')
    setVar('--color-node-interface', '#79c0ff')
    setVar('--color-node-enum', '#ff9e64')
    setVar('--color-node-function', '#56d364')
    setVar('--color-node-method', '#d2a8ff')
    setVar('--color-node-constructor', '#c586c0')
    setVar('--color-node-variable', '#ffa28b')
    setVar('--color-node-import', '#6e7681')
    setVar('--color-node-external-module', '#4a4a5a')
    setVar('--color-node-default', '#808080')
  })

  afterEach(() => {
    Object.values(NODE_TYPE_CSS_VARS).forEach(removeVar)
    removeVar('--color-node-default')
  })

  it('returns the CSS var value for Class', () => {
    expect(getNodeColor('Class')).toBe('#58a6ff')
  })

  it('returns the CSS var value for Function', () => {
    expect(getNodeColor('Function')).toBe('#56d364')
  })

  it('returns the CSS var value for Method', () => {
    expect(getNodeColor('Method')).toBe('#d2a8ff')
  })

  it('returns the CSS var value for Interface', () => {
    expect(getNodeColor('Interface')).toBe('#79c0ff')
  })

  it('returns the CSS var value for Enum', () => {
    expect(getNodeColor('Enum')).toBe('#ff9e64')
  })

  it('returns the CSS var value for Constructor', () => {
    expect(getNodeColor('Constructor')).toBe('#c586c0')
  })

  it('returns the CSS var value for File', () => {
    expect(getNodeColor('File')).toBe('#79c0ff')
  })

  it('returns the CSS var value for Variable', () => {
    expect(getNodeColor('Variable')).toBe('#ffa28b')
  })

  it('returns the CSS var value for Import', () => {
    expect(getNodeColor('Import')).toBe('#6e7681')
  })

  it('returns the --color-node-default CSS var value for an unknown type', () => {
    setVar('--color-node-default', '#aabbcc')
    expect(getNodeColor('UnknownType')).toBe('#aabbcc')
  })

  it('returns hardcoded fallback #808080 when CSS vars are completely unset', () => {
    removeVar('--color-node-class')
    removeVar('--color-node-default')
    expect(getNodeColor('Class')).toBe('#808080')
  })

  it('ALL_NODE_TYPES matches NODE_TYPE_CSS_VARS keys', () => {
    expect(ALL_NODE_TYPES.sort()).toEqual(Object.keys(NODE_TYPE_CSS_VARS).sort())
  })

  it('NODE_TYPE_CSS_VARS has exactly 11 entries', () => {
    expect(Object.keys(NODE_TYPE_CSS_VARS)).toHaveLength(11)
  })
})
