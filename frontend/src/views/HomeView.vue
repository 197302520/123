<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchCases, fetchModules } from '../api/client'
import type { CaseSummary, CourseModule } from '../api/contracts'
import { moduleEditorial } from '../content/catalog'
import NetworkHero from '../components/NetworkHero.vue'

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
  <div class="home-view section-shell">
    <!-- 平台是什么 + 行动入口 -->
    <section class="hero" aria-labelledby="hero-title">
      <div class="hero-copy">
        <p class="eyebrow">《社会网络分析》课程 · 智能教学平台</p>
        <h1 id="hero-title">把关系数据交给算法，<br><em>得到可信的<wbr>网络分析结论</em></h1>
        <p class="hero-intro">
          这是一套覆盖社会网络分析全流程的教学平台：从中文文本中抽取关系建网，
          或直接导入你自己的网络数据，一键运行 42 种算法——中心性、社区发现、链路预测、
          网络韧性、观点演化仿真——并生成图表与分析报告，适合课程作业、课堂实验与课程设计。
        </p>
        <div class="hero-actions">
          <RouterLink class="button primary" to="/courses">按模块学习算法</RouterLink>
          <RouterLink class="button secondary" to="/cases">先浏览教学案例</RouterLink>
          <RouterLink class="button ghost" to="/lab">直达自由实验室</RouterLink>
        </div>
      </div>
      <div class="hero-panel">
        <NetworkHero />
        <div class="hero-stats">
          <div class="stat-card"><strong>42</strong><span>种分析算法</span></div>
          <div class="stat-card"><strong>7</strong><span>个课程模块</span></div>
          <div class="stat-card"><strong>7</strong><span>个教学案例</span></div>
          <div class="stat-card"><strong>6</strong><span>步案例研习</span></div>
        </div>
      </div>
    </section>

    <!-- 平台公告条 -->
    <div class="notice-bar" role="note" aria-label="平台公告">
      <span class="notice-tag">公告</span>
      <p>42 种算法全部真实可运行：Leiden、GCN、GAT 依赖已内置；海豚案例已更新为 Lusseau 真实数据集（62 海豚 / 159 关联）。</p>
      <RouterLink to="/courses/communities">查看社区发现模块 →</RouterLink>
    </div>

    <!-- 怎么用：三步 -->
    <section aria-labelledby="steps-title">
      <div class="portal-section-head">
        <h2 id="steps-title">三步完成一次网络分析</h2>
        <p>数据、算法、结果三段式推进，分析报告一键导出。</p>
      </div>
      <div class="steps-strip">
        <div class="step-card">
          <span class="step-no" aria-hidden="true">1</span>
          <h2>准备网络数据</h2>
          <p>从案例库选一个案例（如空手道俱乐部网络），或在实验室粘贴"起点 终点 权重"边表、上传 TXT / CSV / Excel / GraphML 文件。</p>
        </div>
        <div class="step-card">
          <span class="step-no" aria-hidden="true">2</span>
          <h2>选择算法并运行</h2>
          <p>42 种算法任选：中心性、最短路径、社区发现、链路预测、韧性攻击、观点仿真。参数可调，运行真实计算而非演示动画。</p>
        </div>
        <div class="step-card">
          <span class="step-no" aria-hidden="true">3</span>
          <h2>解读结果并导出</h2>
          <p>查看指标表格、可视化图表与网络叠加图，将结果与案例情境对照解释，一键下载 HTML 报告与 ZIP 复现包。</p>
        </div>
      </div>
    </section>

    <p v-if="error" class="state-message error" role="alert">{{ error }}</p>

    <!-- 七个模块：学习路径 -->
    <section class="home-modules" aria-labelledby="modules-title">
      <div class="portal-section-head">
        <h2 id="modules-title">七个模块，一条学习路径</h2>
        <RouterLink class="more-link" to="/courses">查看完整课程</RouterLink>
      </div>
      <p v-if="loading" class="state-message" role="status">正在加载课程目录…</p>
      <p v-else-if="!modules.length && !error" class="state-message empty">课程目录暂未发布，可先进入自由实验室练习。</p>
      <ol v-else class="module-path">
        <li v-for="module in modules" :key="module.slug" class="path-stop">
          <span class="path-node" aria-hidden="true">{{ moduleEditorial(module.slug)?.numeral }}</span>
          <RouterLink class="path-card" :to="`/courses/${module.slug}`">
            <strong>{{ moduleEditorial(module.slug)?.accent ?? module.title }}</strong>
            <small>{{ moduleEditorial(module.slug)?.question ?? module.summary }}</small>
            <i>模块{{ moduleEditorial(module.slug)?.numeral }} · 进入</i>
          </RouterLink>
        </li>
      </ol>
    </section>

    <!-- 推荐案例 -->
    <section class="home-cases" aria-labelledby="cases-title">
      <div class="portal-section-head">
        <h2 id="cases-title">从经典案例开始上手</h2>
        <RouterLink class="more-link" to="/cases">更多案例</RouterLink>
      </div>
      <p v-if="loading" class="state-message" role="status">正在整理案例索引…</p>
      <p v-else-if="!cases.length && !error" class="state-message empty">案例索引暂未发布，可从课程模块了解分析方法。</p>
      <div v-else class="case-cards">
        <RouterLink v-for="(item, index) in cases.slice(0, 3)" :key="item.slug" class="case-card" :to="`/cases/${item.slug}`">
          <span class="case-card-index" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}<i>案例</i></span>
          <strong>{{ item.title }}</strong>
          <small>{{ item.summary }}</small>
          <i class="case-card-enter">进入案例研习</i>
        </RouterLink>
      </div>
    </section>
  </div>
</template>
