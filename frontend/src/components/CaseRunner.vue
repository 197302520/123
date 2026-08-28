<script setup lang="ts">
import { computed } from 'vue'
import type { CaseDetail, GraphSpec } from '../api/contracts'
import CaseDatasetBrief from './CaseDatasetBrief.vue'
import CaseDemoCard from './CaseDemoCard.vue'

const props = defineProps<{ detail: CaseDetail }>()

const isRecord = (value: unknown): value is Record<string, unknown> =>
  Boolean(value && typeof value === 'object' && !Array.isArray(value))

const caseGraph = computed<GraphSpec | null>(() => {
  const metadata = props.detail.dataset?.metadata
  return isRecord(metadata) && isRecord(metadata.graph) ? (metadata.graph as unknown as GraphSpec) : null
})

const demos = computed(() => {
  const metadata = props.detail.dataset?.metadata
  if (!isRecord(metadata) || !Array.isArray(metadata.demos)) return []
  return metadata.demos.flatMap((item) => {
    if (!isRecord(item) || typeof item.algorithm !== 'string') return []
    return [{
      algorithm: item.algorithm,
      label: typeof item.label === 'string' ? item.label : item.algorithm,
      focus: typeof item.focus === 'string' ? item.focus : '',
      parameters: isRecord(item.parameters) ? item.parameters : {},
      seed: typeof item.seed === 'number' ? item.seed : null,
    }]
  })
})
</script>

<template>
  <div class="case-runner">
    <template v-if="caseGraph && demos.length">
      <CaseDatasetBrief :dataset="detail.dataset" :graph="caseGraph" />
      <section class="runner-demos" aria-labelledby="runner-demos-title">
        <header class="runner-demos-head">
          <div>
            <p class="eyebrow">BUILT-IN RUNS · 内置分析</p>
            <h2 id="runner-demos-title">参数已按案例配好，就地运行</h2>
          </div>
          <p class="runner-demos-note">每个任务都用上方这份真实数据在服务器上完成计算；想换成自己的数据、修改参数或跨算法对比，用页面底部的「去实验室自由探索」。</p>
        </header>
        <div class="runner-demo-list">
          <CaseDemoCard
            v-for="demo in demos"
            :key="`${demo.algorithm}-${demo.label}`"
            v-bind="demo"
            :graph="caseGraph"
          />
        </div>
      </section>
    </template>
    <p v-else class="state-message compact" role="status">
      本案例暂未配置内置分析；请用页面底部「去实验室自由探索」载入案例数据后运行。
    </p>
  </div>
</template>
