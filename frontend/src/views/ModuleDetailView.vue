<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { fetchCases, fetchModule } from '../api/client'
import type { CaseSummary, CourseModuleDetail } from '../api/contracts'
import { moduleEditorial } from '../content/catalog'

const props = defineProps<{ slug: string }>()
const module = ref<CourseModuleDetail | null>(null)
const cases = ref<CaseSummary[]>([])
const error = ref('')
const editorial = computed(() => moduleEditorial(props.slug))
let loadRevision = 0
async function load(slug: string) {
  const revision = ++loadRevision
  module.value = null; cases.value = []; error.value = ''
  try {
    const [detail, allCases] = await Promise.all([fetchModule(slug), fetchCases()])
    if (revision !== loadRevision) return
    module.value = detail
    cases.value = allCases.filter((item) => item.module === slug)
  } catch (reason) { if (revision === loadRevision) error.value = reason instanceof Error ? reason.message : '无法加载模块。' }
}
watch(() => props.slug, load, { immediate: true })
</script>

<template>
  <article class="page-shell module-detail">
    <p v-if="!module && !error" class="state-message" role="status">正在展开课程讲义…</p>
    <p v-else-if="error" class="state-message error" role="alert">{{ error }}</p>
    <template v-else-if="module">
      <header class="module-hero">
        <p class="eyebrow">MODULE {{ String(module.order).padStart(2, '0') }} / {{ editorial?.accent }}</p>
        <h1>{{ module.title }}</h1><p class="lead">{{ editorial?.question }}</p><p>{{ module.summary }}</p>
      </header>
      <div class="module-reading-grid">
        <section aria-labelledby="learn-heading"><h2 id="learn-heading">本模块如何推进</h2><p>{{ module.content || '从一个可观察的关系现象开始，学习选择合适的网络表示与算法，并用方法限制约束结论。' }}</p><p>核心方法：<strong>{{ editorial?.methods }}</strong></p></section>
        <aside><p class="eyebrow">LEARNING CHECK</p><h2>完成后，你应能</h2><ul><li>把案例问题转换为图结构问题</li><li>说明所选方法的关键假设</li><li>从结果、警告和反例共同组织解释</li></ul></aside>
      </div>
      <section class="module-cases" aria-labelledby="module-cases-title"><h2 id="module-cases-title">从案例继续</h2>
        <p v-if="!cases.length" class="state-message">本模块的公开案例正在整理，可先进入自由实验室练习。</p>
        <RouterLink v-for="item in cases" :key="item.slug" :to="`/cases/${item.slug}`"><strong>{{ item.title }}</strong><span>{{ item.summary }}</span><i>进入案例 →</i></RouterLink>
        <RouterLink class="button secondary" to="/lab">带自己的网络进入实验室</RouterLink>
      </section>
    </template>
  </article>
</template>
