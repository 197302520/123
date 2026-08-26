import { render } from '@testing-library/vue'
import { describe, expect, test, vi } from 'vitest'
import GraphCanvas from './GraphCanvas.vue'
import { exampleGraph } from '../test/fixtures'

const { cytoscapeMock } = vi.hoisted(() => ({
  cytoscapeMock: vi.fn().mockReturnValue({ destroy: vi.fn() }),
}))
vi.mock('cytoscape', () => ({ default: cytoscapeMock }))

function latestElements() {
  const options = cytoscapeMock.mock.calls[cytoscapeMock.mock.calls.length - 1][0]
  return options.elements as Array<{ data: Record<string, unknown> }>
}

async function latestEdgeStyle(edgeId: string) {
  const options = cytoscapeMock.mock.calls[cytoscapeMock.mock.calls.length - 1][0]
  const { default: actualCytoscape } = await vi.importActual('cytoscape') as unknown as { default: typeof import('cytoscape') }
  const instance = actualCytoscape({
    headless: true,
    styleEnabled: true,
    elements: options.elements,
    style: options.style,
    layout: { name: 'preset' },
  })
  const edge = instance.getElementById(edgeId)
  const style = { lineColor: edge.style('line-color'), lineStyle: edge.style('line-style') }
  instance.destroy()
  return style
}

describe('backend overlay visual encoding', () => {
  test.each([
    ['force', 'cose'],
    ['circular', 'circle'],
    ['tree', 'breadthfirst'],
  ] as const)('switches to the %s layout the manual requires', (layout, expectedName) => {
    render(GraphCanvas, { props: { graph: exampleGraph, overlay: null, layout } })

    const options = cytoscapeMock.mock.calls[cytoscapeMock.mock.calls.length - 1][0]
    expect(options.layout.name).toBe(expectedName)
  })

  test('defaults to the force-directed layout and keeps directed trees hierarchical', () => {
    render(GraphCanvas, { props: { graph: { ...exampleGraph, directed: true } } })
    expect(cytoscapeMock.mock.calls[cytoscapeMock.mock.calls.length - 1][0].layout.name).toBe('cose')

    render(GraphCanvas, { props: { graph: { ...exampleGraph, directed: true }, layout: 'tree' } })
    const treeLayout = cytoscapeMock.mock.calls[cytoscapeMock.mock.calls.length - 1][0].layout
    expect(treeLayout.name).toBe('breadthfirst')
    expect(treeLayout.directed).toBe(true)
  })

  test.each([
    ['node_values', { node: 'a', value: 0.4 }, 0.4],
    ['opinions', { node: 'a', opinion: 0.7 }, 0.7],
  ])('maps %s backend values to visible node size', (key, node, expected) => {
    render(GraphCanvas, { props: { graph: exampleGraph, overlay: { key, nodes: [node], edges: [], node_styles: {} } } })

    expect(latestElements().find((item) => item.data.id === 'a')!.data.value).toBe(expected)
  })

  test.each(['communities', 'latest_communities', 'embedding_clusters'])('maps %s community ids to distinct node colors', (key) => {
    render(GraphCanvas, { props: {
      graph: exampleGraph,
      overlay: { key, nodes: [], edges: [], node_styles: { a: { community: 0 }, b: { community: 1 } } },
    } })

    const elements = latestElements()
    expect(elements.find((item) => item.data.id === 'a')!.data.color).not.toBe(elements.find((item) => item.data.id === 'b')!.data.color)
  })

  test.each(['generated_graph', 'extracted_graph'])('keeps %s replacement edges in the normal edge style', async (key) => {
    render(GraphCanvas, { props: {
      graph: { directed: false, nodes: exampleGraph.nodes, edges: [{ source: 'a', target: 'b', weight: 1 }] },
      overlay: { key, nodes: exampleGraph.nodes.map((node) => ({ id: node.id, label: node.label })), edges: [{ source: 'a', target: 'b', weight: 1 }], node_styles: {} },
    } })

    expect(latestElements().find((item) => item.data.id === 'edge-0')!.data.predicted).toBe(0)
    expect(await latestEdgeStyle('edge-0')).toEqual({ lineColor: 'rgb(159,176,166)', lineStyle: 'solid' })
  })

  test('marks a backend predicted edge with the red dashed result style', async () => {
    render(GraphCanvas, { props: {
      graph: { ...exampleGraph, edges: [...exampleGraph.edges, { source: 'a', target: 'c', weight: 0.8 }] },
      overlay: { key: 'predicted_edges', nodes: [], edges: [{ source: 'a', target: 'c', score: 0.8 }], node_styles: {} },
    } })

    const edges = latestElements().filter((item) => String(item.data.id).startsWith('edge-'))
    expect(edges.map((item) => item.data.predicted)).toEqual([0, 0, 1])
    expect(await latestEdgeStyle('edge-2')).toEqual({ lineColor: 'rgb(217,90,58)', lineStyle: 'dashed' })
  })

  test('encodes both HITS hub and authority values in node size, color, and label', () => {
    render(GraphCanvas, { props: {
      graph: exampleGraph,
      overlay: { key: 'hits', nodes: [{ node: 'a', hub: 0.8, authority: 0.2 }, { node: 'b', hub: 0.1, authority: 0.9 }], edges: [], node_styles: {} },
    } })

    const a = latestElements().find((item) => item.data.id === 'a')!.data
    const b = latestElements().find((item) => item.data.id === 'b')!.data
    expect(a.value).toBe(0.8)
    expect(b.value).toBe(0.1)
    expect(a.color).not.toBe(b.color)
    expect(a.label).toContain('H 0.8 · A 0.2')
  })

  test('makes earlier robustness removals larger and labels their exact order', () => {
    render(GraphCanvas, { props: {
      graph: exampleGraph,
      overlay: { key: 'removal_order', nodes: [{ node: 'a', order: 1 }, { node: 'b', order: 2 }, { node: 'c', order: 3 }], edges: [], node_styles: {} },
    } })

    const nodes = latestElements().filter((item) => typeof item.data.id === 'string' && !String(item.data.id).startsWith('edge-'))
    expect(Number(nodes[0].data.value)).toBeGreaterThan(Number(nodes[1].data.value))
    expect(Number(nodes[1].data.value)).toBeGreaterThan(Number(nodes[2].data.value))
    expect(nodes[0].data.label).toContain('第 1 位移除')
    expect(nodes[2].data.label).toContain('第 3 位移除')
  })
})
