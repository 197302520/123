<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { AlgorithmSpec, GraphSpec, HistoryRecord, RunRequest, RunResult } from '../api/contracts'
import { cancelRun, fetchAlgorithms, fetchCase, fetchReportBundle, fetchRunResult, fetchRunStatus, submitRun } from '../api/client'
import FormulaBlock from '../components/FormulaBlock.vue'
import GraphEditor from '../components/GraphEditor.vue'
import HistoryPanel from '../components/HistoryPanel.vue'
import ParameterControls from '../components/ParameterControls.vue'
import RunStatus from '../components/RunStatus.vue'
import { LEARNING_EXAMPLE_GRAPH } from '../lab/exampleGraph'
import { clearHistory, deleteHistory, listHistory, saveHistory } from '../lab/historyStore'
import { defaultsFor } from '../lab/parameters'
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
const parameterVersion = ref(0)
const phase = ref<RunPhase>('idle')
const runError = ref('')
const historyError = ref('')
const result = ref<RunResult | null>(null)
const currentRecord = ref<HistoryRecord | null>(null)
const records = ref<HistoryRecord[]>([])
const historyLoading = ref(true)
const compareRecord = ref<HistoryRecord | null>(null)
const parametersValid = ref(true)
const caseMessage = ref('')
const caseLoadError = ref('')
const reportDownloading = ref(false)
const cancellationRunId = ref<string | null>(null)
const cancellationMessage = ref('')
const cancellationError = ref('')
const cancellationInFlight = ref(false)
let activeRunController: AbortController | null = null
let activeRunId: string | null = null
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

const selectedAlgorithm = computed(() => algorithms.value.find((item) => item.key === selectedKey.value) ?? null)
const graphType = computed(() => graph.value.directed ? 'directed' : 'undirected')
const incompatible = computed(() => selectedAlgorithm.value ? !selectedAlgorithm.value.supported_graph_types.includes(graphType.value) : false)
const running = computed(() => phase.value === 'submitting' || phase.value === 'polling')
const canRun = computed(() => Boolean(selectedAlgorithm.value && graphReady.value && parametersValid.value && !incompatible.value && !running.value))

watch(selectedAlgorithm, (algorithm) => { parametersValid.value = true; if (algorithm) parameters.value = defaultsFor(algorithm) })

onMounted(async () => {
  const historyPromise = (async () => {
    try { records.value = await listHistory() }
    catch (reason) { historyError.value = reason instanceof Error ? reason.message : '无法读取本机实验历史。' }
    finally { historyLoading.value = false }
  })()
  try {
    algorithms.value = await fetchAlgorithms()
    selectedKey.value = algorithms.value.find((item) => item.key === 'centrality.degree')?.key ?? algorithms.value[0]?.key ?? ''
  } catch (reason) { registryError.value = reason instanceof Error ? reason.message : '无法加载算法注册表。' }
  finally { registryLoading.value = false }
  const requestedCase = new URLSearchParams(window.location.search).get('case')
  if (requestedCase) {
    try {
      const detail = await fetchCase(requestedCase)
      const metadata = detail.dataset?.metadata ?? {}
      const caseGraph = metadata.graph
      const caseAlgorithm = metadata.algorithm
      if (!caseGraph || typeof caseGraph !== 'object' || typeof caseAlgorithm !== 'string') throw new Error('案例未提供可运行的图与算法。')
      graph.value = clone(caseGraph as GraphSpec)
      editorVersion.value += 1
      if (algorithms.value.some((item) => item.key === caseAlgorithm)) selectedKey.value = caseAlgorithm
      await nextTick()
      const suppliedParameters = (metadata.parameters && typeof metadata.parameters === 'object' ? metadata.parameters : {}) as Record<string, unknown>
      parameters.value = { ...(selectedAlgorithm.value ? defaultsFor(selectedAlgorithm.value) : {}), ...clone(suppliedParameters) }
      seed.value = typeof metadata.seed === 'number' ? metadata.seed : null
      graphReady.value = false
      caseMessage.value = `已载入案例“${detail.title}”`
    } catch (reason) {
      caseLoadError.value = reason instanceof Error ? reason.message : '无法载入案例实验配置。'
    }
  }
  await historyPromise
})
onBeforeUnmount(() => cancelActiveRun())

function onValidated(value: GraphSpec) { graph.value = value; graphReady.value = true; phase.value = 'idle'; runError.value = '' }
function onInvalid() { graphReady.value = false; phase.value = 'idle' }

async function run() {
  if (!selectedAlgorithm.value || !canRun.value) return
  cancelActiveRun()
  const controller = new AbortController()
  activeRunController = controller
  const algorithm = clone(selectedAlgorithm.value)
  const request: RunRequest = clone({ algorithm: algorithm.key, graph: graph.value, parameters: parameters.value, seed: seed.value })
  runError.value = ''; historyError.value = ''; result.value = null; currentRecord.value = null; compareRecord.value = null
  try {
    const completed = await executeRun(request, { submitRun, fetchRunStatus, fetchRunResult }, (next) => {
      if (activeRunController === controller && !controller.signal.aborted) phase.value = next
    }, {
      signal: controller.signal,
      onSubmitted: (submission) => { if (activeRunController === controller) activeRunId = submission.id },
    })
    if (controller.signal.aborted || activeRunController !== controller) return
    result.value = completed
    const record: HistoryRecord = {
      id: completed.run_id,
      createdAt: new Date().toISOString(),
      algorithm: algorithm.key,
      algorithmName: algorithm.name,
      parameters: request.parameters,
      seed: request.seed ?? null,
      graph: request.graph as GraphSpec,
      result: completed,
    }
    currentRecord.value = record
    try {
      await saveHistory(record)
      records.value = [record, ...records.value.filter((item) => item.id !== record.id)]
    } catch (reason) { historyError.value = reason instanceof Error ? reason.message : '结果已完成，但无法写入本机历史。' }
  } catch (reason) {
    if (reason instanceof DOMException && reason.name === 'AbortError') return
    if (activeRunController === controller) runError.value = reason instanceof Error ? reason.message : '运行失败，请检查输入后重试。'
  } finally {
    if (activeRunController === controller) {
      activeRunController = null
      activeRunId = null
    }
  }
}

async function requestCancellation(runId: string) {
  cancellationRunId.value = runId
  cancellationMessage.value = ''
  cancellationError.value = ''
  cancellationInFlight.value = true
  try {
    await cancelRun(runId)
    cancellationMessage.value = `已取消任务 ${runId}`
  } catch (reason) {
    const detail = reason instanceof Error ? reason.message : '取消请求发送失败'
    cancellationError.value = `任务 ${runId}：${detail}`
  } finally {
    cancellationInFlight.value = false
  }
}

function cancelActiveRun() {
  const runId = activeRunId
  activeRunId = null
  activeRunController?.abort()
  activeRunController = null
  if (runId) void requestCancellation(runId)
}

function retryCancellation() {
  if (cancellationRunId.value && !cancellationInFlight.value) void requestCancellation(cancellationRunId.value)
}

function resetExperiment() {
  cancelActiveRun()
  graph.value = structuredClone(LEARNING_EXAMPLE_GRAPH)
  graphReady.value = false
  if (selectedAlgorithm.value) parameters.value = defaultsFor(selectedAlgorithm.value)
  seed.value = 7; phase.value = 'idle'; runError.value = ''; historyError.value = ''; result.value = null; currentRecord.value = null; compareRecord.value = null; parametersValid.value = true
  editorVersion.value += 1
  parameterVersion.value += 1
}

async function removeRecord(id: string) {
  historyError.value = ''
  try { await deleteHistory(id); records.value = records.value.filter((item) => item.id !== id); if (compareRecord.value?.id === id) compareRecord.value = null }
  catch (reason) { historyError.value = reason instanceof Error ? reason.message : '无法删除本机记录。' }
}
async function clearRecords() {
  historyError.value = ''
  try { await clearHistory(); records.value = []; compareRecord.value = null }
  catch (reason) { historyError.value = reason instanceof Error ? reason.message : '无法清空本机历史。' }
}
function selectComparison(record: HistoryRecord) { if (record.id !== result.value?.run_id) compareRecord.value = record }

async function downloadBundle() {
  if (!currentRecord.value || reportDownloading.value) return
  reportDownloading.value = true
  runError.value = ''
  try {
    const blob = await fetchReportBundle(currentRecord.value.id)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `sna-report-${currentRecord.value.id}.zip`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (reason) {
    runError.value = reason instanceof Error ? reason.message : '无法下载复现包。'
  } finally { reportDownloading.value = false }
}

const categoryName = (key: string) => ({ graph: '图结构', model: '随机模型', centrality: '中心性', community: '社区发现', robustness: '鲁棒性', link: '链接预测', opinion: '意见动力学', dynamic: '动态网络', embedding: '图嵌入', text: '文本建网', export: '图导出' }[key.split('.')[0]] ?? '其他方法')
</script>

<template>
  <div class="lab-view page-shell">
    <header class="lab-intro"><div><p class="eyebrow">OPEN LABORATORY</p><h1>自由实验室</h1></div><p>你的图进入真实算法，而不是演示动画。每次运行记录算法版本、参数、种子与输入哈希；历史只保存在这台设备。</p><button type="button" class="button quiet" @click="resetExperiment">重置整个实验</button></header>

    <div class="lab-workbench">
      <div class="lab-main">
        <p v-if="caseMessage" class="state-message compact" role="status">{{ caseMessage }}；请先校验后运行。</p>
        <p v-if="caseLoadError" class="state-message compact error" role="alert">{{ caseLoadError }}</p>
        <GraphEditor :key="editorVersion" v-model="graph" learning-example :disabled="running" @validated="onValidated" @invalid="onInvalid" />

        <section class="algorithm-picker" aria-labelledby="algorithm-heading">
          <div class="control-heading"><div><p class="eyebrow">REGISTRY</p><h2 id="algorithm-heading">二、选择真实算法</h2></div><span v-if="selectedAlgorithm">v{{ selectedAlgorithm.version }}</span></div>
          <p v-if="registryLoading" class="state-message compact" role="status">正在读取后端算法注册表…</p>
          <p v-else-if="registryError" class="state-message error" role="alert">{{ registryError }}</p>
          <template v-else>
            <label class="algorithm-select">算法<select v-model="selectedKey" :disabled="running || !algorithms.length"><option v-if="!algorithms.length" value="">暂无可用算法</option><option v-for="algorithm in algorithms" :key="algorithm.key" :value="algorithm.key">{{ algorithm.name }}</option></select></label>
            <p v-if="!algorithms.length" class="state-message compact empty">算法注册表当前为空，请联系课程教师配置算法后再运行。</p>
            <div v-if="selectedAlgorithm" class="algorithm-notes"><div><span>{{ categoryName(selectedAlgorithm.key) }}</span><h3>{{ selectedAlgorithm.name }}</h3><p>{{ selectedAlgorithm.description }}</p><p>{{ selectedAlgorithm.explanation }}</p></div><FormulaBlock :formula="selectedAlgorithm.formula" /></div>
            <p v-if="incompatible" class="validation-error" role="alert">当前算法不支持{{ graph.directed ? '有向图' : '无向图' }}，请选择兼容方法或修改图类型。</p>
            <ParameterControls v-if="selectedAlgorithm" :key="`${selectedAlgorithm.key}-${parameterVersion}`" v-model="parameters" :algorithm="selectedAlgorithm" :disabled="running" @validity="parametersValid = $event" />
          </template>
        </section>

        <section class="run-console" aria-labelledby="run-heading">
          <div><p class="eyebrow">RUN & TRACE</p><h2 id="run-heading">三、运行并留下证据链</h2><label>随机种子<input v-model.number="seed" :disabled="running" type="number" step="1" /></label></div>
          <div><RunStatus :phase="phase" :message="runError" /><button type="button" class="button primary run-button" :disabled="!canRun" @click="run">{{ running ? '正在提交…' : '运行真实算法' }}</button><p v-if="!graphReady" class="field-help">先在第一步通过图数据校验。</p></div>
        </section>
        <p v-if="runError" class="validation-error" role="alert">{{ runError }}</p>
        <p v-if="cancellationMessage" class="state-message compact" role="status" aria-label="取消状态">{{ cancellationMessage }}</p>
        <div v-if="cancellationError" class="state-message compact error" role="alert" aria-label="取消错误">
          <p>{{ cancellationError }}</p>
          <button type="button" class="button secondary" :disabled="cancellationInFlight" @click="retryCancellation">
            {{ cancellationInFlight ? '正在重试…' : '重试取消任务' }}
          </button>
        </div>

        <div v-if="result" class="result-actions"><button type="button" class="button secondary" @click="downloadBundle" :disabled="!currentRecord || reportDownloading">{{ reportDownloading ? '正在打包…' : '下载本次复现包' }}</button><p>服务器生成 HTML、JSON、CSV 与 GraphML 完整复现包。</p></div>
        <ResultsPanel v-if="result" :result="result" :current-record="currentRecord" :compare-record="compareRecord" />
      </div>

      <HistoryPanel :records="records" :loading="historyLoading" :error="historyError" :current-run-id="result?.run_id" :active-compare-id="compareRecord?.id" @compare="selectComparison" @remove="removeRecord" @clear="clearRecords" />
    </div>
  </div>
</template>
