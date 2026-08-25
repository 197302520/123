<script setup lang="ts">
import { ref, watch } from 'vue'
import type { AlgorithmSpec } from '../api/contracts'
import { defaultsFor } from '../lab/parameters'

const props = withDefaults(defineProps<{ algorithm: AlgorithmSpec; modelValue: Record<string, unknown>; disabled?: boolean }>(), { disabled: false })
const emit = defineEmits<{ 'update:modelValue': [value: Record<string, unknown>]; reset: [value: Record<string, unknown>]; validity: [valid: boolean] }>()
const local = ref<Record<string, unknown>>({ ...props.modelValue })
const errors = ref<Record<string, string>>({})
const clone = (value: Record<string, unknown>) => JSON.parse(JSON.stringify(value)) as Record<string, unknown>

watch(() => props.modelValue, (value) => { local.value = clone(value) }, { deep: true })
watch(() => props.algorithm.key, () => { local.value = defaultsFor(props.algorithm); errors.value = {}; emit('validity', true) })

function change(key: string, value: unknown) {
  local.value = { ...local.value, [key]: value }
  emit('update:modelValue', clone(local.value))
}
const textValue = (event: Event) => (event.target as HTMLInputElement).value
const numericValue = (event: Event) => Number((event.target as HTMLInputElement).value)
const checkedValue = (event: Event) => (event.target as HTMLInputElement).checked
function structuredChange(key: string, type: 'array' | 'object', event: Event) {
  const raw = (event.target as HTMLTextAreaElement).value
  try {
    const value = JSON.parse(raw) as unknown
    const matches = type === 'array' ? Array.isArray(value) : Boolean(value && typeof value === 'object' && !Array.isArray(value))
    if (!matches) throw new Error('type')
    const { [key]: _removed, ...remaining } = errors.value
    errors.value = remaining
    change(key, value)
  } catch {
    errors.value = { ...errors.value, [key]: `${key} 必须是有效的 JSON ${type === 'array' ? '数组' : '对象'}。` }
  }
  emit('validity', !Object.keys(errors.value).length)
}
function reset() {
  local.value = defaultsFor(props.algorithm)
  errors.value = {}
  emit('update:modelValue', clone(local.value))
  emit('reset', clone(local.value))
  emit('validity', true)
}
</script>

<template>
  <section class="parameter-controls" aria-labelledby="parameter-heading">
    <div class="control-heading"><div><p class="eyebrow">PARAMETERS</p><h3 id="parameter-heading">参数设置</h3></div><button type="button" class="text-button" :disabled="disabled" @click="reset">恢复参数默认值</button></div>
    <p v-if="!Object.keys(algorithm.parameters).length" class="state-message compact">这个算法没有可调参数，将直接使用注册表配置。</p>
    <div v-else class="parameter-grid">
      <label v-for="(definition, key) in algorithm.parameters" :key="key" :class="{ checkbox: definition.type === 'boolean', wide: definition.type === 'array' || definition.type === 'object' || key === 'text' }">
        <template v-if="definition.type === 'boolean'"><input type="checkbox" :disabled="disabled" :checked="Boolean(local[key])" @change="change(key, checkedValue($event))" /><span>{{ definition.description }}</span></template>
        <template v-else>
          <span>{{ definition.description }} <code>{{ key }}</code></span>
          <select v-if="definition.choices" :disabled="disabled" :value="String(local[key] ?? '')" @change="change(key, textValue($event))"><option v-for="choice in definition.choices" :key="choice" :value="choice">{{ choice }}</option></select>
          <input v-else-if="definition.type === 'number' || definition.type === 'integer'" type="number" :disabled="disabled" :value="Number(local[key])" :min="definition.minimum" :max="definition.maximum" :step="definition.type === 'integer' ? 1 : 'any'" @input="change(key, numericValue($event))" />
          <textarea v-else-if="definition.type === 'array' || definition.type === 'object'" rows="4" :disabled="disabled" :aria-invalid="Boolean(errors[key])" :aria-describedby="errors[key] ? `parameter-error-${key}` : undefined" :value="JSON.stringify(local[key], null, 2)" @input="structuredChange(key, definition.type, $event)" />
          <textarea v-else-if="key === 'text'" rows="6" :disabled="disabled" :value="String(local[key] ?? '')" @input="change(key, textValue($event))" />
          <input v-else type="text" :disabled="disabled" :value="String(local[key] ?? '')" @input="change(key, textValue($event))" />
          <small v-if="errors[key]" :id="`parameter-error-${key}`" class="validation-error" role="alert">{{ errors[key] }}</small>
        </template>
      </label>
    </div>
  </section>
</template>
