<script setup lang="ts">
import { computed, ref } from 'vue'
import type { CaseDataset, GraphInputSpec, GraphSpec } from '../api/contracts'
import GraphCanvas from './GraphCanvas.vue'

const props = defineProps<{ dataset: CaseDataset | null; graph: GraphSpec }>()

const isRecord = (value: unknown): value is Record<string, unknown> =>
  Boolean(value && typeof value === 'object' && !Array.isArray(value))

const metadata = computed(() => isRecord(props.dataset?.metadata) ? props.dataset!.metadata : {})

const FACT_LABELS: Record<string, string> = {
  source: '数据来源',
  license: '使用许可',
  cleaning: '清洗说明',
  version: '数据版本',
  projection: '投影方法',
}
const facts = computed(() => Object.entries(FACT_LABELS)
  .filter(([key]) => typeof metadata.value[key] === 'string' || typeof metadata.value[key] === 'number')
  .map(([key, label]) => ({ label, value: String(metadata.value[key]) })))

/** 供预览切换的多视图：时间快照案例展示各期，二部网络案例附投影对照。 */
interface GraphView { label: string; graph: GraphInputSpec; note: string }
const asGraph = (value: unknown): GraphInputSpec | null => {
  if (!isRecord(value) || !Array.isArray(value.nodes) || !Array.isArray(value.edges)) return null
  return value as unknown as GraphInputSpec
}
const views = computed<GraphView[]>(() => {
  const parameters = isRecord(metadata.value.parameters) ? metadata.value.parameters : {}
  const snapshots = Array.isArray(parameters.snapshots) ? parameters.snapshots : []
  if (snapshots.length > 1) {
    return snapshots
      .map((snapshot, index) => ({ snapshot: asGraph(snapshot), index }))
      .filter((item): item is { snapshot: GraphInputSpec; index: number } => item.snapshot !== null)
      .map(({ snapshot, index }) => ({
        label: `快照 t${index + 1}`,
        graph: snapshot,
        note: `第 ${index + 1} 期关系快照；运行时会把 ${snapshots.length} 期快照一起送入动态社群算法。`,
      }))
  }
  const projection = asGraph(metadata.value.projection_graph)
  if (projection && typeof metadata.value.projection === 'string') {
    return [
      { label: '原始二部图', graph: props.graph as unknown as GraphInputSpec, note: '运行分析使用这份原始数据；球员只连俱乐部，球员之间不直接相连。' },
      { label: '投影视图', graph: projection, note: `投影视图（${metadata.value.projection}）供对照观察，不是本次运行的输入。` },
    ]
  }
  return [{ label: '数据预览', graph: props.graph as unknown as GraphInputSpec, note: '可拖拽节点、滚轮缩放；下方分析都以这份真实数据为输入。' }]
})
const activeView = ref(0)
const view = computed(() => views.value[Math.min(activeView.value, views.value.length - 1)] ?? views.value[0])

/** 文本建网案例：图为空，原始数据是一段中文叙述。 */
const sourceText = computed(() => {
  if (props.graph.nodes.length) return ''
  const parameters = isRecord(metadata.value.parameters) ? metadata.value.parameters : {}
  return typeof parameters.text === 'string' ? parameters.text : ''
})

const stats = computed(() => {
  const nodeCount = props.graph.nodes.length
  const edgeCount = props.graph.edges.length
  const pairs = nodeCount * (nodeCount - 1)
  const density = nodeCount > 1 ? (props.graph.directed ? edgeCount / pairs : (2 * edgeCount) / pairs) : 0
  return [
    { label: '节点', value: String(nodeCount) },
    { label: '关系边', value: String(edgeCount) },
    { label: '网络类型', value: props.graph.directed ? '有向' : '无向' },
    { label: '整体密度', value: density.toFixed(3) },
    { label: '平均度', value: nodeCount ? (props.graph.directed ? edgeCount / nodeCount : (2 * edgeCount) / nodeCount).toFixed(2) : '0' },
  ]
})

const SAMPLE_SIZE = 8
const nodeAttributes = computed(() => isRecord(metadata.value.node_attributes) ? metadata.value.node_attributes : {})
const describeAttributes = (node: GraphSpec['nodes'][number]): string => {
  const attributes = isRecord(node.attributes) ? node.attributes : nodeAttributes.value[node.id]
  if (!isRecord(attributes)) return ''
  return Object.entries(attributes).filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${key}=${typeof value === 'object' ? JSON.stringify(value) : String(value)}`).join('；')
}
const nodeSample = computed(() => props.graph.nodes.slice(0, SAMPLE_SIZE).map((node) => ({ id: node.id, label: node.label || node.id, attributes: describeAttributes(node) })))
const edgeSample = computed(() => props.graph.edges.slice(0, SAMPLE_SIZE).map((edge) => ({ source: edge.source, target: edge.target, weight: edge.weight })))
const hasAttributes = computed(() => nodeSample.value.some((node) => node.attributes))
const truncated = computed(() => ({ nodes: props.graph.nodes.length > SAMPLE_SIZE, edges: props.graph.edges.length > SAMPLE_SIZE }))
</script>

<template>
  <section class="dataset-brief" aria-labelledby="dataset-brief-title">
    <header class="brief-head">
      <div>
        <p class="eyebrow">RUNS ON THIS DATA · 本次分析所用的数据</p>
        <h2 id="dataset-brief-title">{{ dataset?.title ?? '案例自带数据' }}</h2>
      </div>
      <p class="brief-provenance">{{ dataset?.provenance ?? '数据来源需由学习者说明。' }}</p>
    </header>

    <div v-if="!sourceText" class="brief-stats">
      <div v-for="stat in stats" :key="stat.label" class="brief-stat"><strong>{{ stat.value }}</strong><span>{{ stat.label }}</span></div>
    </div>

    <blockquote v-if="sourceText" class="brief-text">{{ sourceText }}</blockquote>
    <p v-if="sourceText" class="brief-text-note">该案例的原始数据是上面这段文本，还没有网络——运行下方分析时才会从中抽取实体与关系，生成网络。</p>

    <template v-else>
      <div class="brief-body">
        <figure class="brief-preview">
          <div v-if="views.length > 1" class="view-switch" role="group" aria-label="切换预览的数据视图">
            <button v-for="(item, index) in views" :key="item.label" type="button" :aria-pressed="index === activeView" @click="activeView = index">{{ item.label }}</button>
          </div>
          <GraphCanvas :graph="view.graph" :label="`案例数据集预览：${stats[0].value} 个节点、${stats[1].value} 条边`" />
          <figcaption>{{ view.note }}</figcaption>
        </figure>

        <div class="brief-facts">
          <dl v-if="facts.length">
            <template v-for="fact in facts" :key="fact.label">
              <dt>{{ fact.label }}</dt><dd>{{ fact.value }}</dd>
            </template>
          </dl>
          <p class="brief-facts-note">运行前先核对：这份数据怎么来的、能用到哪、被清洗过什么。数据建模的每个选择都会影响后面的结论。</p>
          <details class="brief-samples">
            <summary>查看原始数据样本（前 {{ SAMPLE_SIZE }} 条）</summary>
            <div class="sample-tables">
              <div class="table-scroll">
                <table aria-label="节点数据样本">
                  <caption>节点样本</caption>
                  <thead><tr><th scope="col">节点 ID</th><th scope="col">名称</th><th v-if="hasAttributes" scope="col">属性</th></tr></thead>
                  <tbody><tr v-for="node in nodeSample" :key="node.id"><td>{{ node.id }}</td><td>{{ node.label }}</td><td v-if="hasAttributes">{{ node.attributes || '—' }}</td></tr></tbody>
                </table>
              </div>
              <div class="table-scroll">
                <table aria-label="关系数据样本">
                  <caption>关系样本</caption>
                  <thead><tr><th scope="col">起点</th><th scope="col">终点</th><th scope="col">权重</th></tr></thead>
                  <tbody><tr v-for="(edge, index) in edgeSample" :key="index"><td>{{ edge.source }}</td><td>{{ edge.target }}</td><td>{{ edge.weight }}</td></tr></tbody>
                </table>
              </div>
              <p v-if="truncated.nodes || truncated.edges" class="sample-note">仅展示前 {{ SAMPLE_SIZE }} 条样本；完整数据共 {{ stats[0].value }} 个节点、{{ stats[1].value }} 条边，全部随每次运行提交给算法。</p>
            </div>
          </details>
        </div>
      </div>
    </template>
  </section>
</template>
