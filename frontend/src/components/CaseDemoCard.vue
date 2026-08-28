<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { fetchAlgorithms, fetchRunResult, fetchRunStatus, submitRun } from '../api/client'
import type { GraphSpec, RunResult } from '../api/contracts'
import { executeRun } from '../lab/runMachine'
import { allowsMotion } from '../accessibility'
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
const resultsRegion = ref<HTMLElement | null>(null)

onMounted(async () => {
  try {
    const algorithms = await fetchAlgorithms()
    displayName.value = algorithms.find((item) => item.key === props.algorithm)?.name ?? props.algorithm
  } catch { /* 拿不到注册表时退回算法键，不阻塞运行 */ }
})

/** 参数徽章：把案例预置的配置亮出来，避免「黑箱一键运行」。 */
const paramChips = computed(() => Object.entries(props.parameters).map(([key, value]) => ({ key, value: describeParam(key, value) })).filter((chip) => chip.value))

function describeParam(key: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (typeof value === 'string') return value.length > 18 ? `文本（${value.length} 字）` : value
  if (Array.isArray(value)) return value.length ? (key === 'snapshots' ? `${value.length} 期快照` : `${value.length} 项`) : ''
  if (typeof value === 'object') {
    const keys = Object.keys(value as Record<string, unknown>)
    return keys.length ? (key === 'opinions' ? `${keys.length} 个初始观点` : `${keys.length} 项配置`) : ''
  }
  return String(value)
}

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
    await nextTick()
    resultsRegion.value?.scrollIntoView({ behavior: allowsMotion() ? 'smooth' : 'auto', block: 'start' })
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
        <div class="demo-params" :aria-label="`${label} 的预置参数`">
          <code v-for="chip in paramChips" :key="chip.key" class="param-chip">{{ chip.key }} = {{ chip.value }}</code>
          <code v-if="!paramChips.length" class="param-chip">默认参数</code>
        </div>
      </div>
      <button class="button primary" type="button" :disabled="phase === 'running'" @click="run">
        {{ phase === 'running' ? '正在计算…' : phase === 'completed' ? '重新运行' : '运行分析' }}
      </button>
    </header>
    <p v-if="focus" class="demo-focus"><strong>看什么：</strong>{{ focus }}</p>
    <div ref="resultsRegion">
      <p v-if="phase === 'running'" class="state-message compact" role="status">服务器正在真实计算，请稍候…</p>
      <p v-if="error" class="state-message compact error" role="alert">{{ error }}</p>
      <p v-if="result && result.warnings.length" class="demo-warnings" role="note">⚠ {{ result.warnings.join('；') }}</p>
      <ResultsPanel v-if="result" :result="result" />
    </div>
  </section>
</template>
