<script setup lang="ts">
import type { CurationExperiment } from '@/backend'
import {
  displaySymbol,
  displayUnit,
  symbolHtml,
  useDictionaryStore,
  type DictColumn
} from '@/stores/dictionary'
import { fieldLabel } from '@/utils/contribution'
import { isMissing } from '@/utils/curation'
import { groupBy, type FieldGroupId } from '@/utils/fieldGroups'
import type { DatabaseId } from '@/utils/navigation'
import { computed, nextTick, ref } from 'vue'

/**
 * Specimen metadata for the review screen (prototype `.cp-propgrid` style):
 * every column of the repo CSV as a label/value prop row, dictionary-labelled,
 * with unreported required fields highlighted — and, when the existing dataset
 * is loaded, the database's observed range as a subtle ghost hint.
 *
 * Rows are collected into the scientific categories of `utils/fieldGroups.ts`,
 * the same ones the filter rail and the contribution editor use. A group holding
 * a missing required field opens by itself: that is what the reviewer is here for.
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

/** A column the dictionary does not describe still needs a category. */
function dictColumn(name: string): DictColumn {
  return (
    dictionary.columnFor(props.database, name) ?? {
      name,
      description: '',
      symbol: '-',
      unit: '-',
      type: 'String',
      example: '',
      nullable: true
    }
  )
}

const groups = computed(() =>
  groupBy(props.database, rows.value, (row) => dictColumn(row.column)).map((group) => ({
    id: group.id,
    rows: group.items,
    missing: group.items.filter((row) => row.missing && row.required).length
  }))
)

const open = ref<Set<FieldGroupId>>(new Set<FieldGroupId>(['experimental_program_details']))

function isOpen(group: { id: FieldGroupId; missing: number }): boolean {
  return group.missing > 0 || open.value.has(group.id)
}

function toggle(id: FieldGroupId): void {
  const next = new Set(open.value)
  if (!next.delete(id)) next.add(id)
  open.value = next
}

function formatBound(value: number): string {
  return Math.abs(value) >= 1000 ? value.toFixed(0) : String(Number(value.toPrecision(4)))
}

/** Scroll a field into view and flash it — called by the quality-flags rail. */
async function flash(column: string): Promise<void> {
  // Unfold the group first, or the row this points at is not in the DOM yet.
  const group = groups.value.find((entry) => entry.rows.some((row) => row.column === column))
  if (group && !isOpen(group)) toggle(group.id)
  await nextTick()
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
    <div v-for="group in groups" :key="group.id" class="fgroup">
      <button
        class="fgroup-head"
        type="button"
        :aria-expanded="isOpen(group)"
        @click="toggle(group.id)"
      >
        <span class="fgroup-caret" :class="{ open: isOpen(group) }">&rsaquo;</span>
        <span class="fgroup-label">{{ $t(`field_group.${group.id}`) }}</span>
        <span v-if="group.missing > 0" class="fgroup-missing">{{ group.missing }}</span>
        <span class="fgroup-count">{{ group.rows.length }}</span>
      </button>
      <div v-if="isOpen(group)" class="propgrid">
        <div
          v-for="row in group.rows"
          :id="`field-${row.column}`"
          :key="row.column"
          class="prop"
          :title="row.description"
        >
          <span class="pk">
            {{ row.label }}
            <!-- Dictionary symbols carry <sub>/<sup> markup. -->
            <!-- eslint-disable-next-line vue/no-v-html -- sanitised by symbolHtml -->
            <span v-if="row.symbol" class="symbol" v-html="symbolHtml(row.symbol)"></span>
          </span>
          <span class="leader"></span>
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
/* Column count follows the pane width (1 → 4 columns): on wide screens the
   pairs stay compact and more fields are visible at once, instead of two
   columns stretching label and value apart. */
.propgrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0 40px;
}
.fgroup + .fgroup {
  margin-top: 6px;
}
.fgroup-head {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 0;
  background: none;
  border: 0;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  color: var(--fg);
}
.fgroup-head:hover .fgroup-label {
  color: var(--epfl-red);
}
.fgroup-caret {
  flex: 0 0 auto;
  width: 10px;
  color: var(--fg-subtle);
  transition: transform var(--t-fast);
}
.fgroup-caret.open {
  transform: rotate(90deg);
}
.fgroup-label {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.fgroup-count {
  flex: 0 0 auto;
  font-size: 11px;
  font-feature-settings: 'tnum';
  color: var(--fg-subtle);
}
.fgroup-missing {
  flex: 0 0 auto;
  min-width: 16px;
  padding: 0 5px;
  border-radius: 8px;
  background: var(--epfl-red);
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
  text-align: center;
}
.fgroup .propgrid {
  padding-bottom: 10px;
}
.prop {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 13px;
}
.pk {
  color: var(--fg-muted);
}
/* Dotted leader bridging label and value — keeps the pair readable however
   wide the column gets (index-page style, matches the mono microtypography). */
.leader {
  flex: 1;
  min-width: 18px;
  border-bottom: 1px dotted var(--border-strong);
  opacity: 0.55;
  transform: translateY(-3px);
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
