<script setup lang="ts">
/**
 * The input a column's filter calls for, over a small static distribution of
 * the whole dataset: a checkbox list for repeated values, a histogram brush for
 * numbers and dates, a search box (with the recurring values as shortcuts) for
 * free text.
 *
 * Shared by the filter rail ({@link AutoFilterRow}) and the table's column
 * header menu, so both write the same value grammar into the dashboard's
 * searches: `=value` / value arrays for sets, `lo<<hi` for ranges, raw text
 * for a substring match.
 */
import DateDistributionBrush from '@/components/commons/sliders/DateDistributionBrush.vue'
import DistributionBrush, {
  type BrushSeries
} from '@/components/commons/sliders/DistributionBrush.vue'
import { isBrushDragging } from '@/composables/interactionState'
import type { Value } from '@/utils/common'
import { mapDateToNumber } from '@/utils/date'
import type { FilterDescriptor } from '@/utils/filterProfile'
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    filter: FilterDescriptor
    value?: Value
    /** Where the brush's min/max fields go: flanking the histogram (the rail's
     *  narrow rows) or on a line below it (popovers, where height is cheap). */
    fields?: 'sides' | 'below'
    /** The "n distinct · m missing" footnote. */
    meta?: boolean
  }>(),
  { value: undefined, fields: 'sides', meta: true }
)
const emit = defineEmits<{
  (e: 'update', value?: Value): void
}>()

/** Bars read as data, not chrome — the muted blue the dashboards' charts use. */
const BRUSH_COLOR = '#A4BCE3'

/* ---- value-set filters (categorical, boolean, and the text shortcuts) ---- */

/**
 * The selected values, tolerant of every shape the query state can hold: our
 * own `=value` / array emissions, and the bare values a chart click writes.
 */
const selected = computed<string[]>(() => {
  const value = props.value
  if (value == null) return []
  if (Array.isArray(value)) return value.filter((entry): entry is string => entry !== null)
  const text = String(value)
  if (text.startsWith('=')) return [text.slice(1)]
  if (text.includes(',')) return text.split(',')
  return [text]
})

function isSelected(option: string): boolean {
  // Case-insensitive so a chart's `slab:true` still lights up the `True` box.
  return selected.value.some((entry) => entry.toLowerCase() === option.toLowerCase())
}

function toggleOption(option: string): void {
  const next = isSelected(option)
    ? selected.value.filter((entry) => entry.toLowerCase() !== option.toLowerCase())
    : [...selected.value, option]
  if (next.length === 0) return emit('update', undefined)
  // One value goes as `=value` (exact, not the default substring match); two or
  // more as an array, which the query builder joins into the DSL's value set.
  emit('update', next.length === 1 ? `=${next[0]}` : next)
}

/** Share of the column's largest bucket, for the bar behind each option. */
const optionScale = computed<number>(() =>
  Math.max(1, ...(props.filter.options ?? []).map((option) => option.count))
)
function optionWidth(count: number): string {
  return `${(count / optionScale.value) * 100}%`
}

/* ---- text ---- */

const textValue = computed<string>(() => {
  const value = props.value
  if (value == null) return ''
  const text = String(value)
  return text.startsWith('=') ? text.slice(1) : text
})

function changeText(raw: string): void {
  const text = raw.trim()
  emit('update', text.length > 0 ? text : undefined)
}

/* ---- numeric (the histogram is the input) ---- */

const numericSeries = computed<BrushSeries[]>(() => [
  {
    color: BRUSH_COLOR,
    data: (props.filter.bins ?? []).map(
      (bin) => [(bin[2] + bin[3]) / 2, typeof bin[1] === 'number' ? bin[1] : 0] as [number, number]
    )
  }
])

/** The brush's full extent — the bin edges, so the handles reach the chart ends. */
const numericExtent = computed<[number, number]>(() => {
  const edges = props.filter.binEdges
  if (edges?.length) return [edges[0], edges[edges.length - 1]]
  return [props.filter.min ?? 0, props.filter.max ?? 0]
})

/**
 * Drag resolution: a power of ten giving a few hundred steps across the column,
 * so a ratio spanning 0–0.6 brushes in thousandths while a span of thousands
 * snaps to whole units (a fixed step of 1 could only pick 0 or 1 on the ratio).
 */
const numericStep = computed<number>(() => {
  const [lo, hi] = numericExtent.value
  const span = hi - lo
  return span > 0 ? 10 ** Math.floor(Math.log10(span / 200)) : 1
})

/** Live window during a drag; the parent only hears about the settled value. */
const liveRange = ref<[number, number] | undefined>()

const numericRange = computed<[number, number]>(() => {
  if (liveRange.value) return liveRange.value
  const value = props.value
  if (typeof value === 'string' && value.includes('<<')) {
    const [lo, hi] = value.split('<<', 2)
    return [Number(lo), Number(hi)]
  }
  return numericExtent.value
})

function commitNumeric(next: [number, number]): void {
  const [lo, hi] = numericExtent.value
  // Handles at both ends mean "no filter" — drop the clause rather than sending
  // a range that matches everything.
  if (next[0] <= lo && next[1] >= hi) return emit('update', undefined)
  emit('update', `${next[0]}<<${next[1]}`)
}

function changeNumeric(next: [number, number]): void {
  liveRange.value = next
  // A drag emits on every frame; only the number fields commit immediately (the
  // rail's charts are static, but the table and every dashboard chart re-filter).
  if (!isBrushDragging.value) {
    liveRange.value = undefined
    commitNumeric(next)
  }
}

function endNumericDrag(): void {
  const next = liveRange.value
  liveRange.value = undefined
  if (next) commitNumeric(next)
}

/* ---- date ---- */

const dateSeries = computed<BrushSeries[]>(() => [
  {
    color: BRUSH_COLOR,
    data: (props.filter.options ?? []).map(
      (option) => [mapDateToNumber(option.value), option.count] as [number, number]
    )
  }
])

const liveDate = ref<[string, string] | undefined>()

const dateRange = computed<[string, string]>(() => {
  if (liveDate.value) return liveDate.value
  const value = props.value
  if (typeof value === 'string' && value.includes('<<')) {
    return value.split('<<', 2) as [string, string]
  }
  return [props.filter.dateMin ?? '', props.filter.dateMax ?? '']
})

function commitDate(next: [string, string]): void {
  if (next[0] <= (props.filter.dateMin ?? '') && next[1] >= (props.filter.dateMax ?? '')) {
    return emit('update', undefined)
  }
  emit('update', `${next[0]}<<${next[1]}`)
}

function changeDate(next: [string, string]): void {
  liveDate.value = next
  if (!isBrushDragging.value) {
    liveDate.value = undefined
    commitDate(next)
  }
}

function endDateDrag(): void {
  const next = liveDate.value
  liveDate.value = undefined
  if (next) commitDate(next)
}
</script>

<template>
  <div class="afr-input">
    <!-- Repeated values: the bar behind each row is the distribution. -->
    <div
      v-if="filter.kind === 'categorical' || filter.kind === 'boolean'"
      class="afr-options"
      role="group"
    >
      <label
        v-for="option in filter.options"
        :key="option.value"
        class="afr-option"
        :class="{ on: isSelected(option.value) }"
      >
        <span class="afr-option-bar" :style="{ width: optionWidth(option.count) }" />
        <input
          type="checkbox"
          :checked="isSelected(option.value)"
          @change="toggleOption(option.value)"
        />
        <span class="afr-option-value">{{ option.value }}</span>
        <span class="afr-option-count">{{ option.count.toLocaleString('en-CH') }}</span>
      </label>
    </div>

    <!-- Numbers: drag the histogram, or type exact bounds beside/below it. -->
    <distribution-brush
      v-else-if="filter.kind === 'numeric' && filter.binEdges"
      :bin-edges="filter.binEdges"
      :fields="fields"
      :max="numericExtent[1]"
      :min="numericExtent[0]"
      :model-value="numericRange"
      :series="numericSeries"
      :step="numericStep"
      type="bar"
      @dragend="endNumericDrag"
      @update:model-value="changeNumeric"
    />

    <date-distribution-brush
      v-else-if="filter.kind === 'date' && filter.dateMin && filter.dateMax"
      :fields="fields"
      :max="filter.dateMax"
      :min="filter.dateMin"
      :model-value="dateRange"
      :series="dateSeries"
      type="line"
      @dragend="endDateDrag"
      @update:model-value="changeDate"
    />

    <!-- Free text: too many values to list, so search — with the recurring
         ones offered as shortcuts. -->
    <template v-else-if="filter.kind === 'text'">
      <input
        class="afr-text"
        type="search"
        :placeholder="$t('commons.search')"
        :value="textValue"
        @change="changeText(($event.target as HTMLInputElement).value)"
      />
      <div v-if="filter.options" class="afr-options afr-options-quiet">
        <button
          v-for="option in filter.options"
          :key="option.value"
          class="afr-option"
          type="button"
          @click="changeText(option.value)"
        >
          <span class="afr-option-bar" :style="{ width: optionWidth(option.count) }" />
          <span class="afr-option-value">{{ option.value }}</span>
          <span class="afr-option-count">{{ option.count.toLocaleString('en-CH') }}</span>
        </button>
      </div>
    </template>

    <p v-if="meta" class="afr-meta">
      {{ filter.distinct.toLocaleString('en-CH') }} {{ $t('commons.distinct_values') }}
      <template v-if="filter.missing > 0">
        · {{ filter.missing.toLocaleString('en-CH') }} {{ $t('commons.missing_values') }}
      </template>
    </p>
  </div>
</template>
