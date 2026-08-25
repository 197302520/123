import type { AlgorithmSpec } from '../api/contracts'

export function defaultsFor(algorithm: AlgorithmSpec): Record<string, unknown> {
  return Object.fromEntries(Object.entries(algorithm.parameters).map(([key, definition]) => [key, JSON.parse(JSON.stringify(definition.default)) as unknown]))
}
