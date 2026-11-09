<script setup lang="ts">
import TextSubscript from '@/components/commons/TextSubscript.vue'
import { displaySymbol, useDictionaryStore } from '@/stores/dictionary'
import { DETAIL_DATABASE_KEY } from '@/utils/detail'
import { computed, inject } from 'vue'

const props = defineProps<{
  name: string
  unit?: string
  mono?: boolean
  /**
   * The record column this row shows. With it, the row gets a tooltip with
   * the column description and symbol from the data dictionary (#330). The
   * unit is already in the row.
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
  return { description, symbol: displaySymbol(column) }
})
</script>

<template>
  <div
    class="prop-item"
    :class="{ 'has-definition': definition }"
    :tabindex="definition ? 0 : undefined"
  >
    <!-- The whole row opens the definition, so the label needs no underline. -->
    <v-tooltip
      v-if="definition"
      activator="parent"
      content-class="prop-tip"
      location="top start"
      max-width="320"
      offset="2"
      open-delay="200"
    >
      <span class="prop-def">{{ definition.description }}</span>
      <span v-if="definition.symbol" class="prop-def-meta">
        <text-subscript :text="definition.symbol" />
      </span>
    </v-tooltip>
    <!-- The name can be a dictionary symbol with <sub>/<sup> (#328). -->
    <span class="prop-name"><text-subscript :text="props.name" /></span>
    <span class="prop-val" :class="{ mono: props.mono }">
      <slot />
      <span v-if="props.unit" class="prop-unit">{{ props.unit }}</span>
    </span>
  </div>
</template>

<style scoped>
.has-definition {
  cursor: help;
}
.has-definition:hover .prop-name,
.has-definition:focus-visible .prop-name {
  color: var(--fg);
}
.has-definition:focus-visible {
  outline: 1px solid var(--border-strong);
  outline-offset: 2px;
}
</style>

<style>
/* The tooltip is teleported out of the drawer, so its chrome is not scoped.
   Same house style as the chart tooltips (plugins/echarts-theme.ts): flat,
   white, hairline, no shadow. */
.v-tooltip > .v-overlay__content.prop-tip {
  background: var(--bg);
  color: var(--fg);
  border: 1px solid var(--border-strong);
  border-radius: 0;
  box-shadow: none;
  padding: 8px 10px;
  font-family: var(--font-sans);
  font-size: 12px;
  line-height: 1.45;
}
.prop-tip .prop-def {
  display: block;
}
.prop-tip .prop-def-meta {
  display: block;
  margin-top: 4px;
  color: var(--fg-muted);
}
</style>
