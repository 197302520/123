import { describe, expect, test } from 'vitest'
import { chartOptions } from './chartOptions'

describe('backend chart conversion', () => {
  test('turns backend Floyd long-form rows into ECharts heatmap triples', () => {
    const options = chartOptions({
      key: 'distance_heatmap', type: 'heatmap',
      series: [{ name: 'distance', data: [
        { source: 'a', target: 'a', distance: 0 },
        { source: 'a', target: 'b', distance: 1 },
        { source: 'b', target: 'a', distance: 1 },
        { source: 'b', target: 'b', distance: 0 },
      ] }],
    }, false) as Record<string, any>

    expect(options.animation).toBe(false)
    expect(options.xAxis.data).toEqual(['a', 'b'])
    expect(options.yAxis.data).toEqual(['a', 'b'])
    expect(options.series[0].data).toEqual([['a', 'a', 0], ['b', 'a', 1], ['a', 'b', 1], ['b', 'b', 0]])
  })

  test('keeps Floyd zero distance but renders null distance as unreachable', () => {
    const options = chartOptions({
      key: 'distance_heatmap', type: 'heatmap',
      series: [{ name: 'distance', data: [
        { source: 'a', target: 'a', distance: 0 },
        { source: 'a', target: 'b', distance: 2 },
        { source: 'a', target: 'c', distance: null },
      ] }],
    }, false) as Record<string, any>

    expect(options.series[0].data).toEqual([
      ['a', 'a', 0],
      ['b', 'a', 2],
      ['c', 'a', null],
    ])
    expect(options.tooltip.formatter({ value: ['c', 'a', null] })).toContain('不可达')
    expect(options.tooltip.formatter({ value: ['a', 'a', 0] })).toContain('0')
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

  test('labels every scatter point with its node and explains both axes on hover', () => {
    const options = chartOptions({
      key: 'hits_scatter', type: 'scatter',
      x_axis: '枢纽分 hub', y_axis: '权威分 authority',
      series: [{ name: 'HITS', data: [
        { x: 0.0517, y: 0.84050003, label: 'ENG' },
        { x: 0.2, y: 0.1, label: 'ARG' },
      ] }],
    }, false) as Record<string, any>

    expect(options.series[0].data).toEqual([
      { name: 'ENG', value: [0.0517, 0.84050003] },
      { name: 'ARG', value: [0.2, 0.1] },
    ])
    expect(options.tooltip.trigger).toBe('item')
    expect(options.xAxis.name).toBe('枢纽分 hub')
    expect(options.yAxis.name).toBe('权威分 authority')
    const tooltip = options.tooltip.formatter({ name: 'ENG', value: [0.0517, 0.84050003] })
    expect(tooltip).toContain('ENG')
    expect(tooltip).toContain('枢纽分 hub：0.0517')
    expect(tooltip).toContain('权威分 authority：0.8405')
    expect(options.tooltip.formatter({ name: 'X', value: [0.1, null] })).toContain('—')
  })

  test('rotates crowded bar categories and formats tooltip values readably', () => {
    const many = Array.from({ length: 14 }, (_, index) => ({ x: `n${index}`, y: 0.12345678 }))
    const crowded = chartOptions({ key: 'ranking', type: 'bar', series: [{ name: '度中心性', data: many }] }, true) as Record<string, any>
    expect(crowded.xAxis.axisLabel.rotate).toBe(45)
    expect(crowded.grid.bottom).toBe(84)
    expect(crowded.tooltip.valueFormatter(0.12345678)).toBe('0.1235')

    const sparse = chartOptions({ key: 'ranking', type: 'bar', series: [{ name: '度中心性', data: [{ x: 'a', y: 1 }, { x: 'b', y: 2 }] }] }, true) as Record<string, any>
    expect(sparse.xAxis.axisLabel.rotate).toBe(0)
    expect(sparse.grid.bottom).toBe(54)
  })

  test('keeps gauge value and series name together', () => {
    const options = chartOptions({
      key: 'centralization', type: 'gauge', series: [{ name: '度中心势', data: [{ value: 0.42 }] }],
    }, true) as Record<string, any>

    expect(options.series[0]).toMatchObject({ type: 'gauge', data: [{ value: 0.42, name: '度中心势' }] })
  })
})
