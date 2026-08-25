<script setup lang="ts">
import cytoscape, { type Core, type ElementDefinition } from 'cytoscape'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { GraphInputSpec, RunOverlay } from '../api/contracts'
import { allowsMotion } from '../accessibility'

const props = defineProps<{ graph: GraphInputSpec; overlay?: RunOverlay | null; label?: string }>()
const container = ref<HTMLDivElement | null>(null)
let instance: Core | null = null

const palette = ['#b34a32', '#2d6f68', '#d39a32', '#5e6d45', '#7b537d', '#28758d']

function elements(): ElementDefinition[] {
  const overlayNodes = new Map((props.overlay?.nodes ?? []).map((item) => [String(item.node ?? item.id), item]))
  const overlayEdges = new Set<string>()
  ;(props.overlay?.edges ?? []).forEach((edge) => {
    if (typeof edge.source !== 'string' || typeof edge.target !== 'string') return
    overlayEdges.add(`${edge.source}\u0000${edge.target}`)
    if (!props.graph.directed) overlayEdges.add(`${edge.target}\u0000${edge.source}`)
  })
  return [
    ...props.graph.nodes.map((node) => {
      const values = overlayNodes.get(node.id)
      const style = props.overlay?.node_styles?.[node.id]
      const community = Number(style?.community ?? 0)
      const value = Number(values?.value ?? values?.opinion ?? 0)
      return {
        data: { id: node.id, label: node.label ?? node.id, value, color: palette[Math.abs(community) % palette.length] },
      }
    }),
    ...props.graph.edges.map((edge, index) => ({
      data: { id: `edge-${index}`, source: edge.source, target: edge.target, weight: edge.weight ?? 1, predicted: overlayEdges.has(`${edge.source}\u0000${edge.target}`) ? 1 : 0 },
    })),
  ]
}

function renderGraph() {
  if (!container.value) return
  instance?.destroy()
  instance = cytoscape({
    container: container.value,
    elements: elements(),
    style: [
      { selector: 'node', style: {
        label: 'data(label)', 'font-size': 12, 'font-family': 'sans-serif', color: '#18231e',
        'background-color': 'data(color)', 'border-width': 2, 'border-color': '#f7f2e8',
        width: 'mapData(value, 0, 1, 28, 48)', height: 'mapData(value, 0, 1, 28, 48)',
        'text-background-color': '#f7f2e8', 'text-background-opacity': 0.86, 'text-background-padding': '3px',
      } },
      { selector: 'edge', style: {
        width: 'mapData(weight, 0, 5, 1, 5)', 'line-color': '#789087', 'target-arrow-color': '#789087',
        'target-arrow-shape': props.graph.directed ? 'triangle' : 'none', 'curve-style': 'bezier', opacity: 0.72,
      } },
      { selector: 'edge[predicted = 1]', style: { 'line-color': '#b34a32', 'target-arrow-color': '#b34a32', 'line-style': 'dashed', width: 4, opacity: 1 } },
    ],
    layout: { name: 'cose', animate: allowsMotion(), animationDuration: 450, randomize: false, fit: true, padding: 28 },
    minZoom: 0.35,
    maxZoom: 2.5,
  })
}

onMounted(renderGraph)
watch(() => [props.graph, props.overlay] as const, renderGraph, { deep: true })
onBeforeUnmount(() => instance?.destroy())
</script>

<template>
  <div ref="container" class="graph-canvas" role="img" :aria-label="label ?? `网络图：${graph.nodes.length} 个节点，${graph.edges.length} 条边`" />
</template>
