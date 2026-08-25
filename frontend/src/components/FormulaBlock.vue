<script setup lang="ts">
import katex from 'katex'
import { computed } from 'vue'

const props = defineProps<{ formula: string }>()
const rendered = computed(() => {
  try { return katex.renderToString(props.formula || '\\text{无公式}', { throwOnError: false, displayMode: true }) }
  catch { return `<span>${props.formula}</span>` }
})
</script>

<template>
  <div class="formula-block" aria-label="算法公式" v-html="rendered" />
</template>
