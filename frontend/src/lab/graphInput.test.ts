import { describe, expect, test } from 'vitest'
import { GraphInputError, parseGraphText, validateGraphLocally } from './graphInput'

describe('graph input', () => {
  test('parses a whitespace edge list into a normalized undirected graph', () => {
    expect(parseGraphText('甲 乙 2\n乙 丙')).toEqual({
      directed: false,
      nodes: [{ id: '甲', label: '甲' }, { id: '乙', label: '乙' }, { id: '丙', label: '丙' }],
      edges: [{ source: '甲', target: '乙', weight: 2 }, { source: '乙', target: '丙', weight: 1 }],
    })
  })

  test('reports malformed JSON instead of silently converting it to an edge list', () => {
    expect(() => parseGraphText('{"nodes": [}')).toThrow(GraphInputError)
    expect(() => parseGraphText('{"nodes": [}')).toThrow('JSON 格式不完整')
  })

  test('returns precise duplicate, missing-endpoint, and invalid-weight issues', () => {
    expect(validateGraphLocally({
      directed: false,
      nodes: [{ id: 'a' }, { id: 'a' }],
      edges: [{ source: 'a', target: 'z', weight: 0 }],
    })).toEqual([
      { path: 'nodes[1].id', message: "节点 'a' 重复。" },
      { path: 'edges[0].target', message: "节点 'z' 不存在。" },
      { path: 'edges[0].weight', message: '边权重必须是大于 0 的有限数值。' },
    ])
  })
})
