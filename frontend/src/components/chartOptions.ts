import type { RunChart } from '../api/contracts'

type Datum = Record<string, unknown> | string | number
const isRecord = (value: Datum): value is Record<string, unknown> => typeof value === 'object' && value !== null
const text = (value: unknown, fallback: string) => value === undefined || value === null ? fallback : String(value)
const number = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : Number(value) || 0
const finiteOrNull = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : null
const escapeHtml = (value: unknown) => String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character] ?? character))

function base(animation: boolean) {
  return {
    animation,
    color: ['#0e8a5f', '#0f766e', '#b45309', '#6d5a8e'],
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, textStyle: { color: '#33433c' } },
    grid: { left: 52, right: 24, top: 28, bottom: 54 },
  }
}

/** 课堂投影可读的数值格式：最多 4 位小数，去掉尾随零。 */
function formatMetric(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  const numeric = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(numeric)) return '—'
  return String(parseFloat(numeric.toFixed(4)))
}

function heatmap(chart: RunChart, animation: boolean) {
  const xLabels: string[] = []
  const yLabels: string[] = []
  const data: Array<[string, string, number | null]> = []
  chart.series.flatMap((series) => series.data).forEach((datum, rowIndex) => {
    if (!isRecord(datum)) return
    if ('source' in datum && 'target' in datum && 'distance' in datum) {
      const source = text(datum.source, String(rowIndex + 1))
      const target = text(datum.target, String(rowIndex + 1))
      if (!xLabels.includes(target)) xLabels.push(target)
      if (!yLabels.includes(source)) yLabels.push(source)
      data.push([target, source, finiteOrNull(datum.distance)])
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
  const values = data.map((item) => item[2]).filter((value): value is number => typeof value === 'number')
  return {
    ...base(animation),
    tooltip: {
      position: 'top',
      formatter: (parameter: { value?: unknown }) => {
        const value = Array.isArray(parameter.value) ? parameter.value : []
        const distance = value[2]
        return `${escapeHtml(value[1] ?? '')} → ${escapeHtml(value[0] ?? '')}：${distance === null || distance === undefined ? '不可达' : escapeHtml(distance)}`
      },
    },
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
  const type = ['bar', 'line'].includes(chart.type) ? chart.type : 'line'
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
      return number(datum.y ?? datum.value ?? datum.score)
    }),
  }))
  return {
    ...base(animation),
    tooltip: { trigger: 'axis', valueFormatter: (value: unknown) => formatMetric(value) },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: '#6b6459', rotate: categories.length > 12 ? 45 : 0, fontSize: 11 },
    },
    yAxis: { type: 'value', axisLabel: { color: '#6b6459' }, splitLine: { lineStyle: { color: '#e3ded2' } } },
    grid: { left: 52, right: 24, top: 28, bottom: categories.length > 12 ? 84 : 54 },
    series,
  }
}

/**
 * 节点级散点（HITS 枢纽-权威、嵌入空间）：每个点带节点名，
 * 悬停只看这一个点——名字 + 两个维度，而不是整列原始小数。
 * 轴含义由后端 chart.x_axis / chart.y_axis 说明。
 */
function nodeScatter(chart: RunChart, animation: boolean) {
  const xLabel = text(chart.x_axis, 'x')
  const yLabel = text(chart.y_axis, 'y')
  const series = chart.series.map((item) => ({
    name: item.name,
    type: 'scatter',
    symbolSize: 12,
    emphasis: { focus: 'item', scale: 1.4 },
    data: item.data.flatMap((datum, index) => {
      if (!isRecord(datum)) return []
      return [{
        name: text(datum.label ?? datum.node, `#${index + 1}`),
        value: [number(datum.x), number(datum.y ?? datum.value ?? datum.score)],
      }]
    }),
  }))
  return {
    ...base(animation),
    tooltip: {
      trigger: 'item',
      formatter: (parameter: { name?: unknown; value?: unknown }) => {
        const value = Array.isArray(parameter.value) ? parameter.value : []
        return `<strong>${escapeHtml(parameter.name)}</strong><br/>${escapeHtml(xLabel)}：${formatMetric(value[0])}<br/>${escapeHtml(yLabel)}：${formatMetric(value[1])}`
      },
    },
    grid: { left: 56, right: 28, top: 36, bottom: 54 },
    xAxis: { type: 'value', name: xLabel, nameGap: 6, nameTextStyle: { color: '#6b6459', fontSize: 12 }, axisLabel: { color: '#6b6459' }, splitLine: { lineStyle: { color: '#e3ded2' } } },
    yAxis: { type: 'value', name: yLabel, nameGap: 10, nameTextStyle: { color: '#6b6459', fontSize: 12, align: 'left' }, axisLabel: { color: '#6b6459' }, splitLine: { lineStyle: { color: '#e3ded2' } } },
    series,
  }
}

export function chartOptions(chart: RunChart, animation: boolean): Record<string, unknown> {
  if (chart.type === 'heatmap') return heatmap(chart, animation)
  if (chart.type === 'timeline') return timeline(chart, animation)
  if (chart.type === 'gauge') return gauge(chart, animation)
  if (chart.type === 'scatter') return nodeScatter(chart, animation)
  return standard(chart, animation)
}
