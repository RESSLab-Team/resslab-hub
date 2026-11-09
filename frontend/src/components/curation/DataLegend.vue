<script setup lang="ts">
/**
 * Names the colours of the submitted-vs-existing convention (#268), the same
 * way on the curation review and the contribution preview: red for what was
 * submitted, a faded grey for what is already in the database. The swatches
 * read the semantic tokens, so a palette change lands here by itself.
 */
export interface DataLegendItem {
  /**
   * `submitted` and `existing` are lines on a chart; `submitted-value` and
   * `existing-range` are the vertical rules of the metadata panel; `brushed`
   * is a brushed cohort subset; `model` is the dashed reference curve.
   */
  kind: 'submitted' | 'existing' | 'submitted-value' | 'existing-range' | 'brushed' | 'model'
  label: string
}

defineProps<{ items: DataLegendItem[] }>()
</script>

<template>
  <div class="data-legend">
    <span v-for="item in items" :key="item.kind" class="li">
      <span class="sw" :class="item.kind" aria-hidden="true"></span>
      {{ item.label }}
    </span>
  </div>
</template>

<style scoped>
.data-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}
.li {
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-muted);
}
.sw {
  flex: 0 0 auto;
  width: 16px;
  height: 0;
}
.sw.submitted {
  border-top: 2px solid var(--data-submitted);
}
.sw.existing {
  border-top: 1px solid var(--data-existing);
}
.sw.submitted-value,
.sw.existing-range {
  width: 0;
  height: 12px;
}
.sw.submitted-value {
  border-left: 2px solid var(--data-submitted);
}
.sw.existing-range {
  border-left: 2px solid var(--data-existing);
}
.sw.brushed {
  border-top: 2px solid var(--data-submitted);
  opacity: 0.6;
}
.sw.model {
  border-top: 2px dashed var(--fg);
}
</style>
