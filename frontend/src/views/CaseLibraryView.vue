<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchCases } from '../api/client'
import type { CaseSummary } from '../api/contracts'
import { MODULE_EDITORIAL } from '../content/catalog'

const cases = ref<CaseSummary[]>([])
const loading = ref(true)
const error = ref('')
const query = ref('')
const moduleFilter = ref('all')

const availableModules = computed(() => MODULE_EDITORIAL.filter((module) => cases.value.some((item) => item.module === module.slug)))
const filteredCases = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase('zh-CN')
  return cases.value.filter((item) => (moduleFilter.value === 'all' || item.module === moduleFilter.value)
    && (!needle || `${item.title} ${item.summary}`.toLocaleLowerCase('zh-CN').includes(needle)))
})

function clearFilters() { query.value = ''; moduleFilter.value = 'all' }
onMounted(async () => {
  try { cases.value = await fetchCases() }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '无法加载案例。' }
  finally { loading.value = false }
})
</script>

<template>
  <section class="page-shell case-library" aria-labelledby="case-library-title">
    <header class="page-intro split-intro">
      <div><p class="eyebrow">CASE INDEX</p><h1 id="case-library-title">先进入情境，<br>再选择方法。</h1></div>
      <p>每个案例沿六个章节展开：提出问题、认识数据、选择方法、运行分析、解释发现与反思迁移。</p>
    </header>

    <form class="case-filters" role="search" @submit.prevent>
      <label>搜索案例<input v-model="query" type="search" aria-label="搜索案例" placeholder="输入人物、现象或方法" /></label>
      <label>按课程模块筛选<select v-model="moduleFilter"><option value="all">全部模块</option><option v-for="module in availableModules" :key="module.slug" :value="module.slug">模块{{ module.numeral }} · {{ module.accent }}</option></select></label>
      <button type="button" class="button quiet" @click="clearFilters">清除筛选</button>
      <output aria-live="polite">{{ filteredCases.length }} 个公开案例</output>
    </form>

    <p v-if="loading" class="state-message" role="status">正在检索公开案例…</p>
    <div v-else-if="error" class="state-message error" role="alert"><strong>案例索引暂时无法读取</strong><br>{{ error }}</div>
    <div v-else-if="!filteredCases.length" class="state-message empty"><strong>没有符合条件的案例</strong><br>换一个关键词，或清除当前筛选。</div>
    <ol v-else class="case-index-list">
      <li v-for="(item, index) in filteredCases" :key="item.slug">
        <RouterLink :to="`/cases/${item.slug}`">
          <span class="case-number">{{ String(index + 1).padStart(2, '0') }}</span>
          <div><p>{{ MODULE_EDITORIAL.find((module) => module.slug === item.module)?.accent }}</p><h2>{{ item.title }}</h2><span>{{ item.summary }}</span></div>
          <span class="case-route">六步案例研习 <b aria-hidden="true">→</b></span>
        </RouterLink>
      </li>
    </ol>
  </section>
</template>
