<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import AppFooter from './components/AppFooter.vue'

const route = useRoute()
const presentation = computed(() => route.meta.presentation === true)
</script>

<template>
  <a class="skip-link" href="#main-content">跳到主要内容</a>
  <header v-if="!presentation" class="site-header">
    <RouterLink class="wordmark" to="/" aria-label="关系研习室首页">
      <span class="wordmark-mark" aria-hidden="true">关系</span>
      <span>社会网络分析研习室<small>CASE · METHOD · EVIDENCE</small></span>
    </RouterLink>
    <nav aria-label="主要导航">
      <RouterLink to="/courses">课程</RouterLink>
      <RouterLink to="/cases">案例</RouterLink>
      <RouterLink class="nav-lab" to="/lab">自由实验室</RouterLink>
    </nav>
  </header>
  <main id="main-content" :class="{ 'presentation-main': presentation }">
    <RouterView />
  </main>
  <AppFooter v-if="!presentation" />
</template>
