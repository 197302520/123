import { render, screen } from '@testing-library/vue'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import CourseLibraryView from './CourseLibraryView.vue'
import HomeView from './HomeView.vue'

vi.mock('../api/client', () => ({ fetchModules: vi.fn(), fetchCases: vi.fn() }))
import { fetchCases, fetchModules } from '../api/client'

const global = { stubs: { RouterLink: { template: '<a><slot /></a>' } } }

beforeEach(() => {
  vi.mocked(fetchModules).mockResolvedValue([])
  vi.mocked(fetchCases).mockResolvedValue([])
})

describe('successful empty catalog states', () => {
  test('home distinguishes empty modules and cases from loading', async () => {
    render(HomeView, { global })

    expect(await screen.findByText('课程目录暂未发布，可先进入自由实验室练习。')).toBeVisible()
    expect(screen.getByText('案例索引暂未发布，可从课程模块了解分析方法。')).toBeVisible()
    expect(screen.queryByText(/正在装订|正在整理/)).not.toBeInTheDocument()
  })

  test('course library explains what to do when no modules are published', async () => {
    render(CourseLibraryView, { global })

    expect(await screen.findByText('课程模块暂未发布，请稍后再来，或先进入自由实验室。')).toBeVisible()
  })
})
