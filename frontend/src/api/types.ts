// All TypeScript interfaces matching backend API contracts
// Source: specs/001-frontend-spa/contracts/api-contracts.md

// ── Error ──────────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string
}

// ── Health ─────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  version: string
  sqlite: string
  neo4j: string | null
}

// ── Projects ───────────────────────────────────────────────────────────────

export interface ProjectResponse {
  id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
  is_deleted: boolean
}

export interface ProjectListResponse {
  projects: ProjectResponse[]
  total: number
}

export interface CreateProjectRequest {
  name: string
  description?: string
}

export interface UpdateProjectRequest {
  name?: string
  description?: string
}

// ── Files ──────────────────────────────────────────────────────────────────

export interface UploadSessionResponse {
  session_id: string
  project_id: string
  file_count: number
  extracted_path: string
}

export interface FileEntry {
  name: string
  path: string
  size: number
  is_directory: boolean
}

export interface FileListResponse {
  files: FileEntry[]
  total: number
}

export interface FileContentResponse {
  content: string
}

// ── Analysis ───────────────────────────────────────────────────────────────

export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface AnalysisJobResponse {
  id: string
  project_id: string
  status: AnalysisStatus
  progress: number | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
}

export interface AnalysisJobListResponse {
  jobs: AnalysisJobResponse[]
  total: number
}

export type ASTNodeType =
  | 'File'
  | 'Package'
  | 'Class'
  | 'Interface'
  | 'Enum'
  | 'Function'
  | 'Method'
  | 'Constructor'
  | 'Variable'
  | 'Import'
  | 'ExternalModule'

export type ASTRelationshipType =
  | 'CONTAINS'
  | 'EXTENDS'
  | 'IMPLEMENTS'
  | 'CALLS'
  | 'DEPENDS_ON'
  | 'USES'
  | 'IMPORTS'

export interface AnalysisDefaultsResponse {
  delete_graph_data: boolean
  enabled_node_types: ASTNodeType[]
  enabled_relationship_types: ASTRelationshipType[]
}

export interface ConfigDefaultsResponse {
  graph_default_visible_nodes: string[]
  analysis_default_enabled_node_types: string[]
  enabled_relationship_types: string[]
  delete_graph_data: boolean
}

export interface AnalysisStartConfig {
  cross_file_relations?: {
    imports?: boolean
    inheritance?: boolean
    calls?: boolean
    usage?: boolean
    include_external?: boolean
  }
  delete_graph_data?: boolean
  enabled_node_types?: ASTNodeType[]
  enabled_relationship_types?: ASTRelationshipType[]
}

export interface GraphSummaryResponse {
  total_nodes: number
  nodes_by_type: Record<string, number>
  total_relationships: number
  relationships_by_type: Record<string, number>
}

export interface ProgressEvent {
  percentage: number
  current_file: string | null
}

export interface CompleteEvent {
  job_id: string
  status: 'completed' | 'failed'
  error_message: string | null
  node_count: number
  relationship_count: number
}

// ── Graph ──────────────────────────────────────────────────────────────────

export type NodeType =
  | 'Class'
  | 'Function'
  | 'Method'
  | 'Module'
  | 'File'
  | 'Variable'
  | 'Import'
  | string

export interface GraphNode {
  id: string
  type: NodeType
  name: string
  source_file: string | null
  start_line: number | null
  end_line: number | null
  start_column?: number | null
  end_column?: number | null
  signature?: string | null
  decorators?: string[]
  base_classes?: string[]
  data_type?: string | null
  [key: string]: unknown
}

export interface NodeListResponse {
  nodes: GraphNode[]
  total: number
  limit: number
}

export interface NodeResponse {
  node: GraphNode
}

export interface GraphRelationship {
  type: string
  source_id: string
  target_id: string
  project_id?: string
  source?: {
    id: string
    type: string
    name: string
    source_file?: string | null
  }
  target?: {
    id: string
    type: string
    name: string
    source_file?: string | null
  }
  [key: string]: unknown
}

export interface RelationshipListResponse {
  relationships: GraphRelationship[]
  total: number
}

export interface NodeSearchResponse {
  nodes: GraphNode[]
  total: number
  query: string
  limit: number
}

export interface ProjectStatsResponse {
  project_id: string
  node_count: number
  relationship_count: number
}

// ── LLM / Settings ─────────────────────────────────────────────────────────

export type LLMProvider = 'openai' | 'anthropic' | 'ollama'

export interface LLMConfigResponse {
  provider: LLMProvider | null
  model: string | null
  base_url: string | null
  is_configured: boolean
}

export interface LLMConfigUpdateRequest {
  provider: LLMProvider
  model: string
  api_key?: string
  base_url?: string
}

export interface LLMTestResponse {
  success: boolean
  message: string
}

export interface GeneratedDocResponse {
  node_id: string
  content: string
  generated_at: string
}
