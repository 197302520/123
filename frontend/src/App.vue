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
    <RouterLink class="wordmark" to="/" aria-label="社会网络分析教学平台首页">
      <span class="wordmark-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" focusable="false">
          <path d="M6 7.5 12 5l6 2.5M6 7.5 8.5 15M18 7.5 15.5 15M8.5 15h7M12 5v4.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          <circle cx="6" cy="7.5" r="2.1" fill="currentColor"/>
          <circle cx="12" cy="5" r="2.1" fill="currentColor"/>
          <circle cx="18" cy="7.5" r="2.1" fill="currentColor"/>
          <circle cx="8.5" cy="15" r="2.4" fill="currentColor"/>
          <circle cx="15.5" cy="15" r="2.4" fill="currentColor"/>
        </svg>
      </span>
      <span><strong>社会网络分析教学平台</strong><small>SNA TEACHING PLATFORM</small></span>
    </RouterLink>
    <nav aria-label="主要导航">
      <RouterLink to="/">首页</RouterLink>
      <RouterLink to="/courses">课程模块</RouterLink>
      <RouterLink to="/cases">案例库</RouterLink>
      <RouterLink class="nav-lab" to="/lab">进入实验室</RouterLink>
    </nav>
  </header>
  <main id="main-content" :class="{ 'presentation-main': presentation }">
    <RouterView />
  </main>
  <AppFooter v-if="!presentation" />
</template>
