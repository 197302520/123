import { beforeEach, describe, expect, test, vi } from 'vitest'
import { clearHistory, deleteHistory, listHistory, saveHistory } from './historyStore'
import { historyRecord } from '../test/fixtures'

describe('anonymous IndexedDB history', () => {
  beforeEach(async () => clearHistory())

  test('stores no identity and lists experiments newest first', async () => {
    await saveHistory({ ...historyRecord, id: 'older', createdAt: '2026-08-24T08:00:00.000Z' })
    await saveHistory({ ...historyRecord, id: 'newer', createdAt: '2026-08-25T08:00:00.000Z' })

    const rows = await listHistory()

    expect(rows.map((row) => row.id)).toEqual(['newer', 'older'])
    expect(Object.keys(rows[0])).not.toContain('userId')
  })

  test('deletes one run and clears the remaining local history', async () => {
    await saveHistory(historyRecord)
    await saveHistory({ ...historyRecord, id: 'run-2' })
    await deleteHistory('run-1')
    expect((await listHistory()).map((row) => row.id)).toEqual(['run-2'])

    await clearHistory()
    expect(await listHistory()).toEqual([])
  })

  test('closes the IndexedDB connection when a write request fails', async () => {
    const close = vi.spyOn(IDBDatabase.prototype, 'close')
    const invalid = { ...historyRecord, parameters: { cannotClone: () => 'function' } } as never

    await expect(saveHistory(invalid)).rejects.toBeDefined()

    expect(close).toHaveBeenCalledTimes(1)
  })
})
