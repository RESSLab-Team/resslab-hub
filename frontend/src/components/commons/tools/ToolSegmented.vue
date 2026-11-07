<script setup lang="ts">
// EPFL tool-page segmented control (design: tools.css `.tseg`).
// A bordered row of buttons; the active segment inverts (--fg fill, --bg text)
// so it stays high-contrast in both light and dark mode.
//
// For the keyboard and screen readers it is a radio group: one choice out of
// a few. Tab enters on the checked segment, the arrow keys move the choice.
import { nextTick, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: string
    items: { value: string; text: string }[]
    full?: boolean
    /** Name of the choice, read by screen readers (the visible label next to it). */
    label?: string
  }>(),
  { full: false, label: undefined }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const buttons = ref<HTMLButtonElement[]>([])

/** Only one segment is in the tab order: the checked one, or the first one. */
function tabIndexOf(index: number): number {
  const checked = props.items.findIndex((item) => item.value === props.modelValue)
  return index === (checked === -1 ? 0 : checked) ? 0 : -1
}

const STEPS: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }

async function onKeydown(event: KeyboardEvent): Promise<void> {
  const step = STEPS[event.key]
  if (step === undefined || props.items.length === 0) return
  event.preventDefault()
  const current = props.items.findIndex((item) => item.value === props.modelValue)
  const next = (Math.max(current, 0) + step + props.items.length) % props.items.length
  emit('update:modelValue', props.items[next].value)
  await nextTick()
  buttons.value[next]?.focus()
}
</script>

<template>
  <div
    class="tseg"
    :class="{ 'tseg-full': full }"
    role="radiogroup"
    :aria-label="label"
    @keydown="onKeydown"
  >
    <button
      v-for="(item, index) in items"
      :key="item.value"
      ref="buttons"
      :aria-checked="modelValue === item.value"
      class="tseg-btn"
      :class="{ 'is-active': modelValue === item.value }"
      role="radio"
      type="button"
      :tabindex="tabIndexOf(index)"
      @click="emit('update:modelValue', item.value)"
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
