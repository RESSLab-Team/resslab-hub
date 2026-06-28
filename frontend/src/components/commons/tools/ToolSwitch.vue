<script setup lang="ts">
// EPFL tool-page switch (design: tool-screens.css `.tswitch`).
// A square hairline-bordered track with a square knob (dark when off, white
// when on); the track turns brand-red when on. Brutalist: no pill, no radius.
defineProps<{
  modelValue: boolean
  label?: string
}>()
defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()
</script>

<template>
  <label class="tswitch">
    <span
      class="tswitch-track"
      :class="{ on: modelValue }"
      @click="$emit('update:modelValue', !modelValue)"
    >
      <span class="tswitch-thumb" />
    </span>
    <span v-if="label" class="tswitch-label">{{ label }}</span>
  </label>
</template>

<style scoped>
.tswitch {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}
.tswitch-track {
  width: 40px;
  height: 20px;
  border: 1px solid var(--epfl-control-outline);
  background: var(--bg);
  position: relative;
  transition: background var(--t-base), border-color var(--t-base);
  flex: 0 0 auto;
}
.tswitch-track.on {
  background: var(--epfl-red);
  border-color: var(--epfl-red);
}
.tswitch-thumb {
  position: absolute;
  top: 1px;
  left: 1px;
  width: 16px;
  height: 16px;
  background: var(--epfl-control-fill);
  transition: transform var(--t-base), background var(--t-base);
}
.tswitch-track.on .tswitch-thumb {
  transform: translateX(20px);
  background: #fff;
}
.tswitch-label {
  font-size: 13px;
  color: var(--fg);
}
</style>
