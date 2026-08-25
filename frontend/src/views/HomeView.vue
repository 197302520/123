<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchCases, fetchModules } from '../api/client'
import type { CaseSummary, CourseModule } from '../api/contracts'
import { moduleEditorial } from '../content/catalog'

const modules = ref<CourseModule[]>([])
const cases = ref<CaseSummary[]>([])
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try { [modules.value, cases.value] = await Promise.all([fetchModules(), fetchCases()]) }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '首页内容暂时无法加载。' }
  finally { loading.value = false }
})
</script>

<template>
  <div class="home-view">
    <section class="hero section-shell" aria-labelledby="hero-title">
      <div class="hero-copy">
        <p class="eyebrow">CASE-ORIENTED SOCIAL NETWORK ANALYSIS</p>
        <h1 id="hero-title">关系不是背景，<br><em>关系就是证据。</em></h1>
        <p class="hero-intro">从真实问题出发，把关系画成网络、交给算法，再把结果带回社会情境。这里没有登录门槛，也没有脱离证据的答案。</p>
        <div class="hero-actions">
          <RouterLink class="button primary" to="/cases">从案例开始</RouterLink>
          <RouterLink class="text-link" to="/lab">打开自由实验室 →</RouterLink>
        </div>
      </div>
      <div class="hero-figure" aria-label="从情境到证据的学习路径">
        <div class="orbit orbit-a"><span>问题</span></div>
        <div class="orbit orbit-b"><span>网络</span></div>
        <div class="orbit orbit-c"><span>方法</span></div>
        <div class="orbit orbit-d"><span>证据</span></div>
        <p>观察不是终点<br><strong>解释才是</strong></p>
      </div>
    </section>

    <section class="manifesto" aria-label="学习原则">
      <p>01 / 用案例提出问题</p><p>02 / 用算法检验证据</p><p>03 / 用限制约束解释</p>
    </section>

    <p v-if="error" class="state-message error" role="alert">{{ error }}</p>
    <section class="section-shell home-modules" aria-labelledby="modules-title">
      <div class="section-heading"><p class="eyebrow">SEVEN LENSES</p><h2 id="modules-title">七个模块，七种观察关系的方式</h2><RouterLink to="/courses">查看完整课程 →</RouterLink></div>
      <p v-if="loading" class="state-message" role="status">正在装订课程目录…</p>
      <p v-else-if="!modules.length && !error" class="state-message empty">课程目录暂未发布，可先进入自由实验室练习。</p>
      <ol v-else class="module-ribbon">
        <li v-for="module in modules" :key="module.slug">
          <RouterLink :to="`/courses/${module.slug}`">
            <span>模块{{ moduleEditorial(module.slug)?.numeral }}</span>
            <strong>{{ moduleEditorial(module.slug)?.accent ?? module.title }}</strong>
            <small>{{ moduleEditorial(module.slug)?.question ?? module.summary }}</small>
          </RouterLink>
        </li>
      </ol>
    </section>

    <section class="section-shell featured-cases" aria-labelledby="cases-title">
      <div class="section-index">CASE<br>NOTES</div>
      <div>
        <p class="eyebrow">READ THE NETWORK</p>
        <h2 id="cases-title">案例不是算法的包装，<br>而是解释的边界。</h2>
        <div class="case-lines">
          <RouterLink v-for="(item, index) in cases.slice(0, 3)" :key="item.slug" :to="`/cases/${item.slug}`">
            <span>0{{ index + 1 }}</span><strong>{{ item.title }}</strong><small>{{ item.summary }}</small>
          </RouterLink>
          <p v-if="loading" class="state-message" role="status">正在整理案例索引…</p>
          <p v-else-if="!cases.length && !error" class="state-message empty">案例索引暂未发布，可从课程模块了解分析方法。</p>
        </div>
      </div>
    </section>
  </div>
</template>
