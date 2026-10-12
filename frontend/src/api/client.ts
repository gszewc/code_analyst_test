// Typed fetch-based API client for all /api/v1 endpoints
import type {
  ApiError,
  HealthResponse,
  ProjectListResponse,
  ProjectResponse,
  CreateProjectRequest,
  UpdateProjectRequest,
  UploadSessionResponse,
  FileListResponse,
  FileContentResponse,
  AnalysisJobResponse,
  AnalysisJobListResponse,
  NodeListResponse,
  NodeResponse,
  NodeSearchResponse,
  RelationshipListResponse,
  ProjectStatsResponse,
  GeneratedDocResponse,
  LLMConfigResponse,
  LLMConfigUpdateRequest,
  LLMTestResponse,
  AnalysisDefaultsResponse,
  AnalysisStartConfig,
  GraphSummaryResponse,
  ConfigDefaultsResponse,
} from './types'

// Resolve base URL: env var → window.__ENV__ → localhost fallback
declare global {
  interface Window {
    __ENV__?: { API_BASE_URL?: string }
  }
}

export function getBaseUrl(): string {
  return (
    import.meta.env.VITE_API_BASE_URL ??
    window.__ENV__?.API_BASE_URL ??
    'http://localhost:8080'
  )
}

export class ApiRequestError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail)
    this.name = 'ApiRequestError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${getBaseUrl()}/api/v1${path}`
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (res.status === 204) return undefined as T

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = (await res.json()) as ApiError
      detail = body.detail ?? detail
    } catch {
      // ignore parse errors
    }
    throw new ApiRequestError(res.status, detail)
  }

  return res.json() as Promise<T>
}

export const api = {
  // ── Health ────────────────────────────────────────────────────────────────
  health: {
    check: (): Promise<HealthResponse> =>
      fetch(`${getBaseUrl()}/health`)
        .then((r) => r.json() as Promise<HealthResponse>)
        .catch(() => ({ status: 'unhealthy', version: 'unknown', sqlite: 'unknown', neo4j: null } satisfies HealthResponse)),
  },

  // ── Projects ──────────────────────────────────────────────────────────────
  projects: {
    list: (): Promise<ProjectListResponse> => request('/projects/'),
    get: (id: string): Promise<ProjectResponse> => request(`/projects/${id}`),
    create: (body: CreateProjectRequest): Promise<ProjectResponse> =>
      request('/projects/', { method: 'POST', body: JSON.stringify(body) }),
    update: (id: string, body: UpdateProjectRequest): Promise<ProjectResponse> =>
      request(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
    delete: (id: string): Promise<void> =>
      request(`/projects/${id}`, { method: 'DELETE' }),
  },

  // ── Files ─────────────────────────────────────────────────────────────────
  files: {
    upload: (
      projectId: string,
      file: File,
      onProgress?: (pct: number) => void
    ): Promise<UploadSessionResponse> => {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest()
        const formData = new FormData()
        formData.append('file', file)

        if (onProgress) {
          xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
              onProgress(Math.round((e.loaded / e.total) * 100))
            }
          })
        }

        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              resolve(JSON.parse(xhr.responseText) as UploadSessionResponse)
            } catch {
              reject(new ApiRequestError(xhr.status, 'Invalid response format'))
            }
          } else {
            let detail = `HTTP ${xhr.status}`
            try {
              const body = JSON.parse(xhr.responseText) as ApiError
              detail = body.detail ?? detail
            } catch {
              // ignore
            }
            reject(new ApiRequestError(xhr.status, detail))
          }
        })

        xhr.addEventListener('error', () =>
          reject(new ApiRequestError(0, 'Network error'))
        )

        xhr.open('POST', `${getBaseUrl()}/api/v1/projects/${projectId}/upload`)
        xhr.send(formData)
      })
    },

    list: (projectId: string, path?: string): Promise<FileListResponse> => {
      const params = path ? `?path=${encodeURIComponent(path)}` : ''
      return request(`/projects/${projectId}/files${params}`)
    },

    getContent: (projectId: string, filepath: string): Promise<FileContentResponse> =>
      request(`/projects/${projectId}/files/${filepath}`),
  },

  // ── Analysis ──────────────────────────────────────────────────────────────
  analysis: {
    start: (projectId: string, config?: AnalysisStartConfig): Promise<AnalysisJobResponse> =>
      request(`/analysis/projects/${projectId}/analyze`, {
        method: 'POST',
        ...(config ? { body: JSON.stringify(config) } : {}),
      }),
    getJob: (jobId: string): Promise<AnalysisJobResponse> =>
      request(`/analysis/jobs/${jobId}`),
    listJobs: (projectId: string): Promise<AnalysisJobListResponse> =>
      request(`/analysis/projects/${projectId}/jobs`),
    streamUrl: (jobId: string): string =>
      `${getBaseUrl()}/api/v1/analysis/jobs/${jobId}/stream`,
    getDefaults: (): Promise<AnalysisDefaultsResponse> =>
      request('/analysis/defaults'),
    getGraphSummary: (projectId: string): Promise<GraphSummaryResponse> =>
      request(`/analysis/projects/${projectId}/graph-summary`),
  },

  // ── Graph ─────────────────────────────────────────────────────────────────
  graph: {
    listNodes: (projectId: string, options?: { nodeType?: string; limit?: number }): Promise<NodeListResponse> => {
      const params = new URLSearchParams()
      if (options?.nodeType) params.set('node_type', options.nodeType)
      if (options?.limit !== undefined) params.set('limit', String(options.limit))
      const qs = params.toString() ? `?${params}` : ''
      return request(`/projects/${projectId}/nodes${qs}`)
    },
    getNode: (projectId: string, nodeId: string): Promise<NodeResponse> =>
      request(`/projects/${projectId}/nodes/${nodeId}`),
    listRelationships: (
      projectId: string,
      nodeId?: string,
      direction?: 'incoming' | 'outgoing' | 'both',
      options?: { limit?: number }
    ): Promise<RelationshipListResponse> => {
      if (nodeId) {
        const params = direction ? `?direction=${direction}` : ''
        return request(`/projects/${projectId}/nodes/${nodeId}/relationships${params}`)
      }
      const params = options?.limit !== undefined ? `?limit=${options.limit}` : ''
      return request(`/projects/${projectId}/relationships${params}`)
    },
    search: (projectId: string, q: string, options?: { nodeType?: string; limit?: number }): Promise<NodeSearchResponse> => {
      const params = new URLSearchParams({ q })
      if (options?.nodeType) params.set('node_type', options.nodeType)
      if (options?.limit !== undefined) params.set('limit', String(options.limit))
      return request(`/projects/${projectId}/search?${params}`)
    },
    stats: (projectId: string): Promise<ProjectStatsResponse> =>
      request(`/projects/${projectId}/stats`),
  },

  // ── Config ────────────────────────────────────────────────────────────────
  config: {
    getDefaults: (): Promise<ConfigDefaultsResponse> => request('/config/defaults'),
  },

  // ── LLM / Settings ────────────────────────────────────────────────────────
  llm: {
    getConfig: (): Promise<LLMConfigResponse> => request('/settings/llm'),
    updateConfig: (body: LLMConfigUpdateRequest): Promise<LLMConfigResponse> =>
      request('/settings/llm', { method: 'PUT', body: JSON.stringify(body) }),
    testConnection: (): Promise<LLMTestResponse> =>
      request('/settings/llm/test', { method: 'POST' }),
    generateNodeDocs: (projectId: string, nodeId: string): Promise<GeneratedDocResponse> =>
      request(`/projects/${projectId}/nodes/${nodeId}/docs`, { method: 'POST' }),
  },
}
