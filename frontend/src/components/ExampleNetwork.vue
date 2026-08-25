<script setup lang="ts">
import GraphCanvas from './GraphCanvas.vue'
import { LEARNING_EXAMPLE_GRAPH } from '../lab/exampleGraph'
</script>

<template>
  <figure class="example-network">
    <GraphCanvas :graph="LEARNING_EXAMPLE_GRAPH" label="教学示例网络：两个紧密群体由一条弱关系连接" />
    <figcaption><strong>教学示例图</strong> · 两个小群体由一条较弱的桥接关系相连；它用于理解结构，不是算法结果。</figcaption>
  </figure>
</template>
