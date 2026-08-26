export interface GraphNode { id: string; label: string; attributes?: Record<string, unknown> }
export interface GraphEdge { source: string; target: string; weight: number }
export interface GraphSpec { directed: boolean; nodes: GraphNode[]; edges: GraphEdge[] }
export interface GraphInputNode { id: string; label?: string; attributes?: Record<string, unknown> }
export interface GraphInputEdge { source: string; target: string; weight?: number }
export interface GraphInputSpec { directed: boolean; nodes: GraphInputNode[]; edges: GraphInputEdge[] }

export interface ValidationIssue { path: string; message: string }
export interface GraphValidation {
  valid: boolean
  errors: ValidationIssue[]
  graph?: GraphSpec
}

export type ParameterValue = string | number | boolean | unknown[] | Record<string, unknown> | null
export interface ParameterDefinition {
  type: 'integer' | 'number' | 'string' | 'boolean' | 'array' | 'object'
  default: ParameterValue
  description: string
  minimum?: number
  maximum?: number
  choices?: string[]
}

export interface AlgorithmSpec {
  key: string
  name: string
  supported_graph_types: Array<'directed' | 'undirected'>
  parameters: Record<string, ParameterDefinition>
  version: string
  description: string
  limits: { max_nodes: number; max_edges: number }
  formula: string
  explanation: string
  advantages: string[]
  limitations: string[]
}
export interface RunRequest {
  algorithm: string
  graph: GraphInputSpec
  parameters: Record<string, unknown>
  seed?: number | null
}

export interface RunTable {
  key: string
  name: string
  columns: string[]
  rows: Array<Record<string, unknown>>
}
export interface RunSeries { name: string; data: Array<Record<string, unknown> | string | number> }
export interface RunChart { key: string; type: string; series: RunSeries[]; [key: string]: unknown }
export interface RunOverlay {
  key: string
  nodes: Array<Record<string, unknown>>
  edges: Array<Record<string, unknown>>
  node_styles: Record<string, Record<string, unknown>>
}
export interface RunResult {
  run_id: string
  status: string
  tables: RunTable[]
  overlays: RunOverlay[]
  charts: RunChart[]
  warnings: string[]
  provenance: Record<string, unknown>
  validation: { valid: boolean; errors: ValidationIssue[]; graph: GraphSpec }
}

export interface RunStatus {
  id: string
  status: 'pending' | 'completed' | 'failed' | string
  algorithm: string
  seed: number | null
}
export interface CourseModule { slug: string; title: string; summary: string; order: number }
export interface CourseModuleDetail extends CourseModule { content: string }
export interface CaseSummary { slug: string; title: string; summary: string; module: string }
export interface CaseDataset { slug: string; title: string; provenance: string; metadata: Record<string, unknown> }
export interface CaseDetail extends CaseSummary { content: string; dataset: CaseDataset | null }

export interface HistoryRecord {
  id: string
  createdAt: string
  algorithm: string
  algorithmName: string
  parameters: Record<string, unknown>
  seed: number | null
  graph: GraphSpec
  result: RunResult
}
