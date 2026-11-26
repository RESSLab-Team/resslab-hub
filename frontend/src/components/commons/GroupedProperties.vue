<script setup lang="ts">
/**
 * Every recorded property of one specimen, grouped and collapsed.
 *
 * The nine detail drawers each hand-pick 10 to 25 columns to highlight, which
 * leaves most of a 70 to 150 column record unreachable from the UI. This renders
 * the whole record underneath those highlights, in the same scientific categories
 * as the filter rail, so nothing is hidden without also burying the drawer under
 * a wall of properties. Every group starts closed: this is the reference section,
 * not the headline.
 */
import PropertyItem from '@/components/commons/PropertyItem.vue'
import {
  displaySymbol,
  displayUnit,
  useDictionaryStore,
  type DictColumn
} from '@/stores/dictionary'
import { fieldDisplay } from '@/utils/contribution'
import { groupBy, type FieldGroupId } from '@/utils/fieldGroups'
import type { DatabaseId } from '@/utils/navigation'
import { formatFloat, missingLabel } from '@/utils/formatter'
import { formatValue } from '@/utils/queryEngine'
import { mdiChevronRight } from '@mdi/js'
import { computed, ref } from 'vue'

const props = defineProps<{
  database: DatabaseId
  /** The specimen model. Typed loosely: the generated API interfaces carry no
   *  index signature, and this reads them by dictionary column name. */
  record: object
}>()

const cells = computed(() => props.record as Record<string, unknown>)

const dictionary = useDictionaryStore()

interface PropertyRow {
  column: DictColumn
  label: string
  isDescription: boolean
  unit?: string
  value: string
}

/** Columns shown with one decimal here (#454). Every other value shows as
 *  stored: this section is the reference. One decimal is about 11 km. */
const ONE_DECIMAL = new Set(['latitude', 'longitude'])

// An empty cell says why it is empty: not reported or not applicable (#427).
function valueText(field: string): string {
  const value = cells.value[field]
  if (value === null || value === undefined) return missingLabel(props.record, field)
  if (ONE_DECIMAL.has(field) && typeof value === 'number') return formatFloat(value, 1)
  return formatValue(value)
}

/** The dictionary description is the label (#454): it is the same kind of
 *  text in every database, with no unit (the unit is next to the value).
 *  With no description, the old label: translation, symbol or column name. */
function labelFor(column: DictColumn): { label: string; isDescription: boolean } {
  const description = column.description.trim()
  if (description && description !== '-') return { label: description, isDescription: true }
  return {
    label: fieldDisplay(props.database, column.name, displaySymbol(column)),
    isDescription: false
  }
}

const groups = computed(() => {
  const rows: PropertyRow[] = dictionary
    .columnsFor(props.database)
    .filter((column) => column.name in cells.value)
    .map((column) => ({
      column,
      ...labelFor(column),
      unit: displayUnit(column),
      value: valueText(column.name)
    }))
  return groupBy(props.database, rows, (row) => row.column).map((group) => ({
    id: group.id,
    rows: group.items
  }))
})

const open = ref<Set<FieldGroupId>>(new Set())

function toggle(id: FieldGroupId): void {
  const next = new Set(open.value)
  if (!next.delete(id)) next.add(id)
  open.value = next
}
</script>

<template>
  <section v-if="groups.length > 0" class="gp">
    <h3 class="cd-section-h">{{ $t('commons.all_recorded_properties') }}</h3>
    <div v-for="group in groups" :key="group.id" class="gp-group">
      <button
        class="gp-head"
        type="button"
        :aria-expanded="open.has(group.id)"
        @click="toggle(group.id)"
      >
        <v-icon
          class="gp-caret"
          :class="{ open: open.has(group.id) }"
          :icon="mdiChevronRight"
          size="14"
        />
        <span class="gp-label">{{ $t(`field_group.${group.id}`) }}</span>
        <span class="gp-count">{{ group.rows.length }}</span>
      </button>
      <div v-if="open.has(group.id)" class="gp-body">
        <property-item
          v-for="row in group.rows"
          :key="row.column.name"
          :name="row.label"
          :unit="row.unit"
          :column="row.column.name"
          :label-is-description="row.isDescription"
        >
          {{ row.value }}
        </property-item>
      </div>
    </div>
  </section>
</template>

<style scoped>
.gp {
  margin-top: 8px;
}
.gp-group {
  border-top: 1px solid var(--border-subtle);
}
.gp-group:last-child {
  border-bottom: 1px solid var(--border-subtle);
}
.gp-head {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 9px 2px;
  background: none;
  border: 0;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  color: var(--fg);
}
.gp-head:hover .gp-label {
  color: var(--epfl-red);
}
.gp-caret {
  flex: 0 0 auto;
  color: var(--fg-subtle);
  transition: transform var(--t-fast);
}
.gp-caret.open {
  transform: rotate(90deg);
}
.gp-label {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.gp-count {
  flex: 0 0 auto;
  font-size: 11px;
  font-feature-settings: 'tnum';
  color: var(--fg-subtle);
}
.gp-body {
  padding-bottom: 8px;
}
</style>
