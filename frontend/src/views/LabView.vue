<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import type { AlgorithmSpec, GraphSpec, HistoryRecord, RunResult } from '../api/contracts'
import { fetchAlgorithms, fetchRunResult, fetchRunStatus, submitRun } from '../api/client'
import FormulaBlock from '../components/FormulaBlock.vue'
import GraphEditor from '../components/GraphEditor.vue'
import HistoryPanel from '../components/HistoryPanel.vue'
import ParameterControls from '../components/ParameterControls.vue'
import RunStatus from '../components/RunStatus.vue'
import { LEARNING_EXAMPLE_GRAPH } from '../lab/exampleGraph'
import { clearHistory, deleteHistory, listHistory, saveHistory } from '../lab/historyStore'
import { defaultsFor } from '../lab/parameters'
import { downloadReproducibilityBundle } from '../lab/reproducibility'
import { executeRun, type RunPhase } from '../lab/runMachine'

const ResultsPanel = defineAsyncComponent({
  loader: () => import('../components/ResultsPanel.vue'),
  loadingComponent: { template: '<p class="state-message" role="status">正在准备结果视图…</p>' },
  delay: 0,
})

const algorithms = ref<AlgorithmSpec[]>([])
const registryLoading = ref(true)
const registryError = ref('')
const selectedKey = ref('')
const parameters = ref<Record<string, unknown>>({})
const seed = ref<number | null>(7)
const graph = ref<GraphSpec>(structuredClone(LEARNING_EXAMPLE_GRAPH))
const graphReady = ref(false)
const editorVersion = ref(0)
const phase = ref<RunPhase>('idle')
const runError = ref('')
const result = ref<RunResult | null>(null)
const records = ref<HistoryRecord[]>([])
const historyLoading = ref(true)
const compareRecord = ref<HistoryRecord | null>(null)
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

const selectedAlgorithm = computed(() => algorithms.value.find((item) => item.key === selectedKey.value) ?? null)
const graphType = computed(() => graph.value.directed ? 'directed' : 'undirected')
const incompatible = computed(() => selectedAlgorithm.value ? !selectedAlgorithm.value.supported_graph_types.includes(graphType.value) : false)
const running = computed(() => phase.value === 'submitting' || phase.value === 'polling')
const canRun = computed(() => Boolean(selectedAlgorithm.value && graphReady.value && !incompatible.value && !running.value))

watch(selectedAlgorithm, (algorithm) => { if (algorithm) parameters.value = defaultsFor(algorithm) })

onMounted(async () => {
  const historyPromise = listHistory().then((items) => { records.value = items }).finally(() => { historyLoading.value = false })
  try {
    algorithms.value = await fetchAlgorithms()
    selectedKey.value = algorithms.value.find((item) => item.key === 'centrality.degree')?.key ?? algorithms.value[0]?.key ?? ''
  } catch (reason) { registryError.value = reason instanceof Error ? reason.message : '无法加载算法注册表。' }
  finally { registryLoading.value = false }
  await historyPromise
})

function onValidated(value: GraphSpec) { graph.value = value; graphReady.value = true; phase.value = 'idle'; runError.value = '' }
function onInvalid() { graphReady.value = false; phase.value = 'idle' }

async function run() {
  if (!selectedAlgorithm.value || !canRun.value) return
  runError.value = ''; result.value = null; compareRecord.value = null
  try {
    const completed = await executeRun({ algorithm: selectedAlgorithm.value.key, graph: graph.value, parameters: parameters.value, seed: seed.value }, { submitRun, fetchRunStatus, fetchRunResult }, (next) => { phase.value = next })
    result.value = completed
    const record: HistoryRecord = {
      id: completed.run_id,
      createdAt: new Date().toISOString(),
      algorithm: selectedAlgorithm.value.key,
      algorithmName: selectedAlgorithm.value.name,
      parameters: clone(parameters.value),
      seed: seed.value,
      graph: clone(graph.value),
      result: completed,
    }
    await saveHistory(record)
    records.value = [record, ...records.value.filter((item) => item.id !== record.id)]
  } catch (reason) { runError.value = reason instanceof Error ? reason.message : '运行失败，请检查输入后重试。' }
}

function resetExperiment() {
  graph.value = structuredClone(LEARNING_EXAMPLE_GRAPH)
  graphReady.value = false
  if (selectedAlgorithm.value) parameters.value = defaultsFor(selectedAlgorithm.value)
  seed.value = 7; phase.value = 'idle'; runError.value = ''; result.value = null; compareRecord.value = null
  editorVersion.value += 1
}

async function removeRecord(id: string) { await deleteHistory(id); records.value = records.value.filter((item) => item.id !== id); if (compareRecord.value?.id === id) compareRecord.value = null }
async function clearRecords() { await clearHistory(); records.value = []; compareRecord.value = null }

const categoryName = (key: string) => ({ graph: '图结构', model: '随机模型', centrality: '中心性', community: '社区发现', robustness: '鲁棒性', link: '链接预测', opinion: '意见动力学', dynamic: '动态网络', embedding: '图嵌入', text: '文本建网', export: '图导出' }[key.split('.')[0]] ?? '其他方法')
</script>

<template>
  <div class="lab-view page-shell">
    <header class="lab-intro"><div><p class="eyebrow">OPEN LABORATORY</p><h1>自由实验室</h1></div><p>你的图进入真实算法，而不是演示动画。每次运行记录算法版本、参数、种子与输入哈希；历史只保存在这台设备。</p><button type="button" class="button quiet" @click="resetExperiment">重置整个实验</button></header>

    <div class="lab-workbench">
      <div class="lab-main">
        <GraphEditor :key="editorVersion" v-model="graph" learning-example @validated="onValidated" @invalid="onInvalid" />

        <section class="algorithm-picker" aria-labelledby="algorithm-heading">
          <div class="control-heading"><div><p class="eyebrow">REGISTRY</p><h2 id="algorithm-heading">二、选择真实算法</h2></div><span v-if="selectedAlgorithm">v{{ selectedAlgorithm.version }}</span></div>
          <p v-if="registryLoading" class="state-message compact" role="status">正在读取后端算法注册表…</p>
          <p v-else-if="registryError" class="state-message error" role="alert">{{ registryError }}</p>
          <template v-else>
            <label class="algorithm-select">算法<select v-model="selectedKey"><option v-for="algorithm in algorithms" :key="algorithm.key" :value="algorithm.key">{{ algorithm.name }}</option></select></label>
            <div v-if="selectedAlgorithm" class="algorithm-notes"><div><span>{{ categoryName(selectedAlgorithm.key) }}</span><h3>{{ selectedAlgorithm.name }}</h3><p>{{ selectedAlgorithm.description }}</p><p>{{ selectedAlgorithm.explanation }}</p></div><FormulaBlock :formula="selectedAlgorithm.formula" /></div>
            <p v-if="incompatible" class="validation-error" role="alert">当前算法不支持{{ graph.directed ? '有向图' : '无向图' }}，请选择兼容方法或修改图类型。</p>
            <ParameterControls v-if="selectedAlgorithm" v-model="parameters" :algorithm="selectedAlgorithm" />
          </template>
        </section>

        <section class="run-console" aria-labelledby="run-heading">
          <div><p class="eyebrow">RUN & TRACE</p><h2 id="run-heading">三、运行并留下证据链</h2><label>随机种子<input v-model.number="seed" type="number" step="1" /></label></div>
          <div><RunStatus :phase="phase" :message="runError" /><button type="button" class="button primary run-button" :disabled="!canRun" @click="run">{{ running ? '正在提交…' : '运行真实算法' }}</button><p v-if="!graphReady" class="field-help">先在第一步通过图数据校验。</p></div>
        </section>
        <p v-if="runError" class="validation-error" role="alert">{{ runError }}</p>

        <div v-if="result" class="result-actions"><button type="button" class="button secondary" @click="downloadReproducibilityBundle(records.find((item) => item.id === result?.run_id)!)" :disabled="!records.some((item) => item.id === result?.run_id)">下载本次复现包</button><p>包含输入图、参数、种子、算法版本与完整结果。</p></div>
        <ResultsPanel v-if="result" :result="result" :compare-result="compareRecord?.result" />
      </div>

      <HistoryPanel :records="records" :loading="historyLoading" :active-compare-id="compareRecord?.id" @compare="compareRecord = $event" @remove="removeRecord" @clear="clearRecords" />
    </div>
  </div>
</template>
