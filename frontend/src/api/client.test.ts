import { describe, expect, test, vi } from 'vitest'
import { fetchAlgorithms, validateGraph } from './client'
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
})
