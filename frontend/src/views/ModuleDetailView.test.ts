import { render, screen } from '@testing-library/vue'
import { describe, expect, test, vi } from 'vitest'
import ModuleDetailView from './ModuleDetailView.vue'

vi.mock('../api/client', () => ({
  fetchModule: vi.fn((slug: string) => Promise.resolve({ slug, title: `模块：${slug}`, summary: `${slug} 摘要`, order: 1, content: `${slug} 内容` })),
  fetchCases: vi.fn().mockResolvedValue([]),
}))
import { fetchCases, fetchModule } from '../api/client'

describe('module detail route changes', () => {
  test('reloads content when the module route parameter changes', async () => {
    const view = render(ModuleDetailView, {
      props: { slug: 'network-basics' },
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })
    expect(await screen.findByRole('heading', { name: '模块：network-basics' })).toBeVisible()

    await view.rerender({ slug: 'communities' })

    expect(await screen.findByRole('heading', { name: '模块：communities' })).toBeVisible()
    expect(fetchModule).toHaveBeenLastCalledWith('communities')
  })

  test('keeps the newest module when an older route request finishes last', async () => {
    vi.mocked(fetchCases).mockResolvedValue([])
    let resolveOlder!: (value: any) => void
    vi.mocked(fetchModule)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOlder = resolve }))
      .mockResolvedValueOnce({ slug: 'communities', title: '模块：communities', summary: '新摘要', order: 3, content: '新内容' })
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
