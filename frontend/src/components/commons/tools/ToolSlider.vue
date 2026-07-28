<script setup lang="ts">
// EPFL tool-page slider (design: tools.css `.tslider`).
// Label + value sit above a thin 3px track with a filled portion and
// a ringed thumb — no surrounding box. Colors use --fg/--bg tokens so the
// control inverts correctly in dark mode. Unit conversion (SI/US) is handled
// through `useUnits`.
// Sizing is driven by the `--tsl-*` tokens that tool-pages.css sets per
// VIEWPORT-HEIGHT tier: the model rails stack up to ten of these, so on a short
// laptop viewport they run dense, and on a tall screen they relax back to the
// handoff's original proportions. The fallbacks below (the dense tier) keep the
// control self-contained if it's ever used outside a `.tool-page`.
import { useUnits } from '@/composables/unit'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    modelValue: number
    min: number
    max: number
    step?: number
    unit?: string
    disabled?: boolean
  }>(),
  {
    step: undefined,
    unit: undefined,
    disabled: false
  }
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
}>()

const { ratio, unitLabel } = useUnits(props.unit)

const displayedMin = computed(() => props.min / ratio.value)
const displayedMax = computed(() => props.max / ratio.value)
const displayedValue = computed(() => props.modelValue / ratio.value)
const displayedStep = computed(() =>
  props.step != null ? props.step / ratio.value : (displayedMax.value - displayedMin.value) / 200
)
const fillPercent = computed(() => {
  const span = displayedMax.value - displayedMin.value
  if (span <= 0) return 0
  const pct = ((displayedValue.value - displayedMin.value) / span) * 100
  return Math.max(0, Math.min(100, pct))
})
const valueText = computed(() =>
  displayedValue.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
)
const minText = computed(() =>
  displayedMin.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
)
const maxText = computed(() =>
  displayedMax.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
)

function onInput(event: Event): void {
  emit('update:modelValue', Number((event.target as HTMLInputElement).value) * ratio.value)
}
</script>

<template>
  <div class="tslider" :class="{ 'is-disabled': disabled }">
    <div class="tslider-head">
      <!-- eslint-disable-next-line vue/no-v-html -->
      <span class="tslider-label" v-html="label" />
      <span class="tslider-val"
        >{{ valueText }}<em v-if="unitLabel"> {{ unitLabel }}</em></span
      >
    </div>
    <div class="tslider-track">
      <div class="tslider-fill" :style="{ width: fillPercent + '%' }" />
      <input
        type="range"
        :disabled="disabled"
        :max="displayedMax"
        :min="displayedMin"
        :step="displayedStep"
        :value="displayedValue"
        @input="onInput"
      />
    </div>
    <div class="tslider-ends">
      <span>{{ minText }}</span>
      <span>{{ maxText }}</span>
    </div>
  </div>
</template>

<style scoped>
.tslider.is-disabled {
  opacity: 0.4;
  pointer-events: none;
}
.tslider-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  line-height: 1.15;
  margin-bottom: var(--tsl-head-gap, 2px);
}
.tslider-label {
  font-size: var(--tsl-label-size, 12.5px);
  font-weight: 600;
  font-style: italic; /* math-variable labels read as italic in the handoff */
  color: var(--fg);
  white-space: nowrap;
}
.tslider-label :deep(sub) {
  font-size: 0.65em;
}
.tslider-val {
  font-family: var(--font-sans);
  font-size: var(--tsl-val-size, 12px);
  color: var(--fg);
  font-feature-settings: 'tnum';
  white-space: nowrap;
}
.tslider-val em {
  color: var(--fg-subtle);
  font-style: normal;
  margin-left: 3px;
  font-size: 0.8em;
}
.tslider-track {
  position: relative;
  height: var(--tsl-track-h, 16px);
  display: flex;
  align-items: center;
}
.tslider-track::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--bg-muted);
  border-radius: 2px;
}
.tslider-fill {
  position: absolute;
  left: 0;
  height: 3px;
  background: var(--epfl-red); /* handoff: filled portion is brand red (value = active) */
  border-radius: 2px;
  pointer-events: none;
}
/* min / max end labels under the track (handoff .tslider-ends) */
.tslider-ends {
  display: flex;
  justify-content: space-between;
  margin-top: var(--tsl-ends-gap, -1px);
  font-family: var(--font-sans);
  font-size: var(--tsl-ends-size, 9px);
  line-height: 1.1;
  color: var(--fg-subtle);
  font-feature-settings: 'tnum';
}
.tslider-track input[type='range'] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  background: transparent;
  margin: 0;
  position: relative;
  z-index: 1;
  height: var(--tsl-track-h, 16px);
  cursor: pointer;
}
.tslider-track input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: var(--tsl-thumb, 12px);
  height: var(--tsl-thumb, 12px);
  border-radius: 50%; /* circular knob kept per logged deviation */
  background: var(--bg);
  border: 2px solid var(--epfl-red); /* handoff: red-ringed thumb */
  cursor: pointer;
  transition: border-color var(--t-fast);
}
.tslider-track input[type='range']::-webkit-slider-thumb:hover {
  border-color: var(--epfl-red-dark);
}
.tslider-track input[type='range']::-moz-range-thumb {
  width: var(--tsl-thumb, 12px);
  height: var(--tsl-thumb, 12px);
  border-radius: 50%;
  background: var(--bg);
  border: 2px solid var(--epfl-red);
  cursor: pointer;
}
.tslider-track input[type='range']:focus-visible::-webkit-slider-thumb {
  box-shadow: var(--focus-ring);
}
</style>
