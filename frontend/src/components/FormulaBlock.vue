<script setup lang="ts">
import katex from 'katex'
import { computed } from 'vue'

const props = defineProps<{ formula: string }>()
const escapeHtml = (value: string) => value.replace(/[&<>"']/g, (character) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[character] ?? character))
const rendered = computed(() => {
  try { return katex.renderToString(props.formula || '\\text{无公式}', { throwOnError: false, displayMode: true }) }
  catch { return `<span>${escapeHtml(props.formula)}</span>` }
})
</script>

<template>
  <div class="formula-block" aria-label="算法公式" v-html="rendered" />
</template>
