import { render, screen } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'
import ResultsPanel from './ResultsPanel.vue'
import { completedResult } from '../test/fixtures'

const stubs = {
  ResultChart: { props: ['chart'], template: '<div role="img" :aria-label="`结果图表：${chart.key}`"></div>' },
  GraphCanvas: { props: ['graph', 'overlay'], template: '<div role="img" aria-label="结果网络叠加图"></div>' },
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

  test('labels current and historical runs in side-by-side comparison', () => {
    render(ResultsPanel, { props: { result: completedResult, compareResult: { ...completedResult, run_id: 'run-previous' } }, global: { stubs } })
    expect(screen.getByRole('region', { name: '实验结果对比' })).toHaveTextContent('当前实验')
    expect(screen.getByRole('region', { name: '实验结果对比' })).toHaveTextContent('对比实验')
    expect(screen.getByRole('region', { name: '实验结果对比' })).toHaveTextContent('run-previous')
  })
})
