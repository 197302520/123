export interface GraphNode { id: string; label: string }
export interface GraphEdge { source: string; target: string; weight: number }
export interface GraphSpec { directed: boolean; nodes: GraphNode[]; edges: GraphEdge[] }
export interface AlgorithmSpec {
  key: string
  name: string
  supported_graph_types: Array<'directed' | 'undirected'>
  parameters: Record<string, unknown>
  version: string
  description: string
}
export interface RunRequest {
  algorithm: string
  graph: GraphSpec
  parameters: Record<string, unknown>
  seed?: number | null
}
export interface RunResult {
  run_id: string
  status: string
  tables: unknown[]
  charts: unknown[]
  warnings: string[]
  provenance: Record<string, unknown>
}
export interface CourseModule { slug: string; title: string; summary: string; order: number }
