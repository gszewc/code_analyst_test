import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { ApiRequestError } from '../../../src/api/client'

describe('API client error handling', () => {
  const originalFetch = global.fetch

  beforeEach(() => {
    // Restore fetch before each test
    global.fetch = originalFetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('ApiRequestError carries status and detail', () => {
    const err = new ApiRequestError(404, 'Project not found')
    expect(err.status).toBe(404)
    expect(err.detail).toBe('Project not found')
    expect(err.message).toBe('Project not found')
    expect(err.name).toBe('ApiRequestError')
  })

  it('ApiRequestError is instanceof Error', () => {
    const err = new ApiRequestError(500, 'Internal error')
    expect(err).toBeInstanceOf(Error)
    expect(err).toBeInstanceOf(ApiRequestError)
  })

  it('throws ApiRequestError with detail from 4xx response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: () => Promise.resolve({ detail: 'Bad request body' }),
    } as Response)

    const { api } = await import('../../../src/api/client')
    await expect(api.projects.list()).rejects.toMatchObject({
      status: 400,
      detail: 'Bad request body',
    })
  })

  it('throws ApiRequestError with status text fallback when no detail', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.reject(new SyntaxError('invalid json')),
    } as Response)

    const { api } = await import('../../../src/api/client')
    await expect(api.projects.list()).rejects.toMatchObject({
      status: 500,
    })
  })
})
