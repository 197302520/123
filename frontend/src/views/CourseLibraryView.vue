<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchAlgorithms, fetchCases, fetchModules } from '../api/client'
import type { CourseModule } from '../api/contracts'
import { moduleEditorial } from '../content/catalog'

const modules = ref<CourseModule[]>([])
const loading = ref(true)
const error = ref('')
const algorithmCounts = ref<Record<string, number>>({})
const caseCounts = ref<Record<string, number>>({})

const rows = computed(() => modules.value.map((module) => ({
  module,
  editorial: moduleEditorial(module.slug),
  algorithms: algorithmCounts.value[module.slug] ?? 0,
  cases: caseCounts.value[module.slug] ?? 0,
})))

onMounted(async () => {
  try {
    modules.value = await fetchModules()
    // 算法数与案例数是次级信息：失败不应让整页退化成错误态。
    const [algorithms, cases] = await Promise.allSettled([fetchAlgorithms(), fetchCases()])
    if (algorithms.status === 'fulfilled') {
      const counts: Record<string, number> = {}
      for (const item of algorithms.value) counts[item.module] = (counts[item.module] ?? 0) + 1
      algorithmCounts.value = counts
    }
    if (cases.status === 'fulfilled') {
      const counts: Record<string, number> = {}
      for (const item of cases.value) counts[item.module] = (counts[item.module] ?? 0) + 1
      caseCounts.value = counts
    }
  }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '无法加载课程。' }
  finally { loading.value = false }
})
</script>

<template>
  <section class="page-shell library-page" aria-labelledby="course-title">
    <header class="library-intro">
      <div class="library-intro-copy">
        <p class="eyebrow">COURSE LIBRARY · 01—07</p>
        <h1 id="course-title">从关系语言<br>到动态网络</h1>
      </div>
      <div class="library-intro-side">
        <p>课程不是算法清单。七个模块沿着“表示—测量—识别—传播—检验—预测—演化”逐层推进，每一节都回到案例发问。</p>
        <ol class="intro-path" aria-label="七个模块的学习路径">
          <li v-for="module in modules" :key="module.slug">
            <i aria-hidden="true">{{ moduleEditorial(module.slug)?.numeral }}</i>{{ moduleEditorial(module.slug)?.accent }}
          </li>
        </ol>
      </div>
    </header>

    <p v-if="loading" class="state-message" role="status">正在加载七个课程模块…</p>
    <div v-else-if="error" class="state-message error" role="alert"><strong>课程暂时无法打开</strong><br>{{ error }}</div>
    <p v-else-if="!modules.length" class="state-message empty">课程模块暂未发布，请稍后再来，或先进入自由实验室。</p>

    <ol v-else class="syllabus" aria-label="课程模块大纲">
      <li v-for="row in rows" :key="row.module.slug">
        <RouterLink class="syllabus-row" :to="`/courses/${row.module.slug}`">
          <span class="row-numeral" aria-hidden="true">{{ row.editorial?.numeral ?? row.module.order }}</span>
          <div class="row-head">
            <p class="row-accent">
              <span class="row-tag">模块{{ row.editorial?.numeral ?? row.module.order }}</span>
              <span class="row-question">{{ row.editorial?.question ?? row.module.summary }}</span>
            </p>
            <h2>{{ row.module.title.replace(/^模块.：/, '') }}</h2>
          </div>
          <p class="row-summary">{{ row.module.summary }}</p>
          <div class="row-meta">
            <span class="row-methods">{{ row.editorial?.methods }}</span>
            <span class="row-counts"><strong>{{ row.algorithms }}</strong> 种算法 · <strong>{{ row.cases }}</strong> 个案例</span>
          </div>
          <span class="row-go" aria-hidden="true">→</span>
        </RouterLink>
      </li>
    </ol>

    <footer v-if="modules.length" class="library-foot">
      <p>沿路径完成七个模块后，到自由实验室把任意网络交给 42 种算法。</p>
      <RouterLink class="button primary" to="/lab">直达自由实验室</RouterLink>
    </footer>
  </section>
</template>

<style scoped>
.library-intro {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: clamp(1.6rem, 4vw, 4rem);
  align-items: end;
  padding-block: clamp(2.6rem, 5vw, 4rem) clamp(1.8rem, 3.5vw, 2.6rem);
}
.library-intro-copy h1 { margin-bottom: 0; font-family: var(--serif); font-size: clamp(2.1rem, 3.8vw, 3rem); letter-spacing: .02em; }
.library-intro-side > p { margin: 0 0 1.1rem; color: var(--ink-soft); }
.intro-path {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: .3rem .45rem;
  margin: 0;
  padding: .8rem 1rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface);
  list-style: none;
  box-shadow: var(--shadow-sm);
}
.intro-path li { display: inline-flex; align-items: baseline; gap: .3rem; font-size: .78rem; font-weight: 600; color: var(--ink-soft); }
.intro-path li:not(:last-child)::after { content: "—"; margin-left: .45rem; color: var(--line-strong); font-weight: 400; }
.intro-path li i { font-family: var(--serif); font-style: normal; color: var(--brand); }
.intro-path li:nth-child(7) i { color: var(--violet); }

/* 课程大纲：七行编号账本，numeral | 标题区 | 摘要 | 方法与数量 | 箭头 */
.syllabus { margin: 0; padding: 0; list-style: none; border-top: 2px solid var(--brand); }
.syllabus-row {
  position: relative;
  display: grid;
  grid-template-columns: 4.6rem minmax(0, 1.3fr) minmax(0, .92fr) minmax(12rem, auto) 3rem;
  gap: clamp(1rem, 2.4vw, 2.2rem);
  align-items: center;
  padding: 1.45rem .4rem 1.45rem .2rem;
  border-bottom: 1px solid var(--line);
  text-decoration: none;
  color: var(--ink);
  transition: background-color .16s ease;
}
.syllabus-row:hover { background: linear-gradient(90deg, rgba(231, 243, 238, .75), transparent 72%); }
.row-numeral {
  justify-self: center;
  display: grid;
  place-items: center;
  width: 3.1rem;
  aspect-ratio: 1;
  border-radius: 50%;
  border: 1.5px solid var(--line-strong);
  background: var(--surface);
  font-family: var(--serif);
  font-size: 1.18rem;
  font-weight: 700;
  color: var(--brand-deep);
  transition: background-color .16s ease, color .16s ease, border-color .16s ease, box-shadow .16s ease;
}
.syllabus-row:hover .row-numeral { background: var(--brand-grad); border-color: var(--brand-deep); color: #fff; box-shadow: 0 6px 14px rgba(15, 107, 79, .25); }
.syllabus > li:nth-child(7) .row-numeral { color: var(--violet); }
.syllabus > li:nth-child(7):hover .row-numeral { background: linear-gradient(135deg, var(--violet), #55447a); border-color: #55447a; color: #fff; }
.row-head { display: grid; gap: .3rem; min-width: 0; }
.row-accent { display: flex; align-items: center; flex-wrap: wrap; gap: .5rem; margin: 0; }
.row-tag { padding: .1rem .55rem; border-radius: 4px; background: var(--brand-soft); color: var(--brand-deep); font-size: .7rem; font-weight: 700; letter-spacing: .08em; }
.syllabus > li:nth-child(7) .row-tag { background: var(--violet-soft); color: var(--violet); }
.row-question { font-size: .8rem; font-weight: 600; color: var(--ink-soft); }
.row-head h2 { margin: 0; font-size: clamp(1.2rem, 1.9vw, 1.5rem); letter-spacing: .01em; }
.syllabus-row:hover .row-head h2 { color: var(--brand-deep); }
.row-summary {
  margin: 0;
  font-size: .84rem;
  line-height: 1.72;
  color: var(--ink-soft);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.row-meta { display: grid; gap: .55rem; justify-items: start; }
.row-methods { padding: .28rem .7rem; border: 1px solid var(--line); border-radius: 999px; background: var(--surface); font-size: .74rem; font-weight: 600; color: #40514a; }
.row-counts { font-size: .78rem; color: var(--ink-soft); }
.row-counts strong { font-family: var(--serif); font-size: 1.02rem; color: var(--brand); }
.row-go { justify-self: end; font-size: 1.25rem; color: var(--line-strong); transition: color .16s ease, transform .16s ease; }
.syllabus-row:hover .row-go { color: var(--brand); transform: translateX(4px); }

.library-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
  margin-top: 1.8rem;
  padding: 1.3rem 1.5rem;
  border: 1px solid #cfe3d8;
  border-radius: var(--radius);
  background: linear-gradient(120deg, var(--brand-soft), #f4faf7);
}
.library-foot p { margin: 0; font-size: .92rem; }

@media (max-width: 1150px) {
  .syllabus-row { grid-template-columns: 3.6rem minmax(0, 1fr) minmax(10rem, auto) 2.4rem; }
  .row-summary { display: none; }
}
@media (max-width: 820px) {
  .library-intro { grid-template-columns: 1fr; }
  .syllabus-row { grid-template-columns: 3.4rem minmax(0, 1fr); row-gap: .8rem; }
  .row-numeral { justify-self: start; }
  .row-go { display: none; }
  .row-meta { grid-column: 2; }
}
</style>
