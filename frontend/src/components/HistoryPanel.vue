<script setup lang="ts">
import type { HistoryRecord } from '../api/contracts'
import { downloadReproducibilityBundle } from '../lab/reproducibility'

defineProps<{ records: HistoryRecord[]; loading?: boolean; activeCompareId?: string }>()
const emit = defineEmits<{ compare: [record: HistoryRecord]; remove: [id: string]; clear: [] }>()
const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
</script>

<template>
  <aside class="history-panel" aria-labelledby="history-heading">
    <div class="control-heading"><div><p class="eyebrow">LOCAL ARCHIVE</p><h2 id="history-heading">本机实验历史</h2></div><button v-if="records.length" type="button" class="text-button danger" @click="emit('clear')">清空历史</button></div>
    <p class="privacy-note">仅存于此浏览器，不关联姓名或账号。后端临时运行数据最多保留两小时。</p>
    <p v-if="loading" class="state-message compact" role="status">正在读取本机记录…</p>
    <p v-else-if="!records.length" class="state-message compact empty">还没有实验记录。完成一次真实运行后，它会出现在这里。</p>
    <ol v-else class="history-list">
      <li v-for="record in records" :key="record.id" :class="{ active: activeCompareId === record.id }">
        <div><strong>{{ record.algorithmName }}</strong><time :datetime="record.createdAt">{{ formatDate(record.createdAt) }}</time><code>{{ record.id.slice(0, 8) }}</code></div>
        <div class="history-actions"><button type="button" @click="emit('compare', record)">{{ activeCompareId === record.id ? '正在对比' : '加入对比' }}</button><button type="button" @click="downloadReproducibilityBundle(record)">下载复现包</button><button type="button" @click="emit('remove', record.id)">删除</button></div>
      </li>
    </ol>
  </aside>
</template>
