<script setup lang="ts">
import type { GraphInputSpec, RunOverlay, RunResult } from '../api/contracts'
import GraphCanvas from './GraphCanvas.vue'
import ResultChart from './ResultChart.vue'

const props = defineProps<{ result: RunResult; compareResult?: RunResult | null }>()

function display(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(6).replace(/0+$/, '').replace(/\.$/, '')
  if (typeof value === 'object') return JSON.stringify(value, null, 0)
  return String(value)
}

function overlayGraph(overlay: RunOverlay): GraphInputSpec {
  const usableNodes = overlay.nodes.filter((node) => typeof node.id === 'string')
  const usableEdges = overlay.edges.filter((edge) => typeof edge.source === 'string' && typeof edge.target === 'string')
  if (usableNodes.length) {
    return {
      directed: props.result.validation.graph.directed,
      nodes: usableNodes.map((node) => ({ id: String(node.id), label: String(node.label ?? node.id) })),
      edges: usableEdges.map((edge) => ({ source: String(edge.source), target: String(edge.target), weight: Number(edge.weight ?? edge.score ?? 1) })),
    }
  }
  return props.result.validation.graph
}

const hasArtifacts = (result: RunResult) => Boolean(result.tables.length || result.charts.length || result.overlays.length)
</script>

<template>
  <section class="results-panel" aria-labelledby="results-heading">
    <header class="results-heading"><div><p class="eyebrow">COMPUTED EVIDENCE</p><h2 id="results-heading">分析结果</h2></div><span class="result-stamp">真实计算 · {{ result.status }}</span></header>

    <div v-if="result.warnings.length" class="result-warnings" role="alert"><strong>解释前请注意</strong><ul><li v-for="warning in result.warnings" :key="warning">{{ warning }}</li></ul></div>
    <p v-if="!hasArtifacts(result)" class="state-message empty">本次算法没有返回表格、图表或网络叠加层。</p>

    <div v-if="result.tables.length" class="result-section"><h3>数据表</h3><div class="table-scroll" v-for="table in result.tables" :key="table.key"><table :aria-label="table.name"><caption>{{ table.name }}</caption><thead><tr><th v-for="column in table.columns" :key="column" scope="col">{{ column }}</th></tr></thead><tbody><tr v-for="(row, index) in table.rows" :key="index"><td v-for="column in table.columns" :key="column">{{ display(row[column]) }}</td></tr></tbody></table></div></div>
    <div v-if="result.charts.length" class="result-section"><h3>图表</h3><div class="chart-grid"><figure v-for="chart in result.charts" :key="chart.key"><ResultChart :chart="chart" /><figcaption>{{ chart.key }} · {{ chart.type }}</figcaption></figure></div></div>
    <div v-if="result.overlays.length" class="result-section"><h3>网络叠加层</h3><div class="overlay-grid"><figure v-for="overlay in result.overlays" :key="overlay.key"><GraphCanvas :graph="overlayGraph(overlay)" :overlay="overlay" label="结果网络叠加图" /><figcaption>{{ overlay.key }} · 颜色、大小或新边来自本次真实结果</figcaption></figure></div></div>

    <section v-if="compareResult" class="compare-region" role="region" aria-label="实验结果对比">
      <h3>并排核对</h3><p>对比不是“找赢家”，而是检查结论对方法与参数是否稳定。</p>
      <div class="compare-columns"><article><span>当前实验</span><strong>{{ result.run_id }}</strong><dl><dt>算法</dt><dd>{{ result.provenance.algorithm }}</dd><dt>版本</dt><dd>{{ result.provenance.version }}</dd><dt>结果表</dt><dd>{{ result.tables.length }}</dd></dl></article><article><span>对比实验</span><strong>{{ compareResult.run_id }}</strong><dl><dt>算法</dt><dd>{{ compareResult.provenance.algorithm }}</dd><dt>版本</dt><dd>{{ compareResult.provenance.version }}</dd><dt>结果表</dt><dd>{{ compareResult.tables.length }}</dd></dl></article></div>
    </section>

    <details class="provenance" open><summary>复现信息</summary><dl><template v-for="(value, key) in result.provenance" :key="key"><dt>{{ key }}</dt><dd>{{ display(value) }}</dd></template></dl></details>
  </section>
</template>
