<script setup lang="ts">
// EPFL tool-page segmented control (design: tools.css `.tseg`).
// A bordered row of buttons; the active segment inverts (--fg fill, --bg text)
// so it stays high-contrast in both light and dark mode.
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
  /* On a phone the segments wrap to a second row instead of running off the
     screen. The 1px gap shows the border colour behind the buttons, so there
     is a hairline between segments and between rows. */
  flex-wrap: wrap;
  max-width: 100%;
  gap: 1px;
  border: 1px solid var(--border);
  background: var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.tseg-full {
  display: flex;
  width: 100%;
}
.tseg-btn {
  flex: 1 1 auto;
  min-width: 0;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 14px;
  border: 0;
  background: var(--bg);
  color: var(--fg-muted);
  cursor: pointer;
  transition: background var(--t-fast), color var(--t-fast);
}
/* Full width: equal segments, as before. */
.tseg-full .tseg-btn {
  flex-basis: 0;
}
.tseg-btn:hover {
  color: var(--fg);
  background: var(--bg-subtle);
}
.tseg-btn.is-active {
  background: var(--fg);
  color: var(--bg);
}
</style>
