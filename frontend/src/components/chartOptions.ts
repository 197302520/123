import type { RunChart } from '../api/contracts'

type Datum = Record<string, unknown> | string | number
const isRecord = (value: Datum): value is Record<string, unknown> => typeof value === 'object' && value !== null
const text = (value: unknown, fallback: string) => value === undefined || value === null ? fallback : String(value)
const number = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : Number(value) || 0

function base(animation: boolean) {
  return {
    animation,
    color: ['#a94732', '#296a63', '#d69a2d', '#675279'],
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, textStyle: { color: '#33463e' } },
    grid: { left: 52, right: 24, top: 28, bottom: 54 },
  }
}

function heatmap(chart: RunChart, animation: boolean) {
  const xLabels: string[] = []
  const yLabels: string[] = []
  const data: Array<[string, string, number]> = []
  chart.series.flatMap((series) => series.data).forEach((datum, rowIndex) => {
    if (!isRecord(datum)) return
    if ('source' in datum && 'target' in datum && 'distance' in datum) {
      const source = text(datum.source, String(rowIndex + 1))
      const target = text(datum.target, String(rowIndex + 1))
      if (!xLabels.includes(target)) xLabels.push(target)
      if (!yLabels.includes(source)) yLabels.push(source)
      data.push([target, source, number(datum.distance)])
      return
    }
    const row = text(datum.node ?? datum.source ?? datum.row, String(rowIndex + 1))
    if (!yLabels.includes(row)) yLabels.push(row)
    Object.entries(datum).forEach(([column, value]) => {
      if (['node', 'source', 'row'].includes(column) || typeof value !== 'number') return
      if (!xLabels.includes(column)) xLabels.push(column)
      data.push([column, row, value])
    })
  })
  const values = data.map((item) => item[2])
  return {
    ...base(animation),
    tooltip: { position: 'top' },
    xAxis: { type: 'category', data: xLabels, splitArea: { show: true } },
    yAxis: { type: 'category', data: yLabels, splitArea: { show: true } },
    visualMap: { min: Math.min(...values, 0), max: Math.max(...values, 1), calculable: true, orient: 'horizontal', left: 'center', bottom: 0 },
    series: [{ name: chart.series[0]?.name ?? chart.key, type: 'heatmap', data, label: { show: data.length <= 100 } }],
  }
}

function timeline(chart: RunChart, animation: boolean) {
  const events = chart.series.flatMap((series) => series.data).filter(isRecord)
  const xLabels = [...new Set(events.map((item, index) => text(item.snapshot ?? item.step ?? item.time, String(index + 1))))]
  const yLabels = [...new Set(events.map((item) => text(item.event ?? item.type ?? item.kind ?? item.name, 'event')))]
  const data = events.map((item, index) => [
    text(item.snapshot ?? item.step ?? item.time, String(index + 1)),
    text(item.event ?? item.type ?? item.kind ?? item.name, 'event'),
  ])
  return {
    ...base(animation),
    xAxis: { type: 'category', name: '快照', data: xLabels },
    yAxis: { type: 'category', name: '事件', data: yLabels },
    series: [{ name: chart.series[0]?.name ?? 'events', type: 'scatter', symbolSize: 16, data }],
  }
}

function gauge(chart: RunChart, animation: boolean) {
  const series = chart.series.map((item) => {
    const first = item.data[0]
    return { name: item.name, type: 'gauge', data: [{ value: number(isRecord(first) ? first.value : first), name: item.name }] }
  })
  return { ...base(animation), tooltip: { formatter: '{a}<br>{b}: {c}' }, grid: undefined, series }
}

function standard(chart: RunChart, animation: boolean) {
  const type = ['bar', 'line', 'scatter'].includes(chart.type) ? chart.type : 'line'
  const categories: string[] = []
  const series = chart.series.map((item) => ({
    name: item.name,
    type,
    smooth: type === 'line',
    emphasis: { focus: 'series' },
    data: item.data.map((datum, index) => {
      if (!isRecord(datum)) return datum
      const x = text(datum.x ?? datum.label ?? datum.node, String(index + 1))
      if (!categories.includes(x)) categories.push(x)
      const y = number(datum.y ?? datum.value ?? datum.score)
      return type === 'scatter' ? [x, y] : y
    }),
  }))
  return {
    ...base(animation),
    xAxis: { type: type === 'scatter' ? 'value' : 'category', data: type === 'scatter' ? undefined : categories, axisLabel: { color: '#4f5e57' } },
    yAxis: { type: 'value', axisLabel: { color: '#4f5e57' }, splitLine: { lineStyle: { color: '#ddd6c8' } } },
    series,
  }
}

export function chartOptions(chart: RunChart, animation: boolean): Record<string, unknown> {
  if (chart.type === 'heatmap') return heatmap(chart, animation)
  if (chart.type === 'timeline') return timeline(chart, animation)
  if (chart.type === 'gauge') return gauge(chart, animation)
  return standard(chart, animation)
}
