import type { AlgorithmSpec, CaseSummary, GraphSpec, HistoryRecord, RunResult } from '../api/contracts'

export const exampleGraph: GraphSpec = {
  directed: false,
  nodes: [
    { id: 'a', label: '甲' },
    { id: 'b', label: '乙' },
    { id: 'c', label: '丙' },
  ],
  edges: [
    { source: 'a', target: 'b', weight: 1 },
    { source: 'b', target: 'c', weight: 1 },
  ],
}

export const degreeAlgorithm: AlgorithmSpec = {
  key: 'centrality.degree',
  name: '度中心性',
  supported_graph_types: ['directed', 'undirected'],
  parameters: {
    normalized: { type: 'boolean', default: true, description: '是否归一化。' },
    iterations: { type: 'integer', default: 3, description: '迭代次数。', minimum: 1, maximum: 20 },
    mode: { type: 'string', default: 'all', description: '计算方式。', choices: ['all', 'in', 'out'] },
  },
  version: '1.0',
  description: '衡量节点直接连接数量。',
  limits: { max_nodes: 10_000, max_edges: 100_000 },
  formula: 'C_D(v)=\\frac{deg(v)}{n-1}',
  explanation: '连接越多，局部影响力通常越强。',
  advantages: ['直观'],
  limitations: ['只观察一步邻居'],
}

export const completedResult: RunResult = {
  run_id: 'run-1',
  status: 'completed',
  tables: [{
    key: 'nodes',
    name: '节点中心性',
    columns: ['node', 'value'],
    rows: [{ node: 'a', value: 0.5 }, { node: 'b', value: 1 }],
  }],
  overlays: [{
    key: 'node_values',
    nodes: [{ node: 'a', value: 0.5 }, { node: 'b', value: 1 }],
    edges: [],
    node_styles: {},
  }],
  charts: [{
    key: 'ranking',
    type: 'bar',
    series: [{ name: '度中心性', data: [{ x: 'b', y: 1 }, { x: 'a', y: 0.5 }] }],
  }],
  warnings: ['孤立节点不会贡献连接。'],
  provenance: {
    algorithm: 'centrality.degree',
    version: '1.0',
    seed: 7,
    graph_hash: 'graph-hash',
    parameter_hash: 'parameter-hash',
  },
  validation: { valid: true, errors: [], graph: exampleGraph },
}

export const cases: CaseSummary[] = [
  { slug: 'karate', title: '空手道俱乐部网络', summary: '社区分裂的经典案例。', module: 'communities' },
  { slug: 'dolphins', title: '海豚社交网络', summary: '观察动物社群边界。', module: 'communities' },
  { slug: 'opinion', title: '意见如何趋同', summary: '比较意见动力学。', module: 'diffusion' },
]

export const historyRecord: HistoryRecord = {
  id: 'run-1',
  createdAt: '2026-08-25T08:00:00.000Z',
  algorithm: 'centrality.degree',
  algorithmName: '度中心性',
  parameters: { normalized: true },
  seed: 7,
  graph: exampleGraph,
  result: completedResult,
}
