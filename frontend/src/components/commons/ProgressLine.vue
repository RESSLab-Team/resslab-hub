<script setup lang="ts">
import { useDelayedBusy } from '@/composables/useDelayedBusy'
import { computed } from 'vue'

/**
 * One line of text for a network wait, with a thin red bar under it.
 *
 * The text shows at once, so the page is never silent. The bar follows
 * `useDelayedBusy`: it does not flash on a cache hit and does not flicker at
 * the end. With `done` and `total` it fills from left to right; without them
 * it marches, the same way the data tables show a load.
 */
const props = defineProps<{
  active: boolean
  label: string
  done?: number
  total?: number
}>()

const showBar = useDelayedBusy(() => props.active)
const determinate = computed(() => props.total !== undefined && props.total > 0)
const fraction = computed(() => {
  if (!determinate.value) return 0
  return Math.min(1, Math.max(0, (props.done ?? 0) / (props.total as number)))
})
</script>

<template>
  <div v-if="active" class="progress-line" role="status" aria-live="polite">
    <p class="progress-label">{{ label }}</p>
    <div
      class="progress-track"
      :class="{ 'is-shown': showBar, 'is-marching': showBar && !determinate }"
      aria-hidden="true"
    >
      <div v-if="determinate" class="progress-fill" :style="{ width: `${fraction * 100}%` }" />
    </div>
  </div>
</template>

<style scoped>
.progress-line {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.progress-label {
  margin: 0;
  font-size: 14px;
  color: var(--fg-muted);
}
.progress-track {
  position: relative;
  height: 2px;
  overflow: hidden;
  background: var(--border);
  opacity: 0;
  transition: opacity 120ms ease;
}
.progress-track.is-shown {
  opacity: 1;
}
.progress-fill {
  height: 100%;
  background: var(--epfl-red);
  transition: width 200ms ease;
}
.progress-track.is-marching::after {
  content: '';
  position: absolute;
  top: 0;
  left: -26%;
  width: 26%;
  height: 100%;
  background: var(--epfl-red);
  animation: progress-march 1s linear infinite;
}
@keyframes progress-march {
  from {
    left: -26%;
  }
  to {
    left: 100%;
  }
}
/* No motion: a static full-width red line still reads as "working". */
@media (prefers-reduced-motion: reduce) {
  .progress-track.is-marching::after {
    animation: none;
    left: 0;
    width: 100%;
  }
  .progress-fill {
    transition: none;
  }
}
</style>
