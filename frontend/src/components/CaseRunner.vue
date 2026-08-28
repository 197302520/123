<script setup lang="ts">
import { computed } from 'vue'
import type { CaseDetail, GraphSpec } from '../api/contracts'
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
      <p class="runner-intro">这些是本案例内置的真实算法，参数已按案例配好——点「运行分析」就地出结果；想改参数、换算法，再用页面底部的实验室入口。</p>
      <CaseDemoCard v-for="demo in demos" :key="`${demo.algorithm}-${demo.label}`" v-bind="demo" :graph="caseGraph" />
    </template>
    <p v-else class="state-message compact" role="status">
      本案例暂未配置内置分析；请用页面底部「去实验室自由探索」载入案例数据后运行。
    </p>
  </div>
</template>
