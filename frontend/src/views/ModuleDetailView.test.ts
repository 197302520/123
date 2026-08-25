import { render, screen } from '@testing-library/vue'
import { describe, expect, test, vi } from 'vitest'
import ModuleDetailView from './ModuleDetailView.vue'

vi.mock('../api/client', () => ({
  fetchModule: vi.fn((slug: string) => Promise.resolve({ slug, title: `模块：${slug}`, summary: `${slug} 摘要`, order: 1, content: `${slug} 内容` })),
  fetchCases: vi.fn().mockResolvedValue([]),
}))
import { fetchModule } from '../api/client'

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
})
