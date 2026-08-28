<script setup lang="ts">
import { computed, ref } from 'vue'
import type { GraphInputSpec, HistoryRecord, RunOverlay, RunResult } from '../api/contracts'
import { columnLabel } from '../lab/columnLabels'
import GraphCanvas from './GraphCanvas.vue'
import ResultChart from './ResultChart.vue'

const props = defineProps<{ result: RunResult; currentRecord?: HistoryRecord | null; compareRecord?: HistoryRecord | null }>()

// 说明书 3.2：结果网络叠加层同样支持三类布局切换。
type LayoutName = 'force' | 'circular' | 'tree'
const layoutName = ref<LayoutName>('force')
const layoutOptions: Array<{ value: LayoutName; label: string }> = [
  { value: 'force', label: 'FR 力导向布局' },
  { value: 'circular', label: 'Circular 环形布局' },
  { value: 'tree', label: '分层树形布局' },
]

function display(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(6).replace(/0+$/, '').replace(/\.$/, '')
  if (typeof value === 'object') return JSON.stringify(value, null, 0)
  return String(value)
}

function downloadExport(row: Record<string, unknown>) {
  const filename = String(row.filename ?? 'network-export')
  const mimeType = String(row.mime_type ?? 'application/octet-stream')
  const encoding = String(row.encoding ?? 'text')
  const content = String(row.content ?? '')
  let blob: Blob
  if (encoding === 'base64') {
    const bytes = Uint8Array.from(atob(content), (character) => character.charCodeAt(0))
    blob = new Blob([bytes], { type: mimeType })
  } else {
    blob = new Blob([content], { type: `${mimeType};charset=utf-8` })
  }
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

const isRecord = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === 'object' && !Array.isArray(value))
const replacementKeys = new Set(['generated_graph', 'extracted_graph'])

function replacementDirected(overlay: RunOverlay): boolean {
  if (overlay.key === 'generated_graph') {
    const generated = props.result.provenance.generated_graph
    if (isRecord(generated) && typeof generated.directed === 'boolean') return generated.directed
  }
  if (overlay.key === 'extracted_graph') {
    const extraction = props.result.provenance.extraction
    const extractedGraph = isRecord(extraction) ? extraction.graph : null
    if (isRecord(extractedGraph) && typeof extractedGraph.directed === 'boolean') return extractedGraph.directed
  }
  return props.result.validation.graph.directed
}

function overlayCaption(overlay: RunOverlay): string {
  const captions: Record<string, string> = {
    generated_graph: '展示算法生成的新网络，未与输入图合并。',
    extracted_graph: '展示从文本抽取的新网络，未与输入图合并。',
    predicted_edges: '候选关系以高对比虚线叠加在输入网络上。',
    node_values: '节点大小表示本次算法返回的数值。',
    hits: '节点大小表示枢纽分数；颜色与标签表示权威分数。',
    removal_order: '节点大小与标签表示移除顺序，越早移除越醒目。',
    opinions: '节点大小表示最终意见值。',
    communities: '节点颜色表示社区归属。',
    latest_communities: '节点颜色表示最后一个快照的社区归属。',
    embedding_clusters: '节点颜色表示嵌入空间中的聚类归属。',
  }
  return captions[overlay.key] ?? '节点样式或关系来自本次后端计算结果。'
}

function overlayGraph(overlay: RunOverlay): GraphInputSpec {
  const base = props.result.validation.graph
  const usableNodes = overlay.nodes.filter((node) => typeof node.id === 'string')
  const usableEdges = overlay.edges.filter((edge) => typeof edge.source === 'string' && typeof edge.target === 'string')
  if (replacementKeys.has(overlay.key)) {
    return {
      directed: replacementDirected(overlay),
      nodes: usableNodes.map((node) => ({ id: String(node.id), label: String(node.label ?? node.id) })),
      edges: usableEdges.map((edge) => ({ source: String(edge.source), target: String(edge.target), weight: Number.isFinite(Number(edge.weight)) ? Number(edge.weight) : 1 })),
    }
  }
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

    <div v-if="result.tables.length" class="result-section"><h3>数据表</h3>
      <p class="table-note">表头为中文对照，悬停可查看原始字段名（导出文件与复现包中使用原始字段名）。</p>
      <template v-for="table in result.tables" :key="table.key">
        <div v-if="table.key === 'export'" class="export-cards">
          <div v-for="(row, index) in table.rows" :key="index" class="export-card">
            <div class="export-meta"><strong>{{ row.filename }}</strong><span>{{ row.format }} · {{ row.mime_type }} · {{ row.encoding === 'base64' ? '二进制文件' : '文本文件' }}</span></div>
            <button type="button" class="button secondary" @click="downloadExport(row)">下载 {{ row.filename }}</button>
          </div>
        </div>
        <div v-else class="table-scroll"><table :aria-label="table.name"><caption>{{ table.name }}</caption><thead><tr><th v-for="column in table.columns" :key="column" scope="col" :title="`原始字段名：${column}`">{{ columnLabel(column) }}</th></tr></thead><tbody><tr v-for="(row, index) in table.rows" :key="index"><td v-for="column in table.columns" :key="column">{{ display(row[column]) }}</td></tr></tbody></table></div>
      </template>
    </div>
    <div v-if="result.charts.length" class="result-section"><h3>图表</h3><div class="chart-grid"><figure v-for="chart in result.charts" :key="chart.key"><ResultChart :chart="chart" /><figcaption>{{ chart.key }} · {{ chart.type }}</figcaption></figure></div></div>
    <div v-if="result.overlays.length" class="result-section"><h3>网络叠加层</h3><label class="layout-select">可视化布局<select v-model="layoutName" aria-label="选择可视化布局"><option v-for="option in layoutOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label><div class="overlay-grid"><figure v-for="overlay in result.overlays" :key="overlay.key"><GraphCanvas :graph="overlayGraph(overlay)" :overlay="overlay" :layout="layoutName" label="结果网络叠加图" /><figcaption>{{ overlayCaption(overlay) }}</figcaption></figure></div></div>

    <section v-if="comparable" class="compare-region" role="region" aria-label="实验结果对比">
      <h3>并排核对</h3><p>对比不是“找赢家”，而是检查结论对方法与参数是否稳定。</p>
      <div class="compare-columns"><article><span>当前实验</span><strong>{{ result.run_id }}</strong><dl><dt>算法</dt><dd>{{ currentRecord?.algorithm ?? result.provenance.algorithm }}</dd><dt>版本</dt><dd>{{ result.provenance.version }}</dd><dt>随机种子</dt><dd>{{ display(currentRecord?.seed ?? result.provenance.seed) }}</dd></dl></article><article><span>对比实验</span><strong>{{ comparable.id }}</strong><dl><dt>算法</dt><dd>{{ comparable.algorithm }}</dd><dt>版本</dt><dd>{{ comparable.result.provenance.version }}</dd><dt>随机种子</dt><dd>{{ display(comparable.seed) }}</dd></dl></article></div>
      <div class="table-scroll compare-table"><table aria-label="参数差异"><caption>参数差异</caption><thead><tr><th scope="col">参数</th><th scope="col">当前实验</th><th scope="col">对比实验</th></tr></thead><tbody><tr v-for="row in parameterRows" :key="row.key"><th scope="row">{{ row.key }}</th><td>{{ display(row.current) }}</td><td>{{ display(row.previous) }}</td></tr><tr v-if="!parameterRows.length"><td colspan="3">两次实验均未设置额外参数。</td></tr></tbody></table></div>
      <div class="comparison-results"><h4>结果值并列</h4><div class="compare-columns" v-for="table in tableComparisons" :key="table.key"><article><span>当前 · {{ table.key }}</span><pre>{{ table.current ? JSON.stringify(table.current.rows, null, 2) : '未返回此表' }}</pre></article><article><span>对比 · {{ table.key }}</span><pre>{{ table.previous ? JSON.stringify(table.previous.rows, null, 2) : '未返回此表' }}</pre></article></div><p v-if="!tableComparisons.length" class="state-message compact">两次实验都未返回表格，可结合图表与叠加层人工核对。</p></div>
    </section>

    <details class="provenance" open><summary>复现信息</summary><dl><template v-for="(value, key) in result.provenance" :key="key"><dt>{{ key }}</dt><dd>{{ display(value) }}</dd></template></dl></details>
  </section>
</template>
