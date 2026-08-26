<script setup lang="ts">
import type { RunPhase } from '../lab/runMachine'

defineProps<{ phase: RunPhase; message?: string }>()
const labels: Record<RunPhase, string> = {
  idle: '等待校验后的图数据', submitting: '正在提交计算任务…', polling: '算法正在计算，正在轮询结果…',
  background: '任务仍在后台运行，可继续查询状态或取消任务。',
  completed: '计算完成，可以查看结果与复现信息。', error: '运行未完成，可修改输入后重试。',
}
</script>

<template><p class="run-status" :class="`is-${phase}`" role="status" aria-live="polite"><span aria-hidden="true" />{{ message || labels[phase] }}</p></template>
