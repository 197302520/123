import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import LabView from './LabView.vue'
import { completedResult, degreeAlgorithm, exampleGraph } from '../test/fixtures'

vi.mock('../api/client', () => ({
  fetchAlgorithms: vi.fn(),
  validateGraph: vi.fn(),
  submitRun: vi.fn(),
  fetchRunStatus: vi.fn(),
  fetchRunResult: vi.fn(),
}))
vi.mock('../lab/historyStore', () => ({
  listHistory: vi.fn().mockResolvedValue([]),
  saveHistory: vi.fn().mockResolvedValue(undefined),
  deleteHistory: vi.fn(),
  clearHistory: vi.fn(),
}))
import { fetchAlgorithms, fetchRunResult, submitRun, validateGraph } from '../api/client'
import { saveHistory } from '../lab/historyStore'

describe('free laboratory workflow', () => {
  test('prevents duplicate submission, saves completion locally, and resets inputs', async () => {
    const user = userEvent.setup()
    let finishSubmission!: (value: { id: string; status: string; algorithm: string; seed: number }) => void
    vi.mocked(fetchAlgorithms).mockResolvedValue([degreeAlgorithm])
    vi.mocked(validateGraph).mockResolvedValue({ valid: true, errors: [], graph: exampleGraph })
    vi.mocked(submitRun).mockImplementation(() => new Promise((resolve) => { finishSubmission = resolve }))
    vi.mocked(fetchRunResult).mockResolvedValue(completedResult)

    render(LabView, { global: { stubs: {
      GraphCanvas: true,
      ResultChart: true,
      FormulaBlock: { template: '<div />' },
      RouterLink: { template: '<a><slot /></a>' },
    } } })

    expect(await screen.findByRole('option', { name: '度中心性' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    await user.click(screen.getByRole('button', { name: '运行真实算法' }))
    expect(screen.getByRole('button', { name: '正在提交…' })).toBeDisabled()
    expect(submitRun).toHaveBeenCalledTimes(1)

    finishSubmission({ id: 'run-1', status: 'completed', algorithm: 'centrality.degree', seed: 7 })
    expect(await screen.findByRole('heading', { name: '分析结果' }, { timeout: 5_000 })).toBeVisible()
    await waitFor(() => expect(saveHistory).toHaveBeenCalledTimes(1))

    const iterations = screen.getByRole('spinbutton', { name: /迭代次数/ })
    await user.clear(iterations)
    await user.type(iterations, '11')
    await fireEvent.update(screen.getByRole('textbox', { name: '粘贴图数据' }), 'x y')
    await user.click(screen.getByRole('button', { name: '重置整个实验' }))
    expect(iterations).toHaveValue(3)
    expect((screen.getByRole('textbox', { name: '粘贴图数据' }) as HTMLTextAreaElement).value).toContain('教学示例')
  })
})
