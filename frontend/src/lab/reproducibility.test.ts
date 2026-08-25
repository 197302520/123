import { describe, expect, test } from 'vitest'
import { buildReproducibilityBundle } from './reproducibility'
import { historyRecord } from '../test/fixtures'

describe('reproducibility bundle', () => {
  test('preserves the full input and backend provenance needed to repeat a run', async () => {
    const blob = buildReproducibilityBundle(historyRecord)
    const text = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result))
      reader.onerror = () => reject(reader.error)
      reader.readAsText(blob)
    })
    const bundle = JSON.parse(text)

    expect(bundle).toMatchObject({
      schema: 'sna-teaching-reproducibility/v1',
      algorithm: { key: 'centrality.degree', name: '度中心性', version: '1.0' },
      parameters: { normalized: true },
      seed: 7,
      result: { run_id: 'run-1', status: 'completed' },
      provenance: { graph_hash: 'graph-hash', parameter_hash: 'parameter-hash' },
    })
    expect(bundle.graph).toEqual(historyRecord.graph)
  })
})
