<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import type { GraphInputSpec, GraphSpec } from '../api/contracts'
import { importGraph, validateGraph } from '../api/client'
import { parseGraphText, serializeGraph, stripLearningLabel, validateGraphLocally } from '../lab/graphInput'
import GraphCanvas from './GraphCanvas.vue'

const props = withDefaults(defineProps<{ modelValue: GraphInputSpec; learningExample?: boolean; disabled?: boolean }>(), { learningExample: false, disabled: false })
const emit = defineEmits<{ 'update:modelValue': [value: GraphInputSpec]; validated: [value: GraphSpec]; invalid: [message: string] }>()
const text = ref(serializeGraph(props.modelValue, props.learningExample))
const error = ref('')
const status = ref('')
const preview = ref<GraphInputSpec>(props.modelValue)
const validating = ref(false)
// 说明书 3.2：三类内置布局（FR 力导向 / Circular 环形 / 分层树形）
type LayoutName = 'force' | 'circular' | 'tree'
const layoutName = ref<LayoutName>('force')
const layoutOptions: Array<{ value: LayoutName; label: string }> = [
  { value: 'force', label: 'FR 力导向布局' },
  { value: 'circular', label: 'Circular 环形布局' },
  { value: 'tree', label: '分层树形布局' },
]
let sourceRevision = 0
let activeValidation: AbortController | null = null

watch(() => props.modelValue, (graph) => { preview.value = graph; text.value = serializeGraph(graph, props.learningExample) }, { deep: true })

async function validate() {
  if (props.disabled) return
  activeValidation?.abort()
  const controller = new AbortController()
  const revision = ++sourceRevision
  activeValidation = controller
  error.value = ''; status.value = ''; validating.value = true
  try {
    const parsed = parseGraphText(stripLearningLabel(text.value))
    const issues = validateGraphLocally(parsed)
    if (issues.length) throw new Error(issues.map((issue) => `${issue.path || '图数据'}：${issue.message}`).join('；'))
    preview.value = parsed
    emit('update:modelValue', parsed)
    const response = await validateGraph(parsed, controller.signal)
    if (controller.signal.aborted || revision !== sourceRevision) return
    if (!response.graph) throw new Error('服务器未返回规范化图数据。')
    preview.value = response.graph
    emit('update:modelValue', response.graph)
    emit('validated', response.graph)
    status.value = `校验通过：${response.graph.nodes.length} 个节点，${response.graph.edges.length} 条边。`
  } catch (reason) {
    if (controller.signal.aborted || revision !== sourceRevision || (reason instanceof DOMException && reason.name === 'AbortError')) return
    error.value = reason instanceof Error ? reason.message : '图数据校验失败。'
    emit('invalid', error.value)
  } finally {
    if (revision === sourceRevision) {
      validating.value = false
      if (activeValidation === controller) activeValidation = null
    }
  }
}

function editText(event: Event) {
  activeValidation?.abort(); activeValidation = null; sourceRevision += 1; validating.value = false
  text.value = (event.target as HTMLTextAreaElement).value
  status.value = ''
  error.value = ''
  emit('invalid', '图数据已修改，请重新校验。')
}

async function importFile(event: Event) {
  if (props.disabled) return
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  activeValidation?.abort(); activeValidation = null
  const revision = ++sourceRevision
  const controller = new AbortController()
  activeValidation = controller
  validating.value = true; status.value = ''; error.value = ''
  emit('invalid', '已选择新文件，请重新校验。')
  if (file.size > 20 * 1024 * 1024) {
    error.value = '文件超过 20 MB，请先精简后再导入。'; validating.value = false; activeValidation = null; return
  }
  try {
    const response = await importGraph(file, controller.signal)
    if (controller.signal.aborted || revision !== sourceRevision) return
    if (!response.graph) throw new Error('服务器未返回规范化图数据。')
    preview.value = response.graph
    text.value = serializeGraph(response.graph, props.learningExample)
    emit('update:modelValue', response.graph)
    emit('validated', response.graph)
    status.value = `导入并校验通过：${response.graph.nodes.length} 个节点，${response.graph.edges.length} 条边。`
  } catch (reason) {
    if (controller.signal.aborted || revision !== sourceRevision || (reason instanceof DOMException && reason.name === 'AbortError')) return
    error.value = reason instanceof Error ? reason.message : '图文件导入失败。'
    emit('invalid', error.value)
  } finally {
    if (revision === sourceRevision) {
      validating.value = false
      if (activeValidation === controller) activeValidation = null
    }
  }
}
onBeforeUnmount(() => { sourceRevision += 1; activeValidation?.abort() })
</script>

<template>
  <section class="graph-editor" aria-labelledby="graph-input-heading">
    <div class="control-heading"><div><p class="eyebrow">GRAPH INPUT</p><h2 id="graph-input-heading">一、准备网络</h2></div><label class="file-button" :class="{ disabled }">导入文件<input type="file" :disabled="disabled" accept=".txt,.csv,.xlsx,.json,.graphml,.gexf,text/plain,text/csv,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/graphml+xml,application/gexf+xml" @change="importFile" /></label></div>
    <p class="field-help">粘贴 GraphSpec JSON，或每行输入“起点 终点 [权重]”。示例只是学习起点，不代表算法结论。</p>
    <label class="graph-text-label">粘贴图数据<textarea :value="text" :disabled="disabled" rows="14" spellcheck="false" aria-label="粘贴图数据" @input="editText" /></label>
    <div class="editor-actions"><button type="button" class="button secondary" :disabled="validating || disabled" @click="validate">{{ validating ? '正在校验…' : '校验图数据' }}</button><span>文件安全导入：TXT / CSV / XLSX / JSON / GraphML / GEXF · 最大 20 MB</span></div>
    <p v-if="status" class="validation-success" role="status">{{ status }}</p>
    <p v-if="error" class="validation-error" role="alert">{{ error }}</p>
    <label class="layout-select">可视化布局<select v-model="layoutName" :disabled="disabled" aria-label="选择可视化布局"><option v-for="option in layoutOptions" :key="option.value" :value="option.value">{{ option.label }}</option></select></label>
    <GraphCanvas :graph="preview" :layout="layoutName" label="当前输入网络预览" />
  </section>
</template>
