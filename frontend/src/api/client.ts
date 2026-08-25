import type {
  AlgorithmSpec, CaseDetail, CaseSummary, CourseModule, CourseModuleDetail,
  GraphInputSpec, GraphValidation, RunRequest, RunResult, RunStatus,
} from './contracts'

interface ErrorPayload {
  detail?: string
  error?: { message?: string; path?: string }
  errors?: Array<{ path: string; message: string }>
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  })
  const payload = await response.json().catch(() => ({})) as T & ErrorPayload
  if (!response.ok) {
    const validationMessage = payload.errors?.map((issue) => `${issue.path || '图数据'}：${issue.message}`).join('；')
    const algorithmMessage = payload.error?.message
      ? `${payload.error.path ? `${payload.error.path}：` : ''}${payload.error.message}`
      : ''
    throw new Error(validationMessage || algorithmMessage || payload.detail || `请求失败（${response.status}）。`)
  }
  return payload
}

export const fetchModules = () => requestJson<CourseModule[]>('/api/modules/')
export const fetchModule = (slug: string) => requestJson<CourseModuleDetail>(`/api/modules/${encodeURIComponent(slug)}/`)
export const fetchCases = () => requestJson<CaseSummary[]>('/api/cases/')
export const fetchCase = (slug: string) => requestJson<CaseDetail>(`/api/cases/${encodeURIComponent(slug)}/`)
export const fetchAlgorithms = () => requestJson<AlgorithmSpec[]>('/api/algorithms/')
export const validateGraph = (graph: GraphInputSpec) => requestJson<GraphValidation>('/api/graphs/validate/', {
  method: 'POST', body: JSON.stringify(graph),
})
export const submitRun = (request: RunRequest) => requestJson<RunStatus>('/api/runs/', {
  method: 'POST', body: JSON.stringify(request),
})
export const fetchRunStatus = (id: string) => requestJson<RunStatus>(`/api/runs/${encodeURIComponent(id)}/`)
export const fetchRunResult = (id: string) => requestJson<RunResult>(`/api/runs/${encodeURIComponent(id)}/result/`)
