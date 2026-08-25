<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { fetchCase } from '../api/client'
import type { CaseDetail } from '../api/contracts'
import { CASE_SECTIONS } from '../content/catalog'

const props = defineProps<{ slug: string }>()
const detail = ref<CaseDetail | null>(null)
const error = ref('')
const index = ref(0)
const section = computed(() => CASE_SECTIONS[index.value])
const step = (delta: number) => { index.value = Math.max(0, Math.min(CASE_SECTIONS.length - 1, index.value + delta)) }
function onKey(event: KeyboardEvent) {
  if (event.key === 'ArrowRight' || event.key === 'PageDown' || event.key === ' ') { event.preventDefault(); step(1) }
  if (event.key === 'ArrowLeft' || event.key === 'PageUp') { event.preventDefault(); step(-1) }
}
onMounted(async () => {
  window.addEventListener('keydown', onKey)
  try { detail.value = await fetchCase(props.slug) }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '无法加载演示内容。' }
})
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
