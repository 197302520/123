import type { RunRequest, RunResult, RunStatus } from '../api/contracts'

export type RunPhase = 'idle' | 'submitting' | 'polling' | 'background' | 'completed' | 'error'
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

export class RunStillActiveError extends Error {
  readonly name = 'RunStillActiveError'
  constructor(public readonly runId: string, public readonly status: 'pending' | 'running') {
    super('任务仍在后台运行。')
  }
}

interface PollOptions { intervalMs?: number; maxPolls?: number; signal?: AbortSignal }

async function pollRun(
  runId: string,
  initialStatus: RunStatus,
  api: RunApi,
  onState: (phase: RunPhase) => void,
  options: PollOptions,
): Promise<RunResult> {
  const intervalMs = options.intervalMs ?? 700
  const maxPolls = options.maxPolls ?? 120
  let status = initialStatus
  if (status.status !== 'completed') {
    onState('polling')
    for (let attempt = 0; attempt < maxPolls && ['pending', 'running'].includes(status.status); attempt += 1) {
      await delay(intervalMs, options.signal)
      status = await api.fetchRunStatus(runId, options.signal)
      ensureActive(options.signal)
    }
    if (status.status === 'pending' || status.status === 'running') {
      onState('background')
      throw new RunStillActiveError(runId, status.status)
    }
    if (status.status !== 'completed') throw new Error(
      status.status === 'failed' ? '算法运行失败，请检查输入后重试。' : '算法运行已取消。',
    )
  }
  const result = await api.fetchRunResult(runId, options.signal)
  ensureActive(options.signal)
  onState('completed')
  return result
}

export async function executeRun(
  request: RunRequest,
  api: RunApi,
  onState: (phase: RunPhase) => void,
  options: { intervalMs?: number; maxPolls?: number; signal?: AbortSignal; onSubmitted?: (status: RunStatus) => void } = {},
): Promise<RunResult> {
  onState('submitting')
  try {
    ensureActive(options.signal)
    const submission = await api.submitRun(request, options.signal)
    ensureActive(options.signal)
    options.onSubmitted?.(submission)
    return await pollRun(submission.id, submission, api, onState, options)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    if (error instanceof RunStillActiveError) throw error
    onState('error')
    throw error
  }
}

export async function resumeRun(
  runId: string,
  api: RunApi,
  onState: (phase: RunPhase) => void,
  options: PollOptions = {},
): Promise<RunResult> {
  try {
    ensureActive(options.signal)
    const status = await api.fetchRunStatus(runId, options.signal)
    ensureActive(options.signal)
    return await pollRun(runId, status, api, onState, options)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    if (error instanceof RunStillActiveError) throw error
    onState('error')
    throw error
  }
}
