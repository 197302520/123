import type { RunRequest, RunResult, RunStatus } from '../api/contracts'

export type RunPhase = 'idle' | 'submitting' | 'polling' | 'completed' | 'error'
export interface RunApi {
  submitRun(request: RunRequest, signal?: AbortSignal): Promise<RunStatus>
  fetchRunStatus(id: string, signal?: AbortSignal): Promise<RunStatus>
  fetchRunResult(id: string, signal?: AbortSignal): Promise<RunResult>
}

function aborted(): DOMException { return new DOMException('运行已取消。', 'AbortError') }
function ensureActive(signal?: AbortSignal) { if (signal?.aborted) throw aborted() }
function delay(milliseconds: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    ensureActive(signal)
    const timer = window.setTimeout(() => { signal?.removeEventListener('abort', cancel); resolve() }, milliseconds)
    const cancel = () => { window.clearTimeout(timer); reject(aborted()) }
    signal?.addEventListener('abort', cancel, { once: true })
  })
}

export async function executeRun(
  request: RunRequest,
  api: RunApi,
  onState: (phase: RunPhase) => void,
  options: { intervalMs?: number; maxPolls?: number; signal?: AbortSignal } = {},
): Promise<RunResult> {
  const intervalMs = options.intervalMs ?? 700
  const maxPolls = options.maxPolls ?? 120
  onState('submitting')
  try {
    ensureActive(options.signal)
    const submission = await api.submitRun(request, options.signal)
    ensureActive(options.signal)
    if (submission.status !== 'completed') {
      onState('polling')
      let status = submission
      for (let attempt = 0; attempt < maxPolls && status.status === 'pending'; attempt += 1) {
        await delay(intervalMs, options.signal)
        status = await api.fetchRunStatus(submission.id, options.signal)
        ensureActive(options.signal)
      }
      if (status.status !== 'completed') throw new Error(status.status === 'failed' ? '算法运行失败，请检查输入后重试。' : '等待结果超时，请稍后重试。')
    }
    const result = await api.fetchRunResult(submission.id, options.signal)
    ensureActive(options.signal)
    onState('completed')
    return result
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    onState('error')
    throw error
  }
}
