import { render, screen } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import CaseLibraryView from './CaseLibraryView.vue'
import { cases } from '../test/fixtures'

vi.mock('../api/client', () => ({ fetchCases: vi.fn(), fetchCase: vi.fn() }))
import { fetchCase, fetchCases } from '../api/client'

const RouterLinkStub = { props: ['to'], template: '<a href="#"><slot /></a>' }

describe('case library filtering', () => {
  beforeEach(() => {
    vi.mocked(fetchCases).mockResolvedValue(cases)
    // 数据集缩略图是渐进增强：详情失败时列表照常渲染。
    vi.mocked(fetchCase).mockRejectedValue(new Error('detail unavailable'))
  })

  test('combines module and keyword filters and can clear them', async () => {
    const user = userEvent.setup()
    render(CaseLibraryView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    expect(await screen.findByText('空手道俱乐部网络')).toBeVisible()

    await user.selectOptions(screen.getByLabelText('按课程模块筛选'), 'diffusion')
    expect(screen.queryByText('空手道俱乐部网络')).not.toBeInTheDocument()
    expect(screen.getByText('意见如何趋同')).toBeVisible()

    await user.type(screen.getByRole('searchbox', { name: '搜索案例' }), '不存在')
    expect(screen.getByText('没有符合条件的案例')).toBeVisible()

    await user.click(screen.getByRole('button', { name: '清除筛选' }))
    expect(screen.getByText('空手道俱乐部网络')).toBeVisible()
    expect(screen.getByText('海豚社交网络')).toBeVisible()
  })
})
