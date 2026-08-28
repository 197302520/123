import type {
  AlgorithmSpec, CaseDetail, CaseSummary, CourseModule, CourseModuleDetail,
  GraphInputSpec, GraphValidation, RunRequest, RunResult, RunStatus,
} from './contracts'

interface ErrorPayload {
  detail?: string
  error?: { message?: string; path?: string }
  errors?: Array<{ path: string; message: string }>
}

// 教师在同一浏览器登录后台后，DRF SessionAuthentication 会对 POST 强制 CSRF 校验。
function csrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : ''
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const response = await fetch(path, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      ...(method !== 'GET' && method !== 'HEAD' && csrfToken() ? { 'X-CSRFToken': csrfToken() } : {}),
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

async function requestBlob(path: string, init: RequestInit = {}): Promise<Blob> {
  const response = await fetch(path, {
    ...init,
    headers: { Accept: 'application/zip', ...init.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as ErrorPayload
    throw new Error(payload.detail || `报告下载失败（${response.status}）。`)
  }
  return response.blob()
}

export const fetchModules = () => requestJson<CourseModule[]>('/api/modules/')
export const fetchModule = (slug: string) => requestJson<CourseModuleDetail>(`/api/modules/${encodeURIComponent(slug)}/`)
export const fetchCases = () => requestJson<CaseSummary[]>('/api/cases/')
export const fetchCase = (slug: string) => requestJson<CaseDetail>(`/api/cases/${encodeURIComponent(slug)}/`)
export const fetchAlgorithms = () => requestJson<AlgorithmSpec[]>('/api/algorithms/')
export const validateGraph = (graph: GraphInputSpec, signal?: AbortSignal) => requestJson<GraphValidation>('/api/graphs/validate/', {
  method: 'POST', body: JSON.stringify(graph), signal,
})
export const importGraph = (file: File, signal?: AbortSignal) => {
  const body = new FormData()
  body.append('file', file)
  return requestJson<GraphValidation>('/api/graphs/import/', { method: 'POST', body, signal })
}
export const submitRun = (request: RunRequest, signal?: AbortSignal) => requestJson<RunStatus>('/api/runs/', {
  method: 'POST', body: JSON.stringify(request), signal,
})
export const fetchRunStatus = (id: string, signal?: AbortSignal) => requestJson<RunStatus>(`/api/runs/${encodeURIComponent(id)}/`, { signal })
export const fetchRunResult = (id: string, signal?: AbortSignal) => requestJson<RunResult>(`/api/runs/${encodeURIComponent(id)}/result/`, { signal })
export const cancelRun = (id: string) => requestJson<RunStatus>(`/api/runs/${encodeURIComponent(id)}/cancel/`, { method: 'POST', body: JSON.stringify({}) })
export const fetchReportBundle = (id: string, signal?: AbortSignal) => requestBlob(`/api/reports/${encodeURIComponent(id)}/bundle/`, { signal })
