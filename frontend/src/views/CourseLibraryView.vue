<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchModules } from '../api/client'
import type { CourseModule } from '../api/contracts'
import { moduleEditorial } from '../content/catalog'

const modules = ref<CourseModule[]>([])
const loading = ref(true)
const error = ref('')
onMounted(async () => {
  try { modules.value = await fetchModules() }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '无法加载课程。' }
  finally { loading.value = false }
})
</script>

<template>
  <section class="page-shell library-page" aria-labelledby="course-title">
    <header class="page-intro split-intro">
      <div><p class="eyebrow">COURSE LIBRARY · 01—07</p><h1 id="course-title">从关系语言到<br>动态网络</h1></div>
      <p>课程不是算法清单。七个模块沿着“表示—测量—识别—传播—检验—预测—演化”逐层推进，每一节都回到案例发问。</p>
    </header>
    <p v-if="loading" class="state-message" role="status">正在加载七个课程模块…</p>
    <div v-else-if="error" class="state-message error" role="alert"><strong>课程暂时无法打开</strong><br>{{ error }}</div>
    <ol v-else class="course-ledger">
      <li v-for="module in modules" :key="module.slug">
        <RouterLink :to="`/courses/${module.slug}`">
          <span class="ledger-number">0{{ module.order }}</span>
          <div><p>{{ moduleEditorial(module.slug)?.accent }}</p><h2>{{ module.title.replace(/^模块.：/, '') }}</h2><span>{{ moduleEditorial(module.slug)?.question }}</span></div>
          <p>{{ module.summary }}</p><strong>{{ moduleEditorial(module.slug)?.methods }}</strong><span class="ledger-arrow" aria-hidden="true">↗</span>
        </RouterLink>
      </li>
    </ol>
  </section>
</template>
