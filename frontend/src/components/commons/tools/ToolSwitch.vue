<script setup lang="ts">
// EPFL tool-page switch (design: tool-screens.css `.tswitch`).
// A rounded pill track that turns brand-red when on, with a round white thumb —
// toggles stay round even in the otherwise-square brutalist UI.
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
  width: 38px;
  height: 20px;
  border-radius: 10px;
  /* Off state via a token that flips: recedes in dark instead of glowing light */
  background: var(--border);
  position: relative;
  transition: background var(--t-base);
  flex: 0 0 auto;
}
.tswitch-track.on {
  background: var(--epfl-red);
}
.tswitch-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  transition: transform var(--t-base);
  box-shadow: var(--shadow-sm);
}
.tswitch-track.on .tswitch-thumb {
  transform: translateX(18px);
}
.tswitch-label {
  font-size: 13px;
  color: var(--fg);
}
</style>
