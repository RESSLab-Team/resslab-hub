<script setup lang="ts">
/**
 * One cell of a `.charts-strip` row: design chart-head (title + hint) above the
 * chart. `quiet` hides the embedded chart's own (empty) v-card-title so the
 * cell head is the only title.
 *
 * When `field` + `searches` are supplied and the cell's field(s) are active in
 * `searches`, the hint is replaced by a clickable "remove filter" affordance
 * that clears those fields — the head-level counterpart to ResetChartButton.
 */
import type { DoubleFields } from '@/composables/chart'
import type { Searches, Value } from '@/utils/common'
import { mdiClose } from '@mdi/js'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    title?: string
    hint?: string
    quiet?: boolean
    field?: string | DoubleFields | string[]
    searches?: Searches
  }>(),
  {
    title: undefined,
    hint: undefined,
    quiet: false,
    field: undefined,
    searches: undefined
  }
)

const emit = defineEmits<{
  (e: 'change:searches', key: string, value?: Value): void
}>()

const fieldKeys = computed<string[]>(() => {
  const f = props.field
  if (!f) return []
  if (typeof f === 'string') return [f]
  return f.map((entry) => (typeof entry === 'string' ? entry : entry.id))
})

const isFiltered = computed<boolean>(() =>
  fieldKeys.value.some((key) => props.searches?.[key] !== undefined)
)

function clearFilter(): void {
  for (const key of fieldKeys.value) emit('change:searches', key, undefined)
}
</script>

<template>
  <div class="chart-cell" :class="{ 'chart-cell--quiet': quiet }">
    <div v-if="title" class="chart-head">
      <h5>{{ title }}</h5>
      <button v-if="isFiltered" type="button" class="info info--clear" @click="clearFilter">
        <v-icon :icon="mdiClose" size="x-small" />
        {{ $t('dashboards.common.remove_filter') }}
      </button>
      <span v-else-if="hint" class="info">{{ hint }}</span>
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
