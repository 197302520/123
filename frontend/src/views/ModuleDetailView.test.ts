import { render, screen } from '@testing-library/vue'
import { describe, expect, test, vi } from 'vitest'
import ModuleDetailView from './ModuleDetailView.vue'

const registryStub = vi.hoisted(() => [
  {
    key: 'graph.validate', name: '图结构验证', module: 'network-basics', version: '1.0',
    supported_graph_types: ['directed', 'undirected'], parameters: {},
    description: '验证图结构是否可用于后续分析。', limits: { max_nodes: 1, max_edges: 1 },
    formula: 'G=(V,E,w)', explanation: '验证图结构是否可用于后续分析。', advantages: ['错误定位到具体字段'], limitations: ['不评估数据的学科语义'],
  },
  {
    key: 'community.louvain', name: 'Louvain', module: 'communities', version: '1.0',
    supported_graph_types: ['undirected'], parameters: {},
    description: '交替局部移动与社区聚合优化模块度。', limits: { max_nodes: 1, max_edges: 1 },
    formula: 'Q=(1/2m)Σ…', explanation: '交替局部移动与社区聚合优化模块度。', advantages: ['大图上高效'], limitations: ['可产生内部不连通社区'],
  },
])

vi.mock('../api/client', () => ({
  fetchModule: vi.fn((slug: string) => Promise.resolve({ slug, title: `模块：${slug}`, summary: `${slug} 摘要`, order: 1, content: `${slug} 内容` })),
  fetchCases: vi.fn().mockResolvedValue([]),
  fetchAlgorithms: vi.fn(() => Promise.resolve(registryStub)),
}))
import { fetchAlgorithms, fetchCases, fetchModule } from '../api/client'

describe('module detail route changes', () => {
  test('reloads content when the module route parameter changes', async () => {
    const view = render(ModuleDetailView, {
      props: { slug: 'network-basics' },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    expect(await screen.findByRole('heading', { name: '模块：network-basics' })).toBeVisible()
    expect(await screen.findByRole('heading', { name: '本模块的 1 个可运行算法' })).toBeVisible()
    expect(screen.queryByText('Louvain')).not.toBeInTheDocument()

    await view.rerender({ slug: 'communities' })

    expect(await screen.findByRole('heading', { name: '模块：communities' })).toBeVisible()
    expect(await screen.findByText('Louvain')).toBeVisible()
    expect(fetchModule).toHaveBeenLastCalledWith('communities')
  })

  test('keeps the newest module when an older route request finishes last', async () => {
    vi.mocked(fetchCases).mockResolvedValue([])
    let resolveOlder!: (value: any) => void
    vi.mocked(fetchModule)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOlder = resolve }))
      .mockImplementationOnce(() => Promise.resolve({ slug: 'communities', title: '模块：communities', summary: '新摘要', order: 3, content: '新内容' }))
    const view = render(ModuleDetailView, {
      props: { slug: 'network-basics' },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })

    await view.rerender({ slug: 'communities' })
    expect(await screen.findByRole('heading', { name: '模块：communities' })).toBeVisible()
    resolveOlder({ slug: 'network-basics', title: '过期模块', summary: '旧摘要', order: 1, content: '旧内容' })
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(screen.getByRole('heading', { name: '模块：communities' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: '过期模块' })).not.toBeInTheDocument()
  })
})
