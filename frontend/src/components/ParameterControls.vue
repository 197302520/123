<script setup lang="ts">
import { ref, watch } from 'vue'
import type { AlgorithmSpec } from '../api/contracts'
import { defaultsFor } from '../lab/parameters'

const props = defineProps<{ algorithm: AlgorithmSpec; modelValue: Record<string, unknown> }>()
const emit = defineEmits<{ 'update:modelValue': [value: Record<string, unknown>]; reset: [value: Record<string, unknown>] }>()
const local = ref<Record<string, unknown>>({ ...props.modelValue })
const clone = (value: Record<string, unknown>) => JSON.parse(JSON.stringify(value)) as Record<string, unknown>

watch(() => props.modelValue, (value) => { local.value = clone(value) }, { deep: true })
watch(() => props.algorithm.key, () => { local.value = defaultsFor(props.algorithm) })

function change(key: string, value: unknown) {
  local.value = { ...local.value, [key]: value }
  emit('update:modelValue', clone(local.value))
}
const textValue = (event: Event) => (event.target as HTMLInputElement).value
const numericValue = (event: Event) => Number((event.target as HTMLInputElement).value)
const checkedValue = (event: Event) => (event.target as HTMLInputElement).checked
function structuredValue(event: Event, fallback: unknown) {
  try { return JSON.parse((event.target as HTMLTextAreaElement).value) as unknown }
  catch { return fallback }
}
function reset() {
  local.value = defaultsFor(props.algorithm)
  emit('update:modelValue', clone(local.value))
  emit('reset', clone(local.value))
}
</script>

<template>
  <section class="parameter-controls" aria-labelledby="parameter-heading">
    <div class="control-heading"><div><p class="eyebrow">PARAMETERS</p><h3 id="parameter-heading">参数设置</h3></div><button type="button" class="text-button" @click="reset">恢复参数默认值</button></div>
    <p v-if="!Object.keys(algorithm.parameters).length" class="state-message compact">这个算法没有可调参数，将直接使用注册表配置。</p>
    <div v-else class="parameter-grid">
      <label v-for="(definition, key) in algorithm.parameters" :key="key" :class="{ checkbox: definition.type === 'boolean', wide: definition.type === 'array' || definition.type === 'object' || key === 'text' }">
        <template v-if="definition.type === 'boolean'"><input type="checkbox" :checked="Boolean(local[key])" @change="change(key, checkedValue($event))" /><span>{{ definition.description }}</span></template>
        <template v-else>
          <span>{{ definition.description }} <code>{{ key }}</code></span>
          <select v-if="definition.choices" :value="String(local[key] ?? '')" @change="change(key, textValue($event))"><option v-for="choice in definition.choices" :key="choice" :value="choice">{{ choice }}</option></select>
          <input v-else-if="definition.type === 'number' || definition.type === 'integer'" type="number" :value="Number(local[key])" :min="definition.minimum" :max="definition.maximum" :step="definition.type === 'integer' ? 1 : 'any'" @input="change(key, numericValue($event))" />
          <textarea v-else-if="definition.type === 'array' || definition.type === 'object'" rows="4" :value="JSON.stringify(local[key], null, 2)" @change="change(key, structuredValue($event, definition.default))" />
          <textarea v-else-if="key === 'text'" rows="6" :value="String(local[key] ?? '')" @input="change(key, textValue($event))" />
          <input v-else type="text" :value="String(local[key] ?? '')" @input="change(key, textValue($event))" />
        </template>
      </label>
    </div>
  </section>
</template>
