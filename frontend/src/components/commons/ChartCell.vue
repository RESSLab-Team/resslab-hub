<script setup lang="ts">
/**
 * One cell of a `.charts-strip` row: design chart-head (title + hint) above the
 * chart. `quiet` hides the embedded chart's own (empty) v-card-title so the
 * cell head is the only title.
 */
withDefaults(
  defineProps<{
    title?: string
    hint?: string
    quiet?: boolean
  }>(),
  {
    title: undefined,
    hint: undefined,
    quiet: false
  }
)
</script>

<template>
  <div class="chart-cell" :class="{ 'chart-cell--quiet': quiet }">
    <div v-if="title" class="chart-head">
      <h5>{{ title }}</h5>
      <span v-if="hint" class="info">{{ hint }}</span>
    </div>
    <div class="chart-body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.chart-cell--quiet :deep(.v-card-title) {
  display: none;
}
.chart-cell :deep(.v-card) {
  border: 0 !important;
}
</style>
