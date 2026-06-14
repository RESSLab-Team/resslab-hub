<script setup lang="ts">
// EPFL tool-page segmented control (design: tools.css `.tseg`).
// A bordered row of buttons; the active segment fills soft-black with white text.
withDefaults(
  defineProps<{
    modelValue: string
    items: { value: string; text: string }[]
    full?: boolean
  }>(),
  { full: false }
)
defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()
</script>

<template>
  <div class="tseg" :class="{ 'tseg-full': full }" role="tablist">
    <button
      v-for="item in items"
      :key="item.value"
      :aria-selected="modelValue === item.value"
      class="tseg-btn"
      :class="{ 'is-active': modelValue === item.value }"
      role="tab"
      type="button"
      @click="$emit('update:modelValue', item.value)"
    >
      {{ item.text }}
    </button>
  </div>
</template>

<style scoped>
.tseg {
  display: inline-flex;
  border: 1px solid var(--border);
  background: var(--bg);
  border-radius: var(--radius);
  overflow: hidden;
}
.tseg-full {
  display: flex;
  width: 100%;
}
.tseg-btn {
  flex: 1;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 14px;
  border: 0;
  background: transparent;
  color: var(--fg-muted);
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--t-fast), color var(--t-fast);
  border-right: 1px solid var(--border);
}
.tseg-btn:last-child {
  border-right: 0;
}
.tseg-btn:hover {
  color: var(--fg);
  background: var(--bg-subtle);
}
.tseg-btn.is-active {
  background: var(--epfl-black);
  color: #fff;
}
</style>
