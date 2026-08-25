import { describe, expect, test } from 'vitest'
import { chartOptions } from './chartOptions'

describe('backend chart conversion', () => {
  test('turns Floyd matrix rows into ECharts heatmap triples', () => {
    const options = chartOptions({
      key: 'distance_heatmap', type: 'heatmap',
      series: [{ name: 'distance', data: [{ node: 'a', a: 0, b: 1 }, { node: 'b', a: 1, b: 0 }] }],
    }, false) as Record<string, any>

    expect(options.animation).toBe(false)
    expect(options.xAxis.data).toEqual(['a', 'b'])
    expect(options.yAxis.data).toEqual(['a', 'b'])
    expect(options.series[0].data).toEqual([['a', 'a', 0], ['b', 'a', 1], ['a', 'b', 1], ['b', 'b', 0]])
  })

  test('maps dynamic-community events to a categorical timeline scatterplot', () => {
    const options = chartOptions({
      key: 'community_timeline', type: 'timeline',
      series: [{ name: 'events', data: [{ snapshot: 1, event: 'birth' }, { snapshot: 2, event: 'merge' }] }],
    }, true) as Record<string, any>

    expect(options.xAxis.data).toEqual(['1', '2'])
    expect(options.yAxis.data).toEqual(['birth', 'merge'])
    expect(options.series[0]).toMatchObject({ type: 'scatter', data: [['1', 'birth'], ['2', 'merge']] })
  })

  test('keeps gauge value and series name together', () => {
    const options = chartOptions({
      key: 'centralization', type: 'gauge', series: [{ name: '度中心势', data: [{ value: 0.42 }] }],
    }, true) as Record<string, any>

    expect(options.series[0]).toMatchObject({ type: 'gauge', data: [{ value: 0.42, name: '度中心势' }] })
  })
})
