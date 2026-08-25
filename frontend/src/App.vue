<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchModules } from './api/client'
import type { CourseModule } from './api/contracts'

const modules = ref<CourseModule[]>([])
const error = ref('')

onMounted(async () => {
  try { modules.value = await fetchModules() } catch (reason) { error.value = reason instanceof Error ? reason.message : '无法加载课程模块。' }
})
</script>

<template>
  <main>
    <h1>社会网络教学平台</h1>
    <p>面向案例的社会网络分析学习空间。</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <ul v-else>
      <li v-for="module in modules" :key="module.slug"><strong>{{ module.title }}</strong>：{{ module.summary }}</li>
    </ul>
  </main>
</template>
