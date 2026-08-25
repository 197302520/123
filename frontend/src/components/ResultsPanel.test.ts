import { render, screen } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'
import ResultsPanel from './ResultsPanel.vue'
import { completedResult, historyRecord } from '../test/fixtures'

const stubs = {
  ResultChart: { props: ['chart'], template: '<div role="img" :aria-label="`结果图表：${chart.key}`"></div>' },
  GraphCanvas: { props: ['graph', 'overlay'], template: '<div role="img" aria-label="结果网络叠加图" :data-edges="graph.edges.length"></div>' },
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
