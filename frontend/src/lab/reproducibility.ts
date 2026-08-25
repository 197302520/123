import type { HistoryRecord } from '../api/contracts'

export function buildReproducibilityBundle(record: HistoryRecord): Blob {
  return new Blob([JSON.stringify({
    schema: 'sna-teaching-reproducibility/v1',
    exported_at: new Date().toISOString(),
    run_id: record.id,
    created_at: record.createdAt,
    algorithm: { key: record.algorithm, name: record.algorithmName, version: record.result.provenance.version },
    parameters: record.parameters,
    seed: record.seed,
    graph: record.graph,
    result: record.result,
    provenance: record.result.provenance,
  }, null, 2)], { type: 'application/json;charset=utf-8' })
}

export function downloadReproducibilityBundle(record: HistoryRecord): void {
  const url = URL.createObjectURL(buildReproducibilityBundle(record))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `社会网络实验-${record.algorithm}-${record.id}.json`
  anchor.click()
  URL.revokeObjectURL(url)
}
