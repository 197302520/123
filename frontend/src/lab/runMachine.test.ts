import { describe, expect, test, vi } from 'vitest'
import { executeRun } from './runMachine'
import { completedResult, exampleGraph } from '../test/fixtures'

const request = { algorithm: 'centrality.degree', graph: exampleGraph, parameters: {}, seed: 7 }

describe('laboratory run state machine', () => {
  test('renders immediate backend completion through observable states', async () => {
    const states: string[] = []
    const result = await executeRun(request, {
      submitRun: vi.fn().mockResolvedValue({ id: 'run-1', status: 'completed', algorithm: 'centrality.degree', seed: 7 }),
      fetchRunStatus: vi.fn(),
      fetchRunResult: vi.fn().mockResolvedValue(completedResult),
    }, (state) => states.push(state), { intervalMs: 0 })

    expect(states).toEqual(['submitting', 'completed'])
    expect(result).toEqual(completedResult)
  })

  test('polls a queued run and exposes polling before completion', async () => {
    const states: string[] = []
    const fetchRunStatus = vi.fn()
      .mockResolvedValueOnce({ id: 'run-2', status: 'pending', algorithm: 'centrality.degree', seed: 7 })
      .mockResolvedValueOnce({ id: 'run-2', status: 'completed', algorithm: 'centrality.degree', seed: 7 })

    await executeRun(request, {
      submitRun: vi.fn().mockResolvedValue({ id: 'run-2', status: 'pending', algorithm: 'centrality.degree', seed: 7 }),
      fetchRunStatus,
      fetchRunResult: vi.fn().mockResolvedValue({ ...completedResult, run_id: 'run-2' }),
    }, (state) => states.push(state), { intervalMs: 0 })

    expect(states).toEqual(['submitting', 'polling', 'completed'])
    expect(fetchRunStatus).toHaveBeenCalledTimes(2)
  })

  test('exposes a recoverable error state when the backend rejects the input', async () => {
    const states: string[] = []
    await expect(executeRun(request, {
      submitRun: vi.fn().mockRejectedValue(new Error('算法仅支持无向图。')),
      fetchRunStatus: vi.fn(),
      fetchRunResult: vi.fn(),
    }, (state) => states.push(state), { intervalMs: 0 })).rejects.toThrow('算法仅支持无向图。')

    expect(states).toEqual(['submitting', 'error'])
  })

  test('cancels polling without fetching or publishing a terminal state after abort', async () => {
    vi.useFakeTimers()
    const controller = new AbortController()
    const states: string[] = []
    const fetchRunStatus = vi.fn()
    const pending = executeRun(request, {
      submitRun: vi.fn().mockResolvedValue({ id: 'run-2', status: 'pending', algorithm: 'centrality.degree', seed: 7 }),
      fetchRunStatus,
      fetchRunResult: vi.fn(),
    }, (state) => states.push(state), { intervalMs: 1000, signal: controller.signal })

    await vi.advanceTimersByTimeAsync(0)
    controller.abort()
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' })
    await vi.advanceTimersByTimeAsync(2000)

    expect(fetchRunStatus).not.toHaveBeenCalled()
    expect(states).toEqual(['submitting', 'polling'])
    vi.useRealTimers()
  })
})
