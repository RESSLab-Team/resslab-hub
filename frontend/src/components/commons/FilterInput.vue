<script setup lang="ts">
/**
 * The input a column's filter calls for, over the distribution of the rows that
 * pass the other filters (see {@link filterCountsKey}): a checkbox list for
 * repeated values, a histogram brush for numbers and dates, a search box (with
 * the recurring values as shortcuts) for free text.
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
import { publishLive, publishSettle } from '@/composables/crossfilterBus'
import { dashboardQueryKey, withFieldClause } from '@/composables/dashboard'
import { isBrushDragging } from '@/composables/interactionState'
import { filterCountsKey } from '@/composables/useAutoFilters'
import type { Value } from '@/utils/common'
import { mapDateToNumber } from '@/utils/date'
import { staticCounts, type LiveCounts, type LiveOption } from '@/utils/filterCounts'
import type { FilterDescriptor } from '@/utils/filterProfile'
import { computed, inject, ref } from 'vue'

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

// The dashboard's committed query, for the live frames a drag publishes: each
// frame is that query with this column's clause swapped for the drag position
// (see crossfilterBus.ts), so the charts and the table follow the handles
// without a reactive re-render, and the value commits once on pointer-up.
const query = inject(dashboardQueryKey, ref<string | undefined>(undefined))
function publishDrag(value: string | undefined): void {
  publishLive(withFieldClause(query.value, props.filter.key, value))
}

/* ---- what the other filters leave ---- */

const countsFor = inject(filterCountsKey, undefined)

// The committed query, so a drag recounts nothing: its frames go through the bus.
const othersQuery = computed<string | undefined>(() =>
  withFieldClause(query.value, props.filter.key)
)

/** Show the whole-dataset count next to the live one, only when they can differ. */
const narrowed = computed<boolean>(() => countsFor !== undefined && Boolean(othersQuery.value))

const counts = computed<LiveCounts>(() =>
  countsFor ? countsFor(props.filter, othersQuery.value) : staticCounts(props.filter)
)
const liveOptions = computed<LiveOption[]>(() => counts.value.options ?? [])

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

/** Share of the column's largest bucket in the whole dataset, for the bar behind
 *  each option: the scale stays put, so a bar shrinks as the filters narrow. */
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

/** A shortcut picks its exact value, so the rows match the count it shows. A click
 *  on the selected one clears the filter. */
function toggleShortcut(option: string): void {
  emit('update', textValue.value === option ? undefined : `=${option}`)
}

/* ---- numeric (the histogram is the input) ---- */

const numericSeries = computed<BrushSeries[]>(() => [
  {
    color: BRUSH_COLOR,
    data: (counts.value.bins ?? []).map(
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

/** The clause for a window, or undefined when the handles sit at both ends —
 *  "no filter" drops the clause rather than sending a range matching everything. */
function numericValue(next: [number, number]): string | undefined {
  const [lo, hi] = numericExtent.value
  return next[0] <= lo && next[1] >= hi ? undefined : `${next[0]}<<${next[1]}`
}

function commitNumeric(next: [number, number]): void {
  emit('update', numericValue(next))
}

function changeNumeric(next: [number, number]): void {
  // A drag emits on every frame: hold the window locally for the brush and
  // publish it to the bus, so the dashboard follows live without committing.
  // The number fields (no drag) commit at once.
  if (isBrushDragging.value) {
    liveRange.value = next
    publishDrag(numericValue(next))
    return
  }
  liveRange.value = undefined
  commitNumeric(next)
}

// Pointer-up: commit through Vue first, then settle the bus (see DoubleChart) so
// the committed recompute lands with the charts unfrozen. Fires for a no-op
// click too, so nothing can stay frozen.
function endNumericDrag(): void {
  const next = liveRange.value
  liveRange.value = undefined
  if (next) commitNumeric(next)
  publishSettle()
}

/* ---- date ---- */

const dateSeries = computed<BrushSeries[]>(() => [
  {
    color: BRUSH_COLOR,
    data: liveOptions.value.map(
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

function dateValue(next: [string, string]): string | undefined {
  const open = next[0] <= (props.filter.dateMin ?? '') && next[1] >= (props.filter.dateMax ?? '')
  return open ? undefined : `${next[0]}<<${next[1]}`
}

function commitDate(next: [string, string]): void {
  emit('update', dateValue(next))
}

function changeDate(next: [string, string]): void {
  if (isBrushDragging.value) {
    liveDate.value = next
    publishDrag(dateValue(next))
    return
  }
  liveDate.value = undefined
  commitDate(next)
}

function endDateDrag(): void {
  const next = liveDate.value
  liveDate.value = undefined
  if (next) commitDate(next)
  publishSettle()
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
        v-for="option in liveOptions"
        :key="option.value"
        class="afr-option"
        :class="{ on: isSelected(option.value), zero: option.count === 0 }"
      >
        <span class="afr-option-bar" :style="{ width: optionWidth(option.count) }" />
        <input
          type="checkbox"
          :checked="isSelected(option.value)"
          @change="toggleOption(option.value)"
        />
        <span class="afr-option-value">{{ option.value }}</span>
        <span class="afr-option-count">
          {{ option.count.toLocaleString('en-CH')
          }}<span v-if="narrowed" class="afr-option-total">
            / {{ option.total.toLocaleString('en-CH') }}</span
          >
        </span>
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
          :class="{ on: textValue === option.value }"
          type="button"
          :aria-pressed="textValue === option.value"
          @click="toggleShortcut(option.value)"
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
