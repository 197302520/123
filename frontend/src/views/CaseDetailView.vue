<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { fetchCase } from '../api/client'
import type { CaseDetail } from '../api/contracts'
import { CASE_SECTIONS } from '../content/catalog'
import ExampleNetwork from '../components/ExampleNetwork.vue'
import CaseRunner from '../components/CaseRunner.vue'

const props = defineProps<{ slug: string }>()
const detail = ref<CaseDetail | null>(null)
const error = ref('')
const activeIndex = ref(0)
const tabRefs = ref<HTMLButtonElement[]>([])
let loadRevision = 0

const isRecord = (value: unknown): value is Record<string, unknown> =>
  Boolean(value && typeof value === 'object' && !Array.isArray(value))

const caseDemos = computed(() => {
  const metadata = detail.value?.dataset?.metadata
  if (!isRecord(metadata) || !Array.isArray(metadata.demos)) return []
  return metadata.demos.flatMap((item) => {
    if (!isRecord(item) || typeof item.algorithm !== 'string') return []
    return [{
      algorithm: item.algorithm,
      label: typeof item.label === 'string' ? item.label : item.algorithm,
      focus: typeof item.focus === 'string' ? item.focus : '',
    }]
  })
})

const datasetFactKeys = ['source', 'license', 'cleaning', 'version', 'projection']
const datasetFacts = computed(() => {
  const metadata = detail.value?.dataset?.metadata
  if (!isRecord(metadata)) return []
  return datasetFactKeys
    .filter((key) => typeof metadata[key] === 'string' || typeof metadata[key] === 'number')
    .map((key) => [key, String(metadata[key])] as const)
})

function selectSection(index: number, focus = false) {
  activeIndex.value = (index + CASE_SECTIONS.length) % CASE_SECTIONS.length
  if (focus) nextTick(() => tabRefs.value[activeIndex.value]?.focus())
}
function onTabKey(event: KeyboardEvent, index: number) {
  if (event.key === 'ArrowRight' || event.key === 'ArrowDown') { event.preventDefault(); selectSection(index + 1, true) }
  if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') { event.preventDefault(); selectSection(index - 1, true) }
  if (event.key === 'Home') { event.preventDefault(); selectSection(0, true) }
  if (event.key === 'End') { event.preventDefault(); selectSection(CASE_SECTIONS.length - 1, true) }
}
async function load(slug: string) {
  const revision = ++loadRevision
  detail.value = null; error.value = ''; activeIndex.value = 0
  try {
    const response = await fetchCase(slug)
    if (revision === loadRevision) detail.value = response
  } catch (reason) { if (revision === loadRevision) error.value = reason instanceof Error ? reason.message : '无法加载案例。' }
}
watch(() => props.slug, load, { immediate: true })
</script>

<template>
  <article class="case-detail page-shell">
    <p v-if="!detail && !error" class="state-message" role="status">正在打开案例档案…</p>
    <div v-else-if="error" class="state-message error" role="alert"><strong>案例暂时无法打开</strong><br>{{ error }}</div>
    <template v-else-if="detail">
      <header class="case-hero">
        <div><p class="eyebrow">FIELD CASE / {{ detail.module }}</p><h1>{{ detail.title }}</h1><p class="lead">{{ detail.summary }}</p></div>
        <aside><span>六步研习</span><strong>从问题<br>到证据</strong><RouterLink :to="`/present/${detail.slug}`">进入课堂演示模式 ↗</RouterLink></aside>
      </header>
      <p v-if="detail.content" class="case-context">{{ detail.content }}</p>

      <nav class="case-section-tabs" aria-label="案例学习章节">
        <div role="tablist" aria-orientation="horizontal">
          <button v-for="(section, index) in CASE_SECTIONS" :key="section.id" :ref="(element) => { if (element) tabRefs[index] = element as HTMLButtonElement }" type="button" role="tab" :id="`tab-${section.id}`" :data-index="`0${index + 1}`" :aria-selected="activeIndex === index" :aria-controls="`panel-${section.id}`" :tabindex="activeIndex === index ? 0 : -1" @click="selectSection(index)" @keydown="onTabKey($event, index)">{{ section.title }}</button>
        </div>
      </nav>

      <section :id="`panel-${CASE_SECTIONS[activeIndex].id}`" :class="['case-section-panel', { 'run-stage': activeIndex === 3 }]" role="tabpanel" :aria-labelledby="`tab-${CASE_SECTIONS[activeIndex].id}`" tabindex="0">
        <div class="case-reading"><p class="eyebrow">{{ CASE_SECTIONS[activeIndex].eyebrow }}</p><h2>{{ CASE_SECTIONS[activeIndex].heading }}</h2><p>{{ CASE_SECTIONS[activeIndex].body }}</p><ol><li v-for="prompt in CASE_SECTIONS[activeIndex].prompts" :key="prompt">{{ prompt }}</li></ol></div>
        <aside v-if="activeIndex === 1" class="dataset-note"><p class="eyebrow">DATASET NOTE</p><h3>{{ detail.dataset?.title ?? '自带数据' }}</h3><p>{{ detail.dataset?.provenance ?? '数据来源需由学习者说明。' }}</p><dl v-if="datasetFacts.length"><template v-for="[key, value] in datasetFacts" :key="key"><dt>{{ key }}</dt><dd>{{ value }}</dd></template></dl></aside>
        <CaseRunner v-else-if="activeIndex === 3" :detail="detail" />
        <ExampleNetwork v-else-if="activeIndex === 0" />
        <aside v-else-if="activeIndex === 4 && caseDemos.length" class="margin-question">
          <span>解读提示</span>
          <p>对照「运行分析」里已经跑出的结果回答：</p>
          <ul class="demo-interpret-list"><li v-for="demo in caseDemos" :key="`${demo.algorithm}-${demo.label}`"><strong>{{ demo.label }}</strong>——{{ demo.focus }}</li></ul>
        </aside>
        <aside v-else class="margin-question"><span>课堂追问</span><p>{{ CASE_SECTIONS[activeIndex].prompts[0] }}</p><small>先写下判断，再进入实验室检验。</small></aside>
      </section>

      <footer class="case-next-step"><div><p class="eyebrow">MAKE IT COMPUTABLE</p><h2>想改参数、换算法？去自由实验室</h2><p>案例内置分析已能就地出结果；实验室供你自由探索——换自己的数据、调参数、跨算法对比，运行产生真实结果并保存在你的浏览器。</p></div><RouterLink class="button primary" :to="{ path: '/lab', query: { case: detail.slug } }">去实验室自由探索</RouterLink></footer>
    </template>
  </article>
</template>
