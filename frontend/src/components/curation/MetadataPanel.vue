<script setup lang="ts">
import type { CurationExperiment } from '@/backend'
import { displaySymbol, displayUnit, useDictionaryStore } from '@/stores/dictionary'
import { fieldLabel } from '@/utils/contribution'
import { isMissing } from '@/utils/curation'
import type { DatabaseId } from '@/utils/navigation'
import { computed } from 'vue'

/**
 * Specimen metadata for the review screen (prototype `.cp-propgrid` style):
 * every column of the repo CSV as a label/value prop row, dictionary-labelled,
 * with unreported required fields highlighted — and, when the existing dataset
 * is loaded, the database's observed range as a subtle ghost hint.
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
  <section>
    <p class="sech">{{ $t('curation.metadata.title') }}</p>
    <div class="propgrid">
      <div
        v-for="row in rows"
        :id="`field-${row.column}`"
        :key="row.column"
        class="prop"
        :title="row.description"
      >
        <span class="pk">
          {{ row.label }}
          <!-- Dictionary symbols carry <sub>/<sup> markup. -->
          <!-- eslint-disable-next-line vue/no-v-html -->
          <span v-if="row.symbol" class="symbol" v-html="row.symbol"></span>
        </span>
        <span class="pv">
          <span v-if="row.missing && row.required" class="missing">
            {{ $t('curation.metadata.missing') }}
          </span>
          <span v-else-if="row.missing" class="nr">NR</span>
          <template v-else>
            {{ row.value }}<span v-if="row.unit" class="u">{{ row.unit }}</span>
          </template>
          <span v-if="row.range" class="range">
            {{
              $t('curation.metadata.range_hint', {
                min: formatBound(row.range.min),
                max: formatBound(row.range.max)
              })
            }}
          </span>
        </span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.sech {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.propgrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 36px;
}
@media (max-width: 700px) {
  .propgrid {
    grid-template-columns: 1fr;
  }
}
.prop {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 9px 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 13px;
}
.pk {
  color: var(--fg-muted);
}
.symbol {
  margin-left: 4px;
  font-style: italic;
  color: var(--fg);
}
.pv {
  font-feature-settings: 'tnum';
  font-weight: 500;
  text-align: right;
}
.pv .u {
  color: var(--fg-subtle);
  font-weight: 400;
  font-size: 11px;
  margin-left: 3px;
}
.missing {
  color: var(--epfl-red);
  font-weight: 600;
}
.nr {
  color: var(--fg-subtle);
  font-weight: 400;
}
.range {
  display: block;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 400;
  color: var(--fg-subtle);
  margin-top: 2px;
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
