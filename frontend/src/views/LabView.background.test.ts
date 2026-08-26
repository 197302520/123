import { render, screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import LabView from './LabView.vue'
import { completedResult, degreeAlgorithm, exampleGraph } from '../test/fixtures'

vi.mock('../api/client', () => ({
  fetchAlgorithms: vi.fn(), fetchCase: vi.fn(), fetchReportBundle: vi.fn(), cancelRun: vi.fn(),
  validateGraph: vi.fn(), submitRun: vi.fn(), fetchRunStatus: vi.fn(), fetchRunResult: vi.fn(),
}))
vi.mock('../lab/historyStore', () => ({
  listHistory: vi.fn(), saveHistory: vi.fn(), deleteHistory: vi.fn(), clearHistory: vi.fn(),
}))
vi.mock('../lab/runMachine', () => ({
  executeRun: vi.fn(), resumeRun: vi.fn(),
  RunStillActiveError: class RunStillActiveError extends Error {
    name = 'RunStillActiveError'
    constructor(public runId: string, public status: string) { super('任务仍在后台运行。') }
  },
}))

import {
  cancelRun, fetchAlgorithms, fetchRunResult, fetchRunStatus, submitRun, validateGraph,
} from '../api/client'
import { listHistory, saveHistory } from '../lab/historyStore'
import { executeRun, resumeRun } from '../lab/runMachine'

const global = { stubs: {
  GraphCanvas: true,
  ResultChart: true,
  FormulaBlock: { template: '<div />' },
  RouterLink: { template: '<a><slot /></a>' },
} }

function retainedBackgroundRun() {
  vi.mocked(executeRun).mockImplementation(async (_request, _api, onState, options) => {
    onState('submitting')
    options?.onSubmitted?.({ id: 'run-background', status: 'pending', algorithm: 'centrality.degree', seed: 7 })
    onState('background')
    throw Object.assign(new Error('任务仍在后台运行。'), {
      name: 'RunStillActiveError', runId: 'run-background', status: 'running',
    })
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  window.history.replaceState({}, '', '/lab')
  vi.mocked(fetchAlgorithms).mockResolvedValue([degreeAlgorithm])
  vi.mocked(validateGraph).mockResolvedValue({ valid: true, errors: [], graph: exampleGraph })
  vi.mocked(listHistory).mockResolvedValue([])
  vi.mocked(saveHistory).mockResolvedValue(undefined)
  vi.mocked(cancelRun).mockResolvedValue({
    id: 'run-background', status: 'cancelled', algorithm: 'centrality.degree', seed: 7,
  })
})

describe('long-running laboratory jobs', () => {
  test('timeout retains the run capability and explicit resume reaches completion', async () => {
    retainedBackgroundRun()
    vi.mocked(resumeRun).mockImplementation(async (_id, _api, onState) => {
      onState('polling')
      onState('completed')
      return { ...completedResult, run_id: 'run-background' }
    })
    const user = userEvent.setup()
    render(LabView, { global })
    await screen.findByRole('option', { name: '度中心性' })
    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    await user.click(screen.getByRole('button', { name: '运行真实算法' }))

    expect(await screen.findByText('任务仍在后台运行，可继续查询状态或取消任务。')).toBeVisible()
    expect(screen.getByRole('button', { name: '继续查询状态' })).toBeEnabled()
    expect(screen.getByRole('button', { name: '取消后台任务' })).toBeEnabled()

    await user.click(screen.getByRole('button', { name: '继续查询状态' }))

    expect(await screen.findByRole('heading', { name: '分析结果' }, { timeout: 5_000 })).toBeVisible()
    expect(resumeRun).toHaveBeenCalledWith(
      'run-background', { submitRun, fetchRunStatus, fetchRunResult }, expect.any(Function), expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(cancelRun).not.toHaveBeenCalled()
  })

  test('timeout exposes an explicit cancellation that clears only after the server accepts it', async () => {
    retainedBackgroundRun()
    const user = userEvent.setup()
    render(LabView, { global })
    await screen.findByRole('option', { name: '度中心性' })
    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    await user.click(screen.getByRole('button', { name: '运行真实算法' }))
    await screen.findByText('任务仍在后台运行，可继续查询状态或取消任务。')

    await user.click(screen.getByRole('button', { name: '取消后台任务' }))

    await waitFor(() => expect(cancelRun).toHaveBeenCalledWith('run-background'))
    expect(await screen.findByRole('status', { name: '取消状态' })).toHaveTextContent('已取消任务 run-background')
    expect(screen.queryByRole('button', { name: '继续查询状态' })).not.toBeInTheDocument()
  })
})
