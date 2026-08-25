import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import PresentationView from './PresentationView.vue'

vi.mock('../api/client', () => ({
  fetchCase: vi.fn((slug: string) => Promise.resolve({
    slug,
    title: slug === 'dolphins' ? '海豚社交网络' : '空手道俱乐部网络',
    summary: slug === 'dolphins' ? '海豚社群边界' : '社区分裂',
    module: 'communities',
    content: slug === 'dolphins' ? '追踪海豚之间的结伴关系。' : '俱乐部冲突后分裂。',
    dataset: { slug, title: `${slug} 数据集`, provenance: '课堂数据档案', metadata: { nodes: 34 } },
  })),
}))
import { fetchCase } from '../api/client'

const global = { stubs: { RouterLink: { template: '<a><slot /></a>' } } }

describe('presentation keyboard controls', () => {
  test('moves through six case-specific lesson scenes with arrow keys', async () => {
    const user = userEvent.setup()
    render(PresentationView, { props: { slug: 'karate' }, global })

    expect(await screen.findByText('01 / 06')).toBeVisible()
    expect(screen.getByText(/俱乐部冲突后分裂/)).toBeVisible()
    await user.keyboard('{ArrowRight}')
    expect(screen.getByText('02 / 06')).toBeVisible()
    expect(screen.getAllByText(/karate 数据集/)).toHaveLength(2)
    await user.keyboard('{ArrowLeft}')
    expect(screen.getByText('01 / 06')).toBeVisible()
  })

  test('ignores global shortcuts from interactive controls so Space advances only once', async () => {
    const user = userEvent.setup()
    render(PresentationView, { props: { slug: 'karate' }, global })
    const next = await screen.findByRole('button', { name: '下一节 →' })

    next.focus()
    await user.keyboard(' ')

    expect(screen.getByText('02 / 06')).toBeVisible()
  })

  test('reloads case-specific scenes when the route prop changes', async () => {
    const view = render(PresentationView, { props: { slug: 'karate' }, global })
    expect(await screen.findByText('空手道俱乐部网络')).toBeVisible()

    await view.rerender({ slug: 'dolphins' })

    expect(await screen.findByText('海豚社交网络')).toBeVisible()
    expect(fetchCase).toHaveBeenLastCalledWith('dolphins')
    expect(screen.getByText(/追踪海豚之间的结伴关系/)).toBeVisible()
  })

  test('keeps the newest presentation when an older route request finishes last', async () => {
    let resolveOlder!: (value: any) => void
    vi.mocked(fetchCase)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOlder = resolve }))
      .mockResolvedValueOnce({ slug: 'dolphins', title: '海豚社交网络', summary: '新场景', module: 'communities', content: '新内容', dataset: null })
    const view = render(PresentationView, { props: { slug: 'karate' }, global })

    await view.rerender({ slug: 'dolphins' })
    expect(await screen.findByText('海豚社交网络')).toBeVisible()
    resolveOlder({ slug: 'karate', title: '过期空手道场景', summary: '旧场景', module: 'communities', content: '旧内容', dataset: null })
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(screen.getByText('海豚社交网络')).toBeVisible()
    expect(screen.queryByText('过期空手道场景')).not.toBeInTheDocument()
  })
})
