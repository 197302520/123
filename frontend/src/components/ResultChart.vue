<script setup lang="ts">
import { BarChart, GaugeChart, HeatmapChart, LineChart, ScatterChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { ECharts } from 'echarts/core'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { RunChart } from '../api/contracts'
import { allowsMotion } from '../accessibility'
import { chartOptions } from './chartOptions'

const props = defineProps<{ chart: RunChart }>()
const container = ref<HTMLDivElement | null>(null)
echarts.use([BarChart, GaugeChart, HeatmapChart, LineChart, ScatterChart, GridComponent, LegendComponent, TooltipComponent, VisualMapComponent, CanvasRenderer])

let instance: ECharts | null = null

function render() {
  if (!container.value) return
  instance = echarts.init(container.value, undefined, { renderer: 'canvas' })
  instance.setOption(chartOptions(props.chart, allowsMotion()))
}
const resize = () => instance?.resize()
onMounted(() => { render(); window.addEventListener('resize', resize) })
onBeforeUnmount(() => { window.removeEventListener('resize', resize); instance?.dispose() })
</script>

<template><div ref="container" class="result-chart" role="img" :aria-label="`结果图表：${chart.key}`" /></template>
