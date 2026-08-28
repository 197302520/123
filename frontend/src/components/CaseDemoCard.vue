<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchAlgorithms, fetchRunResult, fetchRunStatus, submitRun } from '../api/client'
import type { GraphSpec, RunResult } from '../api/contracts'
import { executeRun } from '../lab/runMachine'
import ResultsPanel from './ResultsPanel.vue'

const props = defineProps<{
  algorithm: string
  label: string
  focus: string
  parameters: Record<string, unknown>
  seed: number | null
  graph: GraphSpec
}>()

const phase = ref<'idle' | 'running' | 'completed' | 'failed'>('idle')
const result = ref<RunResult | null>(null)
const error = ref('')
const displayName = ref(props.algorithm)

onMounted(async () => {
  try {
    const algorithms = await fetchAlgorithms()
    displayName.value = algorithms.find((item) => item.key === props.algorithm)?.name ?? props.algorithm
  } catch { /* 拿不到注册表时退回算法键，不阻塞运行 */ }
})

async function run() {
  if (phase.value === 'running') return
  phase.value = 'running'
  result.value = null
  error.value = ''
  try {
    result.value = await executeRun(
      { algorithm: props.algorithm, graph: props.graph, parameters: props.parameters, seed: props.seed },
      { submitRun, fetchRunStatus, fetchRunResult },
      () => {},
    )
    phase.value = 'completed'
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '运行失败，请稍后重试。'
    phase.value = 'failed'
  }
}
</script>

<template>
  <section class="case-demo-card">
    <header class="demo-head">
      <div>
        <h3>{{ label }}</h3>
        <p class="demo-meta">{{ displayName }} · 随机种子 {{ seed ?? '未固定' }}</p>
      </div>
      <button class="button primary" type="button" :disabled="phase === 'running'" @click="run">
        {{ phase === 'running' ? '正在计算…' : phase === 'completed' ? '重新运行' : '运行分析' }}
      </button>
    </header>
    <p v-if="focus" class="demo-focus"><strong>看什么：</strong>{{ focus }}</p>
    <p v-if="phase === 'running'" class="state-message compact" role="status">服务器正在真实计算，请稍候…</p>
    <p v-if="error" class="state-message compact error" role="alert">{{ error }}</p>
    <p v-if="result && result.warnings.length" class="demo-warnings" role="note">⚠ {{ result.warnings.join('；') }}</p>
    <ResultsPanel v-if="result" :result="result" />
  </section>
</template>
