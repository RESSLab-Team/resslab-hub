<script setup lang="ts">
import type { CurationExperiment } from '@/backend'
import { displaySymbol, displayUnit, useDictionaryStore } from '@/stores/dictionary'
import { fieldLabel } from '@/utils/contribution'
import { isMissing } from '@/utils/curation'
import type { DatabaseId } from '@/utils/navigation'
import { computed } from 'vue'

/**
 * Specimen metadata for the review screen: every column of the repo CSV,
 * dictionary-labelled, with unreported required fields highlighted — and, when
 * the existing dataset is loaded, the database's observed range next to each
 * numeric value ("ghost column").
 */
const props = defineProps<{
  database: DatabaseId
  experiment: CurationExperiment
  columns: string[]
  ranges?: Record<string, { min: number; max: number }>
}>()

const dictionary = useDictionaryStore()

interface FieldRow {
  column: string
  label: string
  symbol?: string
  unit?: string
  description?: string
  value: string
  missing: boolean
  required: boolean
  range?: { min: number; max: number }
}

const rows = computed<FieldRow[]>(() =>
  props.columns.map((column) => {
    const dict = dictionary.columnFor(props.database, column)
    const raw = props.experiment.cells[column] ?? ''
    const missing = isMissing(raw)
    return {
      column,
      label: fieldLabel(props.database, column),
      symbol: dict ? displaySymbol(dict) : undefined,
      unit: dict ? displayUnit(dict) : undefined,
      description: dict?.description,
      value: raw.trim(),
      missing,
      required: dict ? !dict.nullable : false,
      range: props.ranges?.[column]
    }
  })
)

const hasRanges = computed(() => rows.value.some((row) => row.range))

function formatBound(value: number): string {
  return Math.abs(value) >= 1000 ? value.toFixed(0) : String(Number(value.toPrecision(4)))
}

/** Scroll a field into view and flash it — called by the quality-flags rail. */
function flash(column: string): void {
  const element = document.getElementById(`field-${column}`)
  if (!element) return
  element.scrollIntoView({ behavior: 'smooth', block: 'center' })
  element.classList.remove('flash')
  // Restart the animation even when the same field is flashed twice in a row.
  void element.offsetWidth
  element.classList.add('flash')
}
defineExpose({ flash })
</script>

<template>
  <div class="tool-card">
    <div class="tool-card-h">{{ $t('curation.metadata.title') }}</div>
    <table class="fields">
      <thead v-if="hasRanges">
        <tr>
          <th>{{ $t('curation.metadata.field') }}</th>
          <th class="val">{{ $t('curation.metadata.value') }}</th>
          <th class="val">{{ $t('curation.metadata.existing_range') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :id="`field-${row.column}`" :key="row.column">
          <td class="label" :title="row.description">
            {{ row.label }}
            <!-- Dictionary symbols carry <sub>/<sup> markup. -->
            <!-- eslint-disable-next-line vue/no-v-html -->
            <span v-if="row.symbol" class="symbol" v-html="row.symbol"></span>
          </td>
          <td class="val">
            <span v-if="row.missing && row.required" class="missing">
              {{ $t('curation.metadata.missing') }}
            </span>
            <span v-else-if="row.missing" class="nr">NR</span>
            <template v-else>
              <span class="value">{{ row.value }}</span>
              <span v-if="row.unit" class="unit">{{ row.unit }}</span>
            </template>
          </td>
          <td v-if="hasRanges" class="val range">
            <template v-if="row.range">
              {{ formatBound(row.range.min) }} – {{ formatBound(row.range.max) }}
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.fields {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
}
.fields th {
  padding: 6px 10px;
  border-bottom: 1px solid var(--border-strong);
  font-size: 11px;
  font-weight: 600;
  text-align: left;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
}
.fields th.val {
  text-align: right;
}
.fields td {
  padding: 6px 10px;
  border-bottom: 1px solid var(--border);
}
.fields tbody tr:last-child td {
  border-bottom: none;
}
.label {
  color: var(--fg-muted);
}
.symbol {
  margin-left: 4px;
  color: var(--fg);
  font-style: italic;
}
.val {
  text-align: right;
  white-space: nowrap;
}
.value {
  font-weight: 600;
}
.unit {
  margin-left: 4px;
  font-size: 12px;
  color: var(--fg-muted);
}
.missing {
  color: var(--epfl-red);
  font-weight: 600;
}
.nr {
  color: var(--fg-muted);
}
.range {
  font-size: 12.5px;
  color: var(--fg-muted);
}
.flash {
  animation: field-flash 1.6s ease-out;
}
@keyframes field-flash {
  0%,
  40% {
    background: color-mix(in srgb, var(--epfl-red) 14%, transparent);
  }
  100% {
    background: transparent;
  }
}
</style>
