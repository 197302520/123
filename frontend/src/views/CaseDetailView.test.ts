import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import CaseDetailView from './CaseDetailView.vue'

vi.mock('../api/client', () => ({
  fetchCase: vi.fn((slug: string) => Promise.resolve({
    slug,
    title: slug === 'dolphins' ? '海豚社交网络' : '空手道俱乐部网络',
    summary: '社区分裂的经典案例。',
    module: 'communities',
    content: '俱乐部在冲突后分裂成两个群体。',
    dataset: { slug: 'karate', title: 'Zachary 数据', provenance: 'Zachary (1977)', metadata: { nodes: 34, edges: 78 } },
  })),
}))
import { fetchCase } from '../api/client'

describe('six-section case learning flow', () => {
  test('exposes exactly six keyboard-navigable sections and changes the active lesson', async () => {
    const user = userEvent.setup()
    render(CaseDetailView, {
      props: { slug: 'karate' },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, ExampleNetwork: true } },
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
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, ExampleNetwork: true } },
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
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' }, ExampleNetwork: true } },
    })

    await view.rerender({ slug: 'dolphins' })
    expect(await screen.findByRole('heading', { name: '海豚社交网络' })).toBeVisible()
    resolveOlder({ slug: 'karate', title: '过期空手道案例', summary: '旧数据', module: 'communities', content: '旧案例', dataset: null })
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(screen.getByRole('heading', { name: '海豚社交网络' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: '过期空手道案例' })).not.toBeInTheDocument()
  })
})
