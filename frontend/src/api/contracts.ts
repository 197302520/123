export interface GraphNode { id: string; label: string }
export interface GraphEdge { source: string; target: string; weight: number }
export interface GraphSpec { directed: boolean; nodes: GraphNode[]; edges: GraphEdge[] }
export interface GraphInputNode { id: string; label?: string }
export interface GraphInputEdge { source: string; target: string; weight?: number }
export interface GraphInputSpec { directed: boolean; nodes: GraphInputNode[]; edges: GraphInputEdge[] }
export interface AlgorithmSpec {
  key: string
  name: string
  supported_graph_types: Array<'directed' | 'undirected'>
  parameters: Record<string, unknown>
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
export interface RunResult {
  run_id: string
  status: string
  tables: unknown[]
  overlays: unknown[]
  charts: unknown[]
  warnings: string[]
  provenance: Record<string, unknown>
  validation: { valid: boolean; errors: Array<{ path: string; message: string }>; graph: GraphSpec }
}
export interface CourseModule { slug: string; title: string; summary: string; order: number }
