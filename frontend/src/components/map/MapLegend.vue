<script setup lang="ts">
import type { MapCategory } from '@/backend'
import { MAP_CATEGORIES } from '@/utils/mapCategories'
import { formatCount } from '@/utils/mapSites'
import { useI18n } from 'vue-i18n'

/**
 * The category filter under the map. Click toggles a category, double-click
 * keeps only that one. Full variant: a grid with the counts and "Show all".
 * Compact variant: one row of chips that scrolls sideways.
 */
defineProps<{
  hidden: Set<MapCategory>
  /** tests per category, hidden ones included */
  counts: Record<MapCategory, number>
  compact: boolean
}>()

const emit = defineEmits<{
  toggle: [id: MapCategory]
  only: [id: MapCategory]
  reset: []
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div v-if="compact" class="ml-chips">
    <button v-if="hidden.size > 0" class="ml-chip ml-chip-all" type="button" @click="emit('reset')">
      {{ t('map.all') }}
    </button>
    <button
      v-for="category in MAP_CATEGORIES"
      :key="category.id"
      class="ml-chip"
      :class="{ 'is-off': hidden.has(category.id) }"
      type="button"
      :aria-pressed="!hidden.has(category.id)"
      @click="emit('toggle', category.id)"
      @dblclick="emit('only', category.id)"
    >
      <span
        class="ml-sq"
        :style="hidden.has(category.id) ? undefined : { background: category.color }"
      ></span>
      {{ t(category.labelKey) }}
    </button>
  </div>
  <div v-else class="ml">
    <button
      v-for="category in MAP_CATEGORIES"
      :key="category.id"
      class="ml-lg"
      :class="{ 'is-off': hidden.has(category.id) }"
      type="button"
      :aria-pressed="!hidden.has(category.id)"
      :title="t('map.legend_hint')"
      @click="emit('toggle', category.id)"
      @dblclick="emit('only', category.id)"
    >
      <span
        class="ml-sq"
        :style="hidden.has(category.id) ? undefined : { background: category.color }"
      ></span>
      <span class="ml-l">{{ t(category.labelKey) }}</span>
      <span class="ml-n">{{ formatCount(counts[category.id] ?? 0) }}</span>
    </button>
    <button
      class="ml-lg ml-reset"
      type="button"
      :disabled="hidden.size === 0"
      @click="emit('reset')"
    >
      {{ t('map.show_all') }}
    </button>
  </div>
</template>

<style scoped>
.ml {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  border-top: 1px solid var(--border);
  background: var(--bg);
}
.ml-lg {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  padding: 11px 14px;
  border: 0;
  border-right: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  font-size: 12.5px;
  text-align: left;
  cursor: pointer;
  transition: color var(--t-fast), background var(--t-fast);
}
.ml-lg:hover {
  background: var(--bg-subtle);
}
.ml-lg:focus-visible,
.ml-chip:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: -2px;
}
.ml-sq {
  flex: none;
  width: 11px;
  height: 11px;
  border: 1px solid transparent;
}
.is-off {
  color: var(--fg-subtle);
}
.is-off .ml-sq {
  background: var(--bg);
  border-color: var(--border-strong);
}
.ml-l {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ml-n {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 11px;
  font-feature-settings: 'tnum';
  color: var(--fg-subtle);
}
.ml-reset {
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.ml-reset:disabled {
  color: var(--fg-subtle);
  background: var(--bg);
  cursor: default;
}
.ml-chips {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding: 8px 8px;
  border-top: 1px solid var(--border);
  background: var(--bg);
  scrollbar-width: thin;
}
.ml-chip {
  flex: none;
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 32px;
  padding: 0 11px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  font-size: 12px;
  white-space: nowrap;
  cursor: pointer;
  transition: border-color var(--t-fast), color var(--t-fast);
}
.ml-chip:hover {
  border-color: var(--fg);
}
.ml-chip.is-off {
  color: var(--fg-subtle);
}
.ml-chip-all {
  border-color: var(--fg);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
</style>
