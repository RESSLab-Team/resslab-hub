<script setup lang="ts">
/**
 * EPFL design-system page header for the tool pages (component models, fragility
 * curves), mirroring the dash-head of `DashboardShell.vue`: eyebrow, title, an
 * optional actions slot (e.g. the unit toggle) and a description slot.
 */
defineProps<{
  eyebrow: string
  title: string
}>()
</script>

<template>
  <div class="dash-head">
    <div class="eyebrow" style="margin-bottom: 6px">{{ eyebrow }}</div>
    <div class="dash-head-row">
      <h1 class="dash-title">{{ title }}</h1>
      <div v-if="$slots.actions" class="dash-head-actions">
        <slot name="actions" />
      </div>
    </div>
    <p v-if="$slots.default" class="dash-desc"><slot /></p>
  </div>
</template>
