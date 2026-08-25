import type { GraphInputSpec, ValidationIssue } from '../api/contracts'

export class GraphInputError extends Error {}

function edgeList(text: string): GraphInputSpec {
  const nodeIds = new Set<string>()
  const edges = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((line, index) => {
    const [source, target, rawWeight, ...extra] = line.split(/[\s,;]+/)
    if (!source || !target || extra.length) throw new GraphInputError(`第 ${index + 1} 行应为“起点 终点 [权重]”。`)
    const weight = rawWeight === undefined ? 1 : Number(rawWeight)
    nodeIds.add(source)
    nodeIds.add(target)
    return { source, target, weight }
  })
  if (!edges.length) throw new GraphInputError('请粘贴 JSON 或至少一行边数据。')
  return { directed: false, nodes: [...nodeIds].map((id) => ({ id, label: id })), edges }
}

export function parseGraphText(text: string): GraphInputSpec {
  const normalized = text.trim()
  if (!normalized) throw new GraphInputError('图数据不能为空。')
  if (normalized.startsWith('{') || normalized.startsWith('[')) {
    try {
      return JSON.parse(normalized) as GraphInputSpec
    } catch {
      throw new GraphInputError('JSON 格式不完整，请检查括号、引号和逗号。')
    }
  }
  return edgeList(normalized)
}

export function validateGraphLocally(graph: GraphInputSpec): ValidationIssue[] {
  if (!graph || typeof graph !== 'object') return [{ path: '', message: '图必须是对象。' }]
  const issues: ValidationIssue[] = []
  if (typeof graph.directed !== 'boolean') issues.push({ path: 'directed', message: 'directed 必须是布尔值。' })
  if (!Array.isArray(graph.nodes) || !Array.isArray(graph.edges)) return [...issues, { path: '', message: 'nodes 和 edges 必须是数组。' }]
  const ids = new Set<string>()
  graph.nodes.forEach((node, index) => {
    if (!node || typeof node.id !== 'string' || !node.id.trim()) {
      issues.push({ path: `nodes[${index}].id`, message: '节点 id 必须是非空字符串。' })
    } else if (ids.has(node.id)) {
      issues.push({ path: `nodes[${index}].id`, message: `节点 '${node.id}' 重复。` })
    } else ids.add(node.id)
  })
  graph.edges.forEach((edge, index) => {
    if (!ids.has(edge.source)) issues.push({ path: `edges[${index}].source`, message: `节点 '${edge.source}' 不存在。` })
    if (!ids.has(edge.target)) issues.push({ path: `edges[${index}].target`, message: `节点 '${edge.target}' 不存在。` })
    const weight = edge.weight ?? 1
    if (typeof weight !== 'number' || !Number.isFinite(weight) || weight <= 0) {
      issues.push({ path: `edges[${index}].weight`, message: '边权重必须是大于 0 的有限数值。' })
    }
  })
  return issues
}

export function serializeGraph(graph: GraphInputSpec, learningExample = false): string {
  const serialized = JSON.stringify(graph, null, 2)
  return learningExample ? `教学示例（可编辑，非算法结果）\n${serialized}` : serialized
}

export function stripLearningLabel(text: string): string {
  return text.replace(/^教学示例（可编辑，非算法结果）\r?\n/, '')
}
