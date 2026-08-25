import type { RunRequest, RunResult, RunStatus } from '../api/contracts'

export type RunPhase = 'idle' | 'submitting' | 'polling' | 'completed' | 'error'
export interface RunApi {
  submitRun(request: RunRequest): Promise<RunStatus>
  fetchRunStatus(id: string): Promise<RunStatus>
  fetchRunResult(id: string): Promise<RunResult>
}

const delay = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds))

export async function executeRun(
  request: RunRequest,
  api: RunApi,
  onState: (phase: RunPhase) => void,
  options: { intervalMs?: number; maxPolls?: number } = {},
): Promise<RunResult> {
  const intervalMs = options.intervalMs ?? 700
  const maxPolls = options.maxPolls ?? 120
  onState('submitting')
  try {
    const submission = await api.submitRun(request)
    if (submission.status !== 'completed') {
      onState('polling')
      let status = submission
      for (let attempt = 0; attempt < maxPolls && status.status === 'pending'; attempt += 1) {
        await delay(intervalMs)
        status = await api.fetchRunStatus(submission.id)
      }
      if (status.status !== 'completed') throw new Error(status.status === 'failed' ? '算法运行失败，请检查输入后重试。' : '等待结果超时，请稍后重试。')
    }
    const result = await api.fetchRunResult(submission.id)
    onState('completed')
    return result
  } catch (error) {
    onState('error')
    throw error
  }
}
