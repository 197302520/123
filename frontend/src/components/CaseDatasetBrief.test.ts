import { render, screen } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'
import CaseDatasetBrief from './CaseDatasetBrief.vue'
import type { CaseDataset, GraphSpec } from '../api/contracts'
import { exampleGraph } from '../test/fixtures'

const stubs = {
  GraphCanvas: {
    props: ['graph', 'label'],
    template: '<div role="img" :aria-label="label" :data-nodes="graph.nodes.length" :data-edges="graph.edges.length"></div>',
  },
}

const datasetOf = (metadata: Record<string, unknown>): CaseDataset => ({
  slug: 'brief-case', title: '测试数据集', provenance: '一份用于测试的公开数据。', metadata,
})

const triangle: GraphSpec = {
  directed: false,
  nodes: [{ id: 'a', label: '甲' }, { id: 'b', label: '乙' }, { id: 'c', label: '丙' }],
  edges: [
    { source: 'a', target: 'b', weight: 1 },
    { source: 'b', target: 'c', weight: 2 },
    { source: 'a', target: 'c', weight: 1 },
  ],
}

describe('dataset briefing for the case run stage', () => {
  test('surfaces dataset identity, computed stats, provenance facts, and raw samples', async () => {
    const user = (await import('@testing-library/user-event')).default.setup()
    render(CaseDatasetBrief, {
      props: {
        dataset: datasetOf({ source: '测试来源库', license: 'CC0', cleaning: '去除重复边', version: 'v9', node_attributes: { a: { faction: '红派' } } }),
        graph: triangle,
      },
      global: { stubs },
    })

    expect(screen.getByRole('heading', { name: '测试数据集' })).toBeVisible()
    expect(screen.getByText('一份用于测试的公开数据。')).toBeVisible()
    expect(screen.getByRole('img', { name: /3 个节点、3 条边/ })).toBeVisible()
    expect(screen.getByText('数据来源')).toBeVisible()
    expect(screen.getByText('测试来源库')).toBeVisible()
    expect(screen.getByText('去除重复边')).toBeVisible()
    expect(screen.getByText('1.000')).toBeVisible()

    await user.click(screen.getByText('查看原始数据样本（前 8 条）'))
    const nodesTable = screen.getByRole('table', { name: '节点数据样本' })
    expect(nodesTable).toHaveTextContent('faction=红派')
    const edgesTable = screen.getByRole('table', { name: '关系数据样本' })
    expect(edgesTable).toHaveTextContent('a')
    expect(edgesTable).toHaveTextContent('2')
    expect(screen.queryByText(/仅展示前 8 条样本/)).not.toBeInTheDocument()
  })

  test('switches between snapshot views for dynamic datasets', async () => {
    const user = (await import('@testing-library/user-event')).default.setup()
    const snapshot = (edges: GraphSpec['edges']): GraphSpec => ({ directed: false, nodes: triangle.nodes, edges })
    render(CaseDatasetBrief, {
      props: {
        dataset: datasetOf({
          parameters: { snapshots: [snapshot([]), snapshot(triangle.edges)] },
        }),
        graph: snapshot([]),
      },
      global: { stubs },
    })

    expect(screen.getByText('快照 t1')).toBeVisible()
    expect(screen.getByText(/运行时会把 2 期快照一起送入/)).toBeVisible()
    expect(screen.getByRole('img', { name: /案例数据集预览/ })).toHaveAttribute('data-edges', '0')

    await user.click(screen.getByText('快照 t2'))
    expect(screen.getByRole('img', { name: /案例数据集预览/ })).toHaveAttribute('data-edges', '3')
  })

  test('presents the source text instead of a graph for text-extraction cases', () => {
    render(CaseDatasetBrief, {
      props: {
        dataset: datasetOf({ parameters: { text: '云帆科技与星河数据建立联合实验室。' } }),
        graph: { directed: true, nodes: [], edges: [] },
      },
      global: { stubs },
    })

    expect(screen.getByText('云帆科技与星河数据建立联合实验室。')).toBeVisible()
    expect(screen.getByText(/运行下方分析时才会从中抽取实体与关系/)).toBeVisible()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })
})
