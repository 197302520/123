<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchCase, fetchCases } from '../api/client'
import type { CaseDetail, CaseSummary, GraphSpec } from '../api/contracts'
import { MODULE_EDITORIAL } from '../content/catalog'

const cases = ref<CaseSummary[]>([])
const loading = ref(true)
const error = ref('')
const query = ref('')
const moduleFilter = ref('all')
const details = ref<Record<string, CaseDetail>>({})

const availableModules = computed(() => MODULE_EDITORIAL.filter((module) => cases.value.some((item) => item.module === module.slug)))
const filteredCases = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase('zh-CN')
  return cases.value.filter((item) => (moduleFilter.value === 'all' || item.module === moduleFilter.value)
    && (!needle || `${item.title} ${item.summary}`.toLocaleLowerCase('zh-CN').includes(needle)))
})

function clearFilters() { query.value = ''; moduleFilter.value = 'all' }

const MODULE_HUES: Record<string, string> = {
  'network-basics': '#0d8a63',
  'network-measures': '#0f6b4f',
  'communities': '#6d5a8e',
  'diffusion': '#e8930c',
  'robustness': '#b45309',
  'link-prediction': '#2f9e8f',
  'dynamic-networks': '#55447a',
}
const hue = (module: string) => MODULE_HUES[module] ?? '#0f6b4f'
const numeralOf = (module: string) => MODULE_EDITORIAL.find((item) => item.slug === module)?.numeral ?? '·'
const accentOf = (module: string) => MODULE_EDITORIAL.find((item) => item.slug === module)?.accent ?? '综合案例'

interface VisualNode { x: number; y: number; r: number; fill: string }
interface VisualEdge { x1: number; y1: number; x2: number; y2: number }

/** 把案例真实数据集渲染成缩略网络：环形布局、按度定大小、首个分类属性上色。 */
function buildVisual(slug: string, graph: GraphSpec | undefined) {
  if (!graph || !graph.nodes.length) return null
  const width = 260
  const height = 170
  const nodes = graph.nodes.slice(0, 96)
  const allowed = new Set(nodes.map((node) => node.id))
  const edges = graph.edges.filter((edge) => allowed.has(edge.source) && allowed.has(edge.target)).slice(0, 260)
  const base = hue(cases.value.find((item) => item.slug === slug)?.module ?? '')

  const attributeKey = Object.keys(nodes[0].attributes ?? {})[0]
  let categories: string[] = []
  if (attributeKey) {
    const values = [...new Set(nodes.map((node) => String(node.attributes?.[attributeKey] ?? '')))]
    if (values.length > 1 && values.length <= 6) categories = values
  }
  const palette = ['#0f6b4f', '#6d5a8e', '#e8930c', '#2f9e8f', '#b45309', '#55447a']

  const degree = new Map<string, number>()
  for (const edge of edges) {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1)
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1)
  }
  const maxDegree = Math.max(1, ...degree.values())

  const positions = nodes.map((node, index) => {
    const angle = (index / nodes.length) * Math.PI * 2 - Math.PI / 2
    const wobble = ((index * 37) % 11) / 11
    return {
      x: width / 2 + Math.cos(angle) * (width / 2 - 18 - wobble * 10),
      y: height / 2 + Math.sin(angle) * (height / 2 - 14 - wobble * 8),
    }
  })
  const indexById = new Map(nodes.map((node, index) => [node.id, index]))
  const visualNodes: VisualNode[] = nodes.map((node, index) => {
    const category = categories.indexOf(String(node.attributes?.[attributeKey] ?? ''))
    return {
      ...positions[index],
      r: 2.2 + (degree.get(node.id) ?? 0) / maxDegree * 3.4,
      fill: category >= 0 ? palette[category % palette.length] : base,
    }
  })
  const visualEdges: VisualEdge[] = edges.map((edge) => {
    const from = positions[indexById.get(edge.source) ?? 0]
    const to = positions[indexById.get(edge.target) ?? 0]
    return { x1: from.x, y1: from.y, x2: to.x, y2: to.y }
  })
  return { width, height, nodes: visualNodes, edges: visualEdges, directed: graph.directed }
}

const visuals = computed(() => {
  const result: Record<string, ReturnType<typeof buildVisual>> = {}
  for (const item of cases.value) result[item.slug] = buildVisual(item.slug, details.value[item.slug]?.dataset?.metadata?.graph as GraphSpec | undefined)
  return result
})
const statsOf = (slug: string) => {
  const graph = details.value[slug]?.dataset?.metadata?.graph as GraphSpec | undefined
  if (!graph) return null
  return { nodes: graph.nodes.length, edges: graph.edges.length, directed: graph.directed }
}

onMounted(async () => {
  try {
    cases.value = await fetchCases()
    // 数据集缩略图是渐进增强：逐个补齐，失败不影响列表。
    const settled = await Promise.allSettled(cases.value.map((item) => fetchCase(item.slug)))
    const gathered: Record<string, CaseDetail> = {}
    settled.forEach((outcome, index) => {
      if (outcome.status === 'fulfilled') gathered[cases.value[index].slug] = outcome.value
    })
    details.value = gathered
  }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '无法加载案例。' }
  finally { loading.value = false }
})
</script>

<template>
  <section class="page-shell case-library" aria-labelledby="case-library-title">
    <header class="case-intro">
      <div>
        <p class="eyebrow">CASE INDEX</p>
        <h1 id="case-library-title">先进入情境，<br>再选择方法。</h1>
      </div>
      <p class="case-intro-lead">每个案例沿六个章节展开：提出问题、认识数据、选择方法、运行分析、解释发现与反思迁移。缩略图即案例真实数据集。</p>
    </header>

    <form class="case-toolbar" role="search" @submit.prevent>
      <label>搜索案例<input v-model="query" type="search" aria-label="搜索案例" placeholder="输入人物、现象或方法" /></label>
      <label>按课程模块筛选<select v-model="moduleFilter"><option value="all">全部模块</option><option v-for="module in availableModules" :key="module.slug" :value="module.slug">模块{{ module.numeral }} · {{ module.accent }}</option></select></label>
      <button type="button" class="button quiet" @click="clearFilters">清除筛选</button>
      <output aria-live="polite">{{ filteredCases.length }} 个公开案例</output>
    </form>

    <p v-if="loading" class="state-message" role="status">正在检索公开案例…</p>
    <div v-else-if="error" class="state-message error" role="alert"><strong>案例索引暂时无法读取</strong><br>{{ error }}</div>
    <div v-else-if="!filteredCases.length" class="state-message empty"><strong>没有符合条件的案例</strong><br>换一个关键词，或清除当前筛选。</div>

    <ol v-else class="case-wall" aria-label="教学案例列表">
      <li v-for="item in filteredCases" :key="item.slug" :class="{ featured: filteredCases[0]?.slug === item.slug && filteredCases.length > 1 }">
        <RouterLink class="case-card" :to="`/cases/${item.slug}`">
          <div class="card-visual" :style="{ '--case-hue': hue(item.module) }">
            <svg
              v-if="visuals[item.slug]"
              :viewBox="`0 0 ${visuals[item.slug]!.width} ${visuals[item.slug]!.height}`"
              role="img"
              :aria-label="`${item.title}数据集缩略图：${statsOf(item.slug)?.nodes ?? 0} 个节点、${statsOf(item.slug)?.edges ?? 0} 条边`"
            >
              <g stroke="currentColor" stroke-opacity=".22" stroke-width="1">
                <line v-for="(edge, index) in visuals[item.slug]!.edges" :key="index" :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" />
              </g>
              <circle v-for="(node, index) in visuals[item.slug]!.nodes" :key="index" :cx="node.x" :cy="node.y" :r="node.r" :fill="node.fill" fill-opacity=".92" />
            </svg>
            <svg v-else class="card-visual-text" viewBox="0 0 260 170" role="img" aria-label="文本建网案例：由中文文本运行时抽取关系">
              <g fill="#c9c4b6" rx="3">
                <rect x="16" y="26" width="86" height="7" rx="3.5" />
                <rect x="16" y="44" width="70" height="7" rx="3.5" />
                <rect x="16" y="62" width="92" height="7" rx="3.5" />
                <rect x="16" y="80" width="58" height="7" rx="3.5" />
                <rect x="16" y="98" width="80" height="7" rx="3.5" />
                <rect x="16" y="116" width="66" height="7" rx="3.5" />
              </g>
              <path d="M118 85 h34" stroke="var(--case-hue)" stroke-width="2" stroke-dasharray="5 4" />
              <path d="M146 79 156 85 146 91 z" fill="var(--case-hue)" />
              <g stroke="#9fb0a6" stroke-width="1">
                <line x1="186" y1="58" x2="222" y2="76" /><line x1="186" y1="58" x2="198" y2="104" /><line x1="222" y1="76" x2="198" y2="104" />
                <line x1="222" y1="76" x2="244" y2="112" /><line x1="198" y1="104" x2="244" y2="112" /><line x1="198" y1="104" x2="186" y2="128" /><line x1="244" y1="112" x2="226" y2="140" />
              </g>
              <circle cx="186" cy="58" r="7" fill="var(--case-hue)" /><circle cx="222" cy="76" r="5.5" fill="var(--case-hue)" />
              <circle cx="198" cy="104" r="8" fill="var(--case-hue)" /><circle cx="244" cy="112" r="5" fill="var(--case-hue)" />
              <circle cx="186" cy="128" r="4.5" fill="var(--case-hue)" /><circle cx="226" cy="140" r="4.5" fill="var(--case-hue)" />
            </svg>
          </div>
          <div class="card-body">
            <p class="card-kicker" :style="{ color: hue(item.module) }">模块{{ numeralOf(item.module) }} · {{ accentOf(item.module) }}</p>
            <h2>{{ item.title }}</h2>
            <p class="card-summary">{{ item.summary }}</p>
          </div>
          <div class="card-foot">
            <span v-if="statsOf(item.slug)" class="card-data">{{ statsOf(item.slug)!.nodes }} 节点 · {{ statsOf(item.slug)!.edges }} 边 · {{ statsOf(item.slug)!.directed ? '有向' : '无向' }}</span>
            <span v-else class="card-data">运行时从文本建网</span>
            <span class="card-go">六步案例研习 →</span>
          </div>
        </RouterLink>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.case-intro {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: clamp(1.6rem, 4vw, 4rem);
  align-items: end;
  padding-block: clamp(2.6rem, 5vw, 4rem) 1.8rem;
}
.case-intro h1 { margin-bottom: 0; font-family: var(--serif); font-size: clamp(2.1rem, 3.8vw, 3rem); letter-spacing: .02em; }
.case-intro-lead { margin: 0; color: var(--ink-soft); }

.case-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) auto auto;
  align-items: end;
  gap: .9rem;
  padding: 1.05rem 1.15rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}
.case-toolbar label { display: grid; gap: .4rem; font-weight: 600; font-size: .8rem; color: #33433c; }
.case-toolbar output { align-self: center; font-size: .8rem; color: var(--ink-soft); white-space: nowrap; }

/* 案例档案墙：首个案例横向通栏（跨两列），其余 3 列铺满，7 个案例零空位 */
.case-wall { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1.15rem; margin: 1.3rem 0 0; padding: 0; list-style: none; }
.case-wall li.featured { grid-column: span 2; }
.case-card {
  display: grid;
  grid-template-rows: auto 1fr auto;
  height: 100%;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  text-decoration: none;
  color: var(--ink);
  transition: box-shadow .18s ease, border-color .18s ease, transform .18s ease;
}
.case-card:hover { border-color: rgba(15, 107, 79, .4); box-shadow: var(--shadow-md); transform: translateY(-3px); color: var(--ink); }
.case-wall li.featured .case-card { grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); grid-template-rows: auto auto; grid-template-areas: "visual body" "visual foot"; }
.card-visual {
  position: relative;
  display: grid;
  place-items: center;
  padding: .55rem;
  color: var(--case-hue, var(--brand));
  background:
    radial-gradient(85% 90% at 78% 12%, rgba(109, 90, 142, .08), transparent 62%),
    linear-gradient(165deg, #fbfaf6 0%, #f2f5f1 100%);
  border-bottom: 1px solid var(--line);
  min-height: 150px;
}
.case-wall li.featured .card-visual { border-bottom: 0; border-right: 1px solid var(--line); min-height: 258px; grid-area: visual; }
.card-visual svg { width: 100%; height: 100%; max-height: 260px; }
.card-body { display: grid; gap: .45rem; align-content: start; padding: 1.05rem 1.15rem .8rem; }
.case-wall li.featured .card-body { grid-area: body; padding: 1.35rem 1.4rem .6rem; align-content: center; }
.card-kicker { margin: 0; font-size: .74rem; font-weight: 700; letter-spacing: .1em; }
.card-body h2 { margin: 0; font-size: clamp(1.06rem, 1.5vw, 1.24rem); }
.case-wall li.featured .card-body h2 { font-size: clamp(1.3rem, 2vw, 1.6rem); }
.card-summary { margin: 0; font-size: .84rem; line-height: 1.7; color: var(--ink-soft); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.case-wall li.featured .card-summary { -webkit-line-clamp: 4; }
.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .8rem;
  margin-top: auto;
  padding: .8rem 1.15rem 1rem;
  border-top: 1px dashed var(--line);
}
.case-wall li.featured .card-foot { grid-area: foot; }
.card-data { font-family: var(--mono); font-size: .7rem; color: var(--ink-soft); }
.card-go { font-size: .8rem; font-weight: 700; color: var(--brand-deep); white-space: nowrap; }
.case-card:hover .card-go { color: var(--brand); }

@media (max-width: 1150px) {
  .case-wall { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .case-toolbar { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .case-toolbar output { grid-column: 1 / -1; }
}
@media (max-width: 820px) {
  .case-intro { grid-template-columns: 1fr; }
  .case-wall { grid-template-columns: 1fr; }
  .case-wall li.featured { grid-column: auto; }
  .case-wall li.featured .case-card { grid-template-columns: 1fr; grid-template-rows: auto auto auto; grid-template-areas: "visual" "body" "foot"; }
  .case-wall li.featured .card-visual { border-right: 0; border-bottom: 1px solid var(--line); min-height: 190px; }
  .case-toolbar { grid-template-columns: 1fr; }
}
</style>
