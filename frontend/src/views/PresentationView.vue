<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { fetchCase } from '../api/client'
import type { CaseDetail } from '../api/contracts'
import { CASE_SECTIONS } from '../content/catalog'

const props = defineProps<{ slug: string }>()
const detail = ref<CaseDetail | null>(null)
const error = ref('')
const index = ref(0)
const sections = computed(() => CASE_SECTIONS.map((base, sectionIndex) => {
  if (!detail.value) return base
  const item = detail.value
  const dataset = item.dataset
  const metadata = dataset ? Object.entries(dataset.metadata).map(([key, value]) => `${key}：${String(value)}`).join('；') : '本案例未附公开数据集，需说明自带数据来源。'
  const bodies = [
    `${item.title}关注“${item.summary}”。${item.content || '先从案例摘要界定要解释的关系现象。'}`,
    `${dataset?.title ?? '自带数据'}：${dataset?.provenance ?? '来源由学习者补充'}。${metadata}`,
    `围绕“${item.summary}”选择适用于 ${item.module} 模块的网络方法，并先核对图类型、参数假设与算法限制。`,
    `${item.title}不预置算法结论。把案例网络送入自由实验室，保留输入图、参数、种子与版本，再阅读真实返回的表格、图表和叠加层。`,
    `解释结果时回到“${item.summary}”，区分计算输出、${dataset?.title ?? '当前数据'}的边界与研究者推断。`,
    `以${item.title}为起点，改变数据边界、算法或参数，检验结论能否迁移；延伸问题仍须受“${item.content || item.summary}”约束。`,
  ]
  const prompts = sectionIndex === 0
    ? [`${item.title}中的行动者与关系分别是什么？`, ...base.prompts.slice(1)]
    : sectionIndex === 1 && dataset ? [`${dataset.title}如何定义节点与边？`, ...base.prompts.slice(1)] : base.prompts
  return { ...base, heading: `${base.heading}｜${item.title}`, body: bodies[sectionIndex], prompts }
}))
const section = computed(() => sections.value[index.value])
const step = (delta: number) => { index.value = Math.max(0, Math.min(CASE_SECTIONS.length - 1, index.value + delta)) }
function onKey(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  if (event.repeat || target?.closest('button, a, input, textarea, select, [contenteditable="true"]')) return
  if (event.key === 'ArrowRight' || event.key === 'PageDown' || event.key === ' ') { event.preventDefault(); step(1) }
  if (event.key === 'ArrowLeft' || event.key === 'PageUp') { event.preventDefault(); step(-1) }
}
async function load(slug: string) {
  detail.value = null; error.value = ''; index.value = 0
  try { detail.value = await fetchCase(slug) }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '无法加载演示内容。' }
}
watch(() => props.slug, load, { immediate: true })
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <section class="presentation-view" aria-labelledby="presentation-title">
    <p v-if="!detail && !error" class="state-message" role="status">正在准备课堂投影…</p>
    <p v-else-if="error" class="state-message error" role="alert">{{ error }}</p>
    <template v-else-if="detail">
      <header><RouterLink :to="`/cases/${detail.slug}`">退出演示</RouterLink><p>{{ detail.title }}</p><strong aria-live="polite">{{ String(index + 1).padStart(2, '0') }} / 06</strong></header>
      <div class="presentation-stage">
        <p class="eyebrow">{{ section.eyebrow }}</p><h1 id="presentation-title">{{ section.heading }}</h1><p class="presentation-body">{{ section.body }}</p>
        <ol><li v-for="prompt in section.prompts" :key="prompt">{{ prompt }}</li></ol>
      </div>
      <footer><button type="button" :disabled="index === 0" @click="step(-1)">← 上一节</button><div class="presentation-progress"><i :style="{ width: `${((index + 1) / 6) * 100}%` }" /></div><button type="button" :disabled="index === 5" @click="step(1)">下一节 →</button></footer>
    </template>
  </section>
</template>
