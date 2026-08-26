import { describe, expect, test, vi } from 'vitest'
import { cancelRun, fetchAlgorithms, fetchReportBundle, importGraph, validateGraph } from './client'
import { degreeAlgorithm, exampleGraph } from '../test/fixtures'

describe('public API client', () => {
  test('returns the complete registry payload from the anonymous endpoint', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify([degreeAlgorithm]), { status: 200 }))

    const algorithms = await fetchAlgorithms()

    expect(algorithms).toEqual([degreeAlgorithm])
    expect(fetch).toHaveBeenCalledWith('/api/algorithms/', expect.objectContaining({ headers: { Accept: 'application/json' } }))
  })

  test('turns a structured graph validation response into an actionable Chinese error', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      valid: false,
      errors: [{ path: 'edges[0].target', message: "节点 'z' 不存在。" }],
    }), { status: 400, headers: { 'Content-Type': 'application/json' } }))

    await expect(validateGraph(exampleGraph)).rejects.toThrow("edges[0].target：节点 'z' 不存在。")
  })

  test('downloads the server-generated multi-format report bundle', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('PK report', {
      status: 200,
      headers: { 'Content-Type': 'application/zip' },
    }))

    const bundle = await fetchReportBundle('run/unsafe')

    expect(fetch).toHaveBeenCalledWith('/api/reports/run%2Funsafe/bundle/', expect.objectContaining({
      headers: { Accept: 'application/zip' },
    }))
    expect(bundle.type).toBe('application/zip')
    const text = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result))
      reader.onerror = () => reject(reader.error)
      reader.readAsText(bundle)
    })
    expect(text).toBe('PK report')
  })

  test('uploads graph files as multipart without forcing a JSON content type', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      valid: true, errors: [], graph: exampleGraph,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    const file = new File(['source,target\na,b'], 'network.xlsx')

    await importGraph(file)

    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(init?.body).toBeInstanceOf(FormData)
    expect(new Headers(init?.headers).has('Content-Type')).toBe(false)
  })

  test('calls the public idempotent cancellation endpoint', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      id: 'run-1', status: 'cancelled', algorithm: 'centrality.degree', seed: 7,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    await cancelRun('run/unsafe')

    expect(fetch).toHaveBeenCalledWith('/api/runs/run%2Funsafe/cancel/', expect.objectContaining({ method: 'POST' }))
  })
})
