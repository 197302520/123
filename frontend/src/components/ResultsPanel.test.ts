import { render, screen } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'
import ResultsPanel from './ResultsPanel.vue'
import { completedResult, historyRecord } from '../test/fixtures'

const stubs = {
  ResultChart: { props: ['chart'], template: '<div role="img" :aria-label="`结果图表：${chart.key}`"></div>' },
  GraphCanvas: { props: ['graph', 'overlay'], template: '<div role="img" aria-label="结果网络叠加图" :data-edges="graph.edges.length" :data-nodes="graph.nodes.map(node => node.id).join(\',\')" :data-directed="String(graph.directed)"></div>' },
}

describe('real result rendering', () => {
  test('renders backend tables, charts, overlays, warnings, and provenance', () => {
    render(ResultsPanel, { props: { result: completedResult }, global: { stubs } })

    expect(screen.getByRole('table', { name: '节点中心性' })).toHaveTextContent('0.5')
    expect(screen.getByRole('img', { name: '结果图表：ranking' })).toBeVisible()
    expect(screen.getByRole('img', { name: '结果网络叠加图' })).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent('孤立节点不会贡献连接。')
    expect(screen.getByText('graph-hash')).toBeVisible()
  })

  test('renders an explicit empty result instead of an empty panel', () => {
    render(ResultsPanel, { props: { result: { ...completedResult, tables: [], charts: [], overlays: [], warnings: [] } }, global: { stubs } })
    expect(screen.getByText('本次算法没有返回表格、图表或网络叠加层。')).toBeVisible()
  })

  test('adds backend-predicted candidate edges to the base graph overlay', () => {
    const result = {
      ...completedResult,
      overlays: [{ key: 'predicted_edges', nodes: [], edges: [{ source: 'a', target: 'c', score: 0.8 }], node_styles: {} }],
    }
    render(ResultsPanel, { props: { result }, global: { stubs } })

    expect(screen.getByRole('img', { name: '结果网络叠加图' })).toHaveAttribute('data-edges', '3')
    expect(screen.getByRole('img', { name: '结果网络叠加图' })).toHaveAttribute('data-nodes', 'a,b,c')
    expect(screen.getByText('候选关系以高对比虚线叠加在输入网络上。')).toBeVisible()
  })

  test.each([
    ['model.er', 'generated_graph', false],
    ['model.ws', 'generated_graph', false],
    ['model.ba', 'generated_graph', false],
    ['text.extract', 'extracted_graph', true],
  ])('renders %s complete-graph overlay as a replacement rather than merging the input', (algorithm, key, directed) => {
    const result = {
      ...completedResult,
      provenance: {
        ...completedResult.provenance,
        algorithm,
        ...(key === 'generated_graph' ? { generated_graph: { directed } } : { extraction: { graph: { directed } } }),
      },
      overlays: [{ key, nodes: [{ id: 'x', label: '新甲' }, { id: 'y', label: '新乙' }], edges: [{ source: 'x', target: 'y', weight: 1 }], node_styles: {} }],
    }
    render(ResultsPanel, { props: { result }, global: { stubs } })

    const graph = screen.getByRole('img', { name: '结果网络叠加图' })
    expect(graph).toHaveAttribute('data-nodes', 'x,y')
    expect(graph).toHaveAttribute('data-edges', '1')
    expect(graph).toHaveAttribute('data-directed', String(directed))
    expect(screen.getByText(key === 'generated_graph' ? '展示算法生成的新网络，未与输入图合并。' : '展示从文本抽取的新网络，未与输入图合并。')).toBeVisible()
  })

  test.each([
    ['node_values', '节点大小表示本次算法返回的数值。'],
    ['hits', '节点大小表示枢纽分数；颜色与标签表示权威分数。'],
    ['removal_order', '节点大小与标签表示移除顺序，越早移除越醒目。'],
    ['opinions', '节点大小表示最终意见值。'],
    ['communities', '节点颜色表示社区归属。'],
    ['latest_communities', '节点颜色表示最后一个快照的社区归属。'],
    ['embedding_clusters', '节点颜色表示嵌入空间中的聚类归属。'],
  ])('explains the visible mapping for backend overlay %s', (key, caption) => {
    const result = { ...completedResult, overlays: [{ key, nodes: [], edges: [], node_styles: {} }] }
    render(ResultsPanel, { props: { result }, global: { stubs } })

    expect(screen.getByText(caption)).toBeVisible()
  })

  test('juxtaposes parameter differences and actual result values for two distinct runs', () => {
    const currentRecord = { ...historyRecord, parameters: { iterations: 3 }, result: completedResult }
    const compareRecord = {
      ...historyRecord,
      id: 'run-previous',
      parameters: { iterations: 9 },
      result: {
        ...completedResult,
        run_id: 'run-previous',
        tables: [{ ...completedResult.tables[0], rows: [{ node: 'a', value: 0.25 }] }],
      },
    }
    render(ResultsPanel, { props: { result: completedResult, currentRecord, compareRecord }, global: { stubs } })
    const region = screen.getByRole('region', { name: '实验结果对比' })

    expect(region).toHaveTextContent('iterations')
    expect(region).toHaveTextContent('3')
    expect(region).toHaveTextContent('9')
    expect(region).toHaveTextContent('0.5')
    expect(region).toHaveTextContent('0.25')
  })

  test('does not compare a run with itself', () => {
    render(ResultsPanel, { props: { result: completedResult, currentRecord: historyRecord, compareRecord: historyRecord }, global: { stubs } })
    expect(screen.queryByRole('region', { name: '实验结果对比' })).not.toBeInTheDocument()
  })
})
