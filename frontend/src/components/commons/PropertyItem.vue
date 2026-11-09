<script setup lang="ts">
import TextSubscript from '@/components/commons/TextSubscript.vue'
import { displaySymbol, displayUnit, useDictionaryStore } from '@/stores/dictionary'
import { DETAIL_DATABASE_KEY } from '@/utils/detail'
import { computed, inject } from 'vue'

const props = defineProps<{
  name: string
  unit?: string
  mono?: boolean
  /**
   * The record column this row shows. With it, the label gets a tooltip with
   * the column description, symbol and unit from the data dictionary (#330).
   * Leave it out for a row that shows a computed or combined value.
   */
  column?: string
}>()

const database = inject(DETAIL_DATABASE_KEY, undefined)
const dictionary = useDictionaryStore()

/** The dictionary row, only when it has a real description to show. */
const definition = computed(() => {
  if (!props.column || !database?.value) return undefined
  const column = dictionary.columnFor(database.value, props.column)
  const description = column?.description.trim()
  if (!column || !description || description === '-') return undefined
  return { description, symbol: displaySymbol(column), unit: displayUnit(column) }
})
</script>

<template>
  <div class="prop-item">
    <v-tooltip v-if="definition" location="top start" max-width="360" open-delay="150">
      <template #activator="{ props: activator }">
        <span class="prop-name has-definition" tabindex="0" v-bind="activator"
          ><text-subscript :text="props.name"
        /></span>
      </template>
      <span class="prop-def">{{ definition.description }}</span>
      <span v-if="definition.symbol || definition.unit" class="prop-def-meta">
        <text-subscript v-if="definition.symbol" :text="definition.symbol" />
        <template v-if="definition.symbol && definition.unit"> · </template>
        <template v-if="definition.unit">{{ definition.unit }}</template>
      </span>
    </v-tooltip>
    <!-- The name can be a dictionary symbol with <sub>/<sup> (#328). -->
    <span v-else class="prop-name"><text-subscript :text="props.name" /></span>
    <span class="prop-val" :class="{ mono: props.mono }">
      <slot />
      <span v-if="props.unit" class="prop-unit">{{ props.unit }}</span>
    </span>
  </div>
</template>

<style scoped>
/* A defined term: a quiet dotted hairline, no icon on every row. */
.has-definition {
  cursor: help;
  text-decoration: underline dotted var(--border-strong);
  text-underline-offset: 3px;
}
.has-definition:hover,
.has-definition:focus-visible {
  color: var(--fg);
  text-decoration-color: var(--fg-muted);
}
.prop-def {
  display: block;
}
.prop-def-meta {
  display: block;
  margin-top: 4px;
  opacity: 0.75;
}
</style>
