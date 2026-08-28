import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import CaseDetailView from './CaseDetailView.vue'
import type { AlgorithmSpec, RunResult } from '../api/contracts'

vi.mock('../api/client', () => ({
  fetchCase: vi.fn((slug: string) => Promise.resolve({
    slug,
    title: slug === 'dolphins' ? '海豚社交网络' : '空手道俱乐部网络',
    summary: '社区分裂的经典案例。',
    module: 'communities',
    content: '俱乐部在冲突后分裂成两个群体。',
    dataset: { slug: 'karate', title: 'Zachary 数据', provenance: 'Zachary (1977)', metadata: { nodes: 34, edges: 78 } },
  })),
  fetchAlgorithms: vi.fn(() => Promise.resolve([])),
  submitRun: vi.fn(),
  fetchRunStatus: vi.fn(),
  fetchRunResult: vi.fn(),
}))
import { fetchAlgorithms, fetchCase, fetchRunResult, fetchRunStatus, submitRun } from '../api/client'

const karateGraph = {
  directed: false,
  nodes: [{ id: '0', label: '校长' }, { id: '1', label: '教官' }],
  edges: [{ source: '0', target: '1', weight: 2 }],
}

function stubBuiltInDemo() {
  vi.mocked(fetchCase).mockResolvedValueOnce({
    slug: 'karate', title: '空手道俱乐部网络', summary: '社区分裂的经典案例。', module: 'communities', content: '',
    dataset: {
      slug: 'karate', title: 'Zachary 数据', provenance: 'Zachary (1977)',
      metadata: {
        graph: karateGraph,
        demos: [{ algorithm: 'centrality.degree', label: '度中心性：谁朋友最多', focus: '找朋友最多的节点。', seed: 7 }],
      },
    },
  })
  vi.mocked(fetchAlgorithms).mockResolvedValue([{
    key: 'centrality.degree', name: '度中心性', supported_graph_types: ['undirected'],
    parameters: {}, version: 'v1', description: '', limits: { max_nodes: 2000, max_edges: 20000 },
    formula: '', explanation: '', advantages: [], limitations: [], module: 'network-measures',
  } satisfies AlgorithmSpec])
  vi.mocked(submitRun).mockResolvedValue({ id: 'run-1', status: 'pending', algorithm: 'centrality.degree', seed: 7 })
  vi.mocked(fetchRunStatus).mockResolvedValue({ id: 'run-1', status: 'completed', algorithm: 'centrality.degree', seed: 7 })
  const result: RunResult = {
    run_id: 'run-1', status: 'completed',
    tables: [{ key: 'degree', name: '度中心性', columns: ['node', 'value'], rows: [{ node: '0', value: 1 }] }],
    overlays: [], charts: [], warnings: [], provenance: {},
    validation: { valid: true, errors: [], graph: karateGraph },
  }
  vi.mocked(fetchRunResult).mockResolvedValue(result)
}

describe('six-section case learning flow', () => {
  test('exposes exactly six keyboard-navigable sections and changes the active lesson', async () => {
    const user = userEvent.setup()
    render(CaseDetailView, {
      props: { slug: 'karate' },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, ExampleNetwork: true, GraphCanvas: true } },
    })

    expect(await screen.findByRole('heading', { name: '空手道俱乐部网络' })).toBeVisible()
    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(6)
    expect(tabs.map((tab) => tab.textContent?.trim())).toEqual([
      '提出问题', '认识数据', '选择方法', '运行分析', '解释发现', '反思迁移',
    ])

    tabs[0].focus()
    await user.keyboard('{ArrowRight}')
    expect(tabs[1]).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel')).toHaveTextContent('节点与关系')
  })

  test('reloads when the case route parameter changes', async () => {
    const view = render(CaseDetailView, {
      props: { slug: 'karate' },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, ExampleNetwork: true, GraphCanvas: true } },
    })
    expect(await screen.findByRole('heading', { name: '空手道俱乐部网络' })).toBeVisible()

    await view.rerender({ slug: 'dolphins' })

    expect(await screen.findByRole('heading', { name: '海豚社交网络' })).toBeVisible()
    expect(fetchCase).toHaveBeenLastCalledWith('dolphins')
  })

  test('does not let an older case request overwrite a newer route', async () => {
    let resolveOlder!: (value: any) => void
    vi.mocked(fetchCase)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOlder = resolve }))
      .mockResolvedValueOnce({
        slug: 'dolphins', title: '海豚社交网络', summary: '海豚社群边界', module: 'communities', content: '新案例', dataset: null,
      })
    const view = render(CaseDetailView, {
      props: { slug: 'karate' },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, ExampleNetwork: true, GraphCanvas: true } },
    })

    await view.rerender({ slug: 'dolphins' })
    expect(await screen.findByRole('heading', { name: '海豚社交网络' })).toBeVisible()
    resolveOlder({ slug: 'karate', title: '过期空手道案例', summary: '旧数据', module: 'communities', content: '旧案例', dataset: null })
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(screen.getByRole('heading', { name: '海豚社交网络' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: '过期空手道案例' })).not.toBeInTheDocument()
  })

  test('runs the built-in case analysis inline without leaving the case page', async () => {
    const user = userEvent.setup()
    stubBuiltInDemo()
    render(CaseDetailView, {
      props: { slug: 'karate' },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, ExampleNetwork: true, GraphCanvas: true } },
    })
    expect(await screen.findByRole('heading', { name: '空手道俱乐部网络' })).toBeVisible()

    await user.click(screen.getByRole('tab', { name: '运行分析' }))
    expect(await screen.findByText('度中心性：谁朋友最多')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Zachary 数据' })).toBeVisible()

    await user.click(screen.getByRole('button', { name: '运行分析' }))

    expect(submitRun).toHaveBeenCalledWith(
      expect.objectContaining({ algorithm: 'centrality.degree', seed: 7 }),
      undefined,
    )
    expect(await screen.findByRole('table', { name: '度中心性' })).toBeVisible()
    expect(screen.getByRole('button', { name: '重新运行' })).toBeVisible()
  })

  test('explains the built-in demos in the interpretation section', async () => {
    const user = userEvent.setup()
    stubBuiltInDemo()
    render(CaseDetailView, {
      props: { slug: 'karate' },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, ExampleNetwork: true, GraphCanvas: true } },
    })
    expect(await screen.findByRole('heading', { name: '空手道俱乐部网络' })).toBeVisible()

    await user.click(screen.getByRole('tab', { name: '解释发现' }))

    expect(await screen.findByText(/对照「运行分析」/)).toBeVisible()
    expect(screen.getByText(/度中心性：谁朋友最多/)).toBeVisible()
  })
})
