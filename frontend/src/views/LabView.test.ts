import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import LabView from './LabView.vue'
import { completedResult, degreeAlgorithm, exampleGraph, historyRecord } from '../test/fixtures'

vi.mock('../api/client', () => ({
  fetchAlgorithms: vi.fn(),
  fetchCase: vi.fn(),
  fetchReportBundle: vi.fn(),
  validateGraph: vi.fn(),
  submitRun: vi.fn(),
  fetchRunStatus: vi.fn(),
  fetchRunResult: vi.fn(),
}))
vi.mock('../lab/historyStore', () => ({
  listHistory: vi.fn(),
  saveHistory: vi.fn(),
  deleteHistory: vi.fn(),
  clearHistory: vi.fn(),
}))
import { fetchAlgorithms, fetchCase, fetchReportBundle, fetchRunResult, submitRun, validateGraph } from '../api/client'
import { clearHistory, deleteHistory, listHistory, saveHistory } from '../lab/historyStore'

const global = { stubs: {
  GraphCanvas: true,
  ResultChart: true,
  FormulaBlock: { template: '<div />' },
  RouterLink: { template: '<a><slot /></a>' },
} }

function renderLab() { return render(LabView, { global }) }

beforeEach(() => {
  vi.clearAllMocks()
  window.history.replaceState({}, '', '/lab')
  vi.mocked(fetchAlgorithms).mockResolvedValue([degreeAlgorithm])
  vi.mocked(fetchCase).mockResolvedValue({
    slug: 'zachary-karate', title: '空手道俱乐部', summary: '案例', module: 'communities', content: '',
    dataset: { slug: 'zachary-karate', title: 'Zachary', provenance: 'source', metadata: {
      graph: exampleGraph, algorithm: 'centrality.degree', parameters: { normalized: true }, seed: 19,
    } },
  })
  vi.mocked(fetchReportBundle).mockResolvedValue(new Blob(['zip'], { type: 'application/zip' }))
  vi.mocked(validateGraph).mockResolvedValue({ valid: true, errors: [], graph: exampleGraph })
  vi.mocked(listHistory).mockResolvedValue([])
  vi.mocked(saveHistory).mockResolvedValue(undefined)
  vi.mocked(deleteHistory).mockResolvedValue(undefined)
  vi.mocked(clearHistory).mockResolvedValue(undefined)
  vi.mocked(fetchRunResult).mockResolvedValue(completedResult)
})

describe('free laboratory workflow', () => {
  test('loads a runnable case graph, algorithm, parameters, and seed from the public case endpoint', async () => {
    window.history.pushState({}, '', '/lab?case=zachary-karate')
    renderLab()

    expect(await screen.findByText(/已载入案例“空手道俱乐部”/)).toBeVisible()
    expect(fetchCase).toHaveBeenCalledWith('zachary-karate')
    expect(screen.getByRole('spinbutton', { name: '随机种子' })).toHaveValue(19)
    expect((screen.getByRole('textbox', { name: '粘贴图数据' }) as HTMLTextAreaElement).value).toContain('"id": "a"')
  })

  test('invalidates readiness immediately after editing a validated graph and will not submit it', async () => {
    const user = userEvent.setup()
    renderLab()
    expect(await screen.findByRole('option', { name: '度中心性' })).toBeVisible()

    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    expect(screen.getByRole('button', { name: '运行真实算法' })).toBeEnabled()
    await fireEvent.update(screen.getByRole('textbox', { name: '粘贴图数据' }), 'a b')

    expect(screen.getByRole('button', { name: '运行真实算法' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: '运行真实算法' }))
    expect(submitRun).not.toHaveBeenCalled()
  })

  test('uses one immutable configuration snapshot for request and saved history during a pending run', async () => {
    const user = userEvent.setup()
    let finishSubmission!: (value: { id: string; status: string; algorithm: string; seed: number }) => void
    vi.mocked(submitRun).mockImplementation(() => new Promise((resolve) => { finishSubmission = resolve }))
    renderLab()

    expect(await screen.findByRole('option', { name: '度中心性' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    await user.click(screen.getByRole('button', { name: '运行真实算法' }))
    expect(submitRun).toHaveBeenCalledWith(expect.objectContaining({ parameters: expect.objectContaining({ iterations: 3 }), seed: 7 }), expect.any(AbortSignal))

    await fireEvent.update(screen.getByRole('spinbutton', { name: /迭代次数/ }), '11')
    await fireEvent.update(screen.getByRole('spinbutton', { name: '随机种子' }), '99')
    finishSubmission({ id: 'run-1', status: 'completed', algorithm: 'centrality.degree', seed: 7 })

    expect(await screen.findByRole('heading', { name: '分析结果' }, { timeout: 5_000 })).toBeVisible()
    await waitFor(() => expect(saveHistory).toHaveBeenCalledWith(expect.objectContaining({
      algorithm: 'centrality.degree', parameters: expect.objectContaining({ iterations: 3 }), seed: 7, graph: exampleGraph,
    })))
  })

  test('keeps a completed result while surfacing a local save failure separately', async () => {
    vi.mocked(submitRun).mockResolvedValue({ id: 'run-1', status: 'completed', algorithm: 'centrality.degree', seed: 7 })
    vi.mocked(saveHistory).mockRejectedValue(new Error('浏览器配额不足'))
    const user = userEvent.setup()
    renderLab()

    await screen.findByRole('option', { name: '度中心性' })
    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    await user.click(screen.getByRole('button', { name: '运行真实算法' }))

    expect(await screen.findByRole('heading', { name: '分析结果' }, { timeout: 5_000 })).toBeVisible()
    expect(await screen.findByRole('alert', { name: '本机历史错误' })).toHaveTextContent('浏览器配额不足')
    expect(screen.getByText('计算完成，可以查看结果与复现信息。')).toBeVisible()
  })

  test('downloads the completed backend report bundle instead of rebuilding a JSON-only file', async () => {
    vi.mocked(submitRun).mockResolvedValue({ id: 'run-1', status: 'completed', algorithm: 'centrality.degree', seed: 7 })
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:report')
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    renderLab()
    const user = userEvent.setup()
    await screen.findByRole('option', { name: '度中心性' })
    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    await user.click(screen.getByRole('button', { name: '运行真实算法' }))
    await user.click(await screen.findByRole('button', { name: '下载本次复现包' }))

    expect(fetchReportBundle).toHaveBeenCalledWith('run-1')
    expect(createObjectURL).toHaveBeenCalledWith(expect.objectContaining({ type: 'application/zip' }))
    expect(click).toHaveBeenCalled()
  })

  test('surfaces load, delete, and clear failures without removing visible records', async () => {
    vi.mocked(listHistory).mockRejectedValueOnce(new Error('读取失败')).mockResolvedValueOnce([historyRecord])
    const first = renderLab()
    expect(await screen.findByRole('alert', { name: '本机历史错误' })).toHaveTextContent('读取失败')
    first.unmount()

    vi.mocked(deleteHistory).mockRejectedValue(new Error('删除失败'))
    vi.mocked(clearHistory).mockRejectedValue(new Error('清空失败'))
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderLab()
    await userEvent.setup().click(await screen.findByRole('button', { name: '删除' }))
    expect(await screen.findByRole('alert', { name: '本机历史错误' })).toHaveTextContent('删除失败')
    expect(screen.getByText('run-1')).toBeVisible()
    await userEvent.setup().click(screen.getByRole('button', { name: '清空历史' }))
    expect(await screen.findByRole('alert', { name: '本机历史错误' })).toHaveTextContent('清空失败')
    expect(screen.getByText('run-1')).toBeVisible()
  })

  test('shows the next step when the registry succeeds with no algorithms', async () => {
    vi.mocked(fetchAlgorithms).mockResolvedValue([])
    renderLab()

    expect(await screen.findByText('算法注册表当前为空，请联系课程教师配置算法后再运行。')).toBeVisible()
    expect(screen.getByRole('combobox', { name: '算法' })).toHaveDisplayValue('暂无可用算法')
    expect(screen.getByRole('button', { name: '运行真实算法' })).toBeDisabled()
  })

  test('blocks submission while a structured parameter contains invalid JSON', async () => {
    vi.mocked(fetchAlgorithms).mockResolvedValue([{
      ...degreeAlgorithm,
      parameters: { weights: { type: 'array', default: [1, 2], description: '权重序列。' } },
    }])
    const user = userEvent.setup()
    renderLab()
    await screen.findByRole('option', { name: '度中心性' })
    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    const field = screen.getByRole('textbox', { name: /权重序列/ })
    await fireEvent.update(field, '[1,')

    expect(screen.getByRole('alert')).toHaveTextContent('weights 必须是有效的 JSON 数组。')
    expect(screen.getByRole('button', { name: '运行真实算法' })).toBeDisabled()
    expect(submitRun).not.toHaveBeenCalled()
  })

  test('whole reset clears structured parameter errors and synchronizes run validity', async () => {
    vi.mocked(fetchAlgorithms).mockResolvedValue([{
      ...degreeAlgorithm,
      parameters: { weights: { type: 'array', default: [1, 2], description: '权重序列。' } },
    }])
    const user = userEvent.setup()
    renderLab()
    await screen.findByRole('option', { name: '度中心性' })
    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    await fireEvent.update(screen.getByRole('textbox', { name: /权重序列/ }), '[1,')
    expect(screen.getByRole('button', { name: '运行真实算法' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: '重置整个实验' }))

    expect(screen.queryByText('weights 必须是有效的 JSON 数组。')).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /权重序列/ })).toHaveValue('[\n  1,\n  2\n]')
    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    expect(screen.getByRole('button', { name: '运行真实算法' })).toBeEnabled()
  })

  test('aborts an in-flight submission on unmount and never saves a late result', async () => {
    let capturedSignal: AbortSignal | undefined
    vi.mocked(submitRun).mockImplementation((_request, signal) => {
      capturedSignal = signal
      return new Promise((_resolve, reject) => signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))))
    })
    const user = userEvent.setup()
    const view = renderLab()
    await screen.findByRole('option', { name: '度中心性' })
    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    await user.click(screen.getByRole('button', { name: '运行真实算法' }))

    view.unmount()
    await Promise.resolve()

    expect(capturedSignal?.aborted).toBe(true)
    expect(saveHistory).not.toHaveBeenCalled()
  })

  test('reset cancels a pending run and restores the learning example and registry defaults', async () => {
    let capturedSignal: AbortSignal | undefined
    vi.mocked(submitRun).mockImplementation((_request, signal) => {
      capturedSignal = signal
      return new Promise((_resolve, reject) => signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))))
    })
    const user = userEvent.setup()
    renderLab()
    await screen.findByRole('option', { name: '度中心性' })
    await user.click(screen.getByRole('button', { name: '校验图数据' }))
    await user.click(screen.getByRole('button', { name: '运行真实算法' }))

    await user.click(screen.getByRole('button', { name: '重置整个实验' }))

    expect(capturedSignal?.aborted).toBe(true)
    expect(screen.getByRole('spinbutton', { name: /迭代次数/ })).toHaveValue(3)
    expect((screen.getByRole('textbox', { name: '粘贴图数据' }) as HTMLTextAreaElement).value).toContain('教学示例')
    expect(screen.getByRole('button', { name: '运行真实算法' })).toBeDisabled()
    expect(saveHistory).not.toHaveBeenCalled()
  })
})
