<script setup lang="ts">
import { computed } from 'vue'
import type { GraphInputSpec, HistoryRecord, RunOverlay, RunResult } from '../api/contracts'
import GraphCanvas from './GraphCanvas.vue'
import ResultChart from './ResultChart.vue'

const props = defineProps<{ result: RunResult; currentRecord?: HistoryRecord | null; compareRecord?: HistoryRecord | null }>()

function display(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(6).replace(/0+$/, '').replace(/\.$/, '')
  if (typeof value === 'object') return JSON.stringify(value, null, 0)
  return String(value)
}

function overlayGraph(overlay: RunOverlay): GraphInputSpec {
  const base = props.result.validation.graph
  const usableNodes = overlay.nodes.filter((node) => typeof node.id === 'string')
  const usableEdges = overlay.edges.filter((edge) => typeof edge.source === 'string' && typeof edge.target === 'string')
  const nodes = new Map(base.nodes.map((node) => [node.id, node]))
  usableNodes.forEach((node) => nodes.set(String(node.id), { id: String(node.id), label: String(node.label ?? node.id) }))
  const edges = base.edges.map((edge) => ({ ...edge }))
  const edgeKey = (source: string, target: string) => base.directed || source < target ? `${source}\u0000${target}` : `${target}\u0000${source}`
  const known = new Set(edges.map((edge) => edgeKey(edge.source, edge.target)))
  usableEdges.forEach((edge) => {
    const source = String(edge.source)
    const target = String(edge.target)
    if (!nodes.has(source)) nodes.set(source, { id: source, label: source })
    if (!nodes.has(target)) nodes.set(target, { id: target, label: target })
    const key = edgeKey(source, target)
    if (!known.has(key)) {
      edges.push({ source, target, weight: Number(edge.weight ?? edge.score ?? 1) })
      known.add(key)
    }
  })
  return { directed: base.directed, nodes: [...nodes.values()], edges }
}

const hasArtifacts = (result: RunResult) => Boolean(result.tables.length || result.charts.length || result.overlays.length)
const comparable = computed(() => props.compareRecord && props.compareRecord.id !== props.result.run_id ? props.compareRecord : null)
const parameterRows = computed(() => {
  if (!comparable.value) return []
  const current = props.currentRecord?.parameters ?? {}
  const previous = comparable.value.parameters
  return [...new Set([...Object.keys(current), ...Object.keys(previous)])].map((key) => ({ key, current: current[key], previous: previous[key] }))
})
const tableComparisons = computed(() => {
  if (!comparable.value) return []
  const current = new Map(props.result.tables.map((table) => [table.key, table]))
  const previous = new Map(comparable.value.result.tables.map((table) => [table.key, table]))
  return [...new Set([...current.keys(), ...previous.keys()])].map((key) => ({ key, current: current.get(key), previous: previous.get(key) }))
})
</script>

<template>
  <section class="results-panel" aria-labelledby="results-heading">
    <header class="results-heading"><div><p class="eyebrow">COMPUTED EVIDENCE</p><h2 id="results-heading">分析结果</h2></div><span class="result-stamp">真实计算 · {{ result.status }}</span></header>

    <div v-if="result.warnings.length" class="result-warnings" role="alert"><strong>解释前请注意</strong><ul><li v-for="warning in result.warnings" :key="warning">{{ warning }}</li></ul></div>
    <p v-if="!hasArtifacts(result)" class="state-message empty">本次算法没有返回表格、图表或网络叠加层。</p>

    <div v-if="result.tables.length" class="result-section"><h3>数据表</h3><div class="table-scroll" v-for="table in result.tables" :key="table.key"><table :aria-label="table.name"><caption>{{ table.name }}</caption><thead><tr><th v-for="column in table.columns" :key="column" scope="col">{{ column }}</th></tr></thead><tbody><tr v-for="(row, index) in table.rows" :key="index"><td v-for="column in table.columns" :key="column">{{ display(row[column]) }}</td></tr></tbody></table></div></div>
    <div v-if="result.charts.length" class="result-section"><h3>图表</h3><div class="chart-grid"><figure v-for="chart in result.charts" :key="chart.key"><ResultChart :chart="chart" /><figcaption>{{ chart.key }} · {{ chart.type }}</figcaption></figure></div></div>
    <div v-if="result.overlays.length" class="result-section"><h3>网络叠加层</h3><div class="overlay-grid"><figure v-for="overlay in result.overlays" :key="overlay.key"><GraphCanvas :graph="overlayGraph(overlay)" :overlay="overlay" label="结果网络叠加图" /><figcaption>{{ overlay.key }} · 颜色、大小或新边来自本次真实结果</figcaption></figure></div></div>

    <section v-if="comparable" class="compare-region" role="region" aria-label="实验结果对比">
      <h3>并排核对</h3><p>对比不是“找赢家”，而是检查结论对方法与参数是否稳定。</p>
      <div class="compare-columns"><article><span>当前实验</span><strong>{{ result.run_id }}</strong><dl><dt>算法</dt><dd>{{ currentRecord?.algorithm ?? result.provenance.algorithm }}</dd><dt>版本</dt><dd>{{ result.provenance.version }}</dd><dt>随机种子</dt><dd>{{ display(currentRecord?.seed ?? result.provenance.seed) }}</dd></dl></article><article><span>对比实验</span><strong>{{ comparable.id }}</strong><dl><dt>算法</dt><dd>{{ comparable.algorithm }}</dd><dt>版本</dt><dd>{{ comparable.result.provenance.version }}</dd><dt>随机种子</dt><dd>{{ display(comparable.seed) }}</dd></dl></article></div>
      <div class="table-scroll compare-table"><table aria-label="参数差异"><caption>参数差异</caption><thead><tr><th scope="col">参数</th><th scope="col">当前实验</th><th scope="col">对比实验</th></tr></thead><tbody><tr v-for="row in parameterRows" :key="row.key"><th scope="row">{{ row.key }}</th><td>{{ display(row.current) }}</td><td>{{ display(row.previous) }}</td></tr><tr v-if="!parameterRows.length"><td colspan="3">两次实验均未设置额外参数。</td></tr></tbody></table></div>
      <div class="comparison-results"><h4>结果值并列</h4><div class="compare-columns" v-for="table in tableComparisons" :key="table.key"><article><span>当前 · {{ table.key }}</span><pre>{{ table.current ? JSON.stringify(table.current.rows, null, 2) : '未返回此表' }}</pre></article><article><span>对比 · {{ table.key }}</span><pre>{{ table.previous ? JSON.stringify(table.previous.rows, null, 2) : '未返回此表' }}</pre></article></div><p v-if="!tableComparisons.length" class="state-message compact">两次实验都未返回表格，可结合图表与叠加层人工核对。</p></div>
    </section>

    <details class="provenance" open><summary>复现信息</summary><dl><template v-for="(value, key) in result.provenance" :key="key"><dt>{{ key }}</dt><dd>{{ display(value) }}</dd></template></dl></details>
  </section>
</template>
