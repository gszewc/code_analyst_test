import { describe, it, expect } from 'vitest'
import { projectCreateSchema } from '../../../src/schemas/project'

describe('projectCreateSchema', () => {
  it('accepts valid names', () => {
    const result = projectCreateSchema.safeParse({ name: 'my-project' })
    expect(result.success).toBe(true)
  })

  it('accepts names with underscores and spaces', () => {
    const result = projectCreateSchema.safeParse({ name: 'my_legacy app-v2' })
    expect(result.success).toBe(true)
  })

  it('rejects empty name', () => {
    const result = projectCreateSchema.safeParse({ name: '' })
    expect(result.success).toBe(false)
    expect(result.error?.issues[0].message).toContain('required')
  })

  it('rejects names with special characters', () => {
    const result = projectCreateSchema.safeParse({ name: 'my/project' })
    expect(result.success).toBe(false)
  })

  it('rejects names longer than 255 chars', () => {
    const result = projectCreateSchema.safeParse({ name: 'a'.repeat(256) })
    expect(result.success).toBe(false)
  })

  it('accepts optional description', () => {
    const result = projectCreateSchema.safeParse({ name: 'test', description: 'A project' })
    expect(result.success).toBe(true)
  })

  it('rejects description longer than 1000 chars', () => {
    const result = projectCreateSchema.safeParse({ name: 'test', description: 'x'.repeat(1001) })
    expect(result.success).toBe(false)
  })

  it('accepts empty description', () => {
    const result = projectCreateSchema.safeParse({ name: 'test', description: '' })
    expect(result.success).toBe(true)
  })
})
