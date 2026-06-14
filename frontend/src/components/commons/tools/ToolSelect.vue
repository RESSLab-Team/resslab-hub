<script setup lang="ts">
// EPFL tool-page select (design: tools.css `.tselect`).
// A native select restyled with a 1px strong border and a custom chevron.
// Value-based: option values are strings; `placeholder` adds a leading empty
// option for clearable selects (emits '' when chosen).
defineProps<{
  modelValue: string | undefined
  items: { title: string; value: string; disabled?: boolean }[]
  placeholder?: string
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

function onChange(event: Event): void {
  emit('update:modelValue', (event.target as HTMLSelectElement).value)
}
</script>

<template>
  <div class="tselect">
    <select :value="modelValue ?? ''" @change="onChange">
      <option v-if="placeholder" value="">{{ placeholder }}</option>
      <option v-for="item in items" :key="item.value" :disabled="item.disabled" :value="item.value">
        {{ item.title }}
      </option>
    </select>
    <svg fill="none" height="16" viewBox="0 0 24 24" width="16">
      <path
        d="M6 9l6 6 6-6"
        stroke="currentColor"
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
      />
    </svg>
  </div>
</template>

<style scoped>
.tselect {
  position: relative;
}
.tselect select {
  width: 100%;
  font-family: inherit;
  font-size: 14px;
  padding: 10px 36px 10px 12px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg);
  border-radius: var(--radius);
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;
}
.tselect select:focus {
  outline: 2px solid var(--epfl-red);
  outline-offset: -1px;
}
.tselect svg {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: var(--fg-muted);
}
</style>
