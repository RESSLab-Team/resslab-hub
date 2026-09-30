<script setup lang="ts">
import type { MapCategory, MapSite } from '@/backend'
import MapPanel from '@/components/map/MapPanel.vue'
import {
  sumCounts,
  visibleCounts,
  visiblePrograms,
  type Counts,
  type Selection
} from '@/utils/mapSites'
import { mdiChevronUp, mdiCrosshairsGps } from '@mdi/js'
import { computed, ref, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * The compact variant's bottom sheet. Collapsed, it shows the total, the
 * strip and the top categories, with two actions. "List" expands it over the
 * whole map: a side panel would cover the only thing on screen.
 */
const props = defineProps<{
  selection: Selection
  sitesById: Map<string, MapSite>
  hidden: Set<MapCategory>
  /** a short frame: two bars instead of three */
  short: boolean
}>()

const emit = defineEmits<{
  close: []
  back: []
  centre: []
  'select-site': [sid: string]
  highlight: [sid: string | null]
}>()

const { t } = useI18n({ useScope: 'global' })

const expanded = ref(false)
watch(
  () => props.selection.key,
  () => (expanded.value = false)
)

const visibleSites = computed(() => {
  if (props.selection.kind !== 'cluster') return 0
  return props.selection.sids.filter((sid) => {
    const site = props.sitesById.get(sid)
    return site && sumCounts(visibleCounts(site.counts as Counts, props.hidden)) > 0
  }).length
})

const programCount = computed(() => {
  if (props.selection.kind !== 'site') return 0
  const site = props.sitesById.get(props.selection.sid)
  return site ? visiblePrograms(site, props.hidden).length : 0
})

const root = useTemplateRef<HTMLElement>('root')
/** How much of the map the sheet covers, for the map padding. */
defineExpose({ height: () => root.value?.offsetHeight ?? 0 })
</script>

<template>
  <aside ref="root" class="ms" :class="{ 'is-exp': expanded }">
    <map-panel
      :selection="selection"
      :sites-by-id="sitesById"
      :hidden="hidden"
      compact
      :peek="!expanded"
      :peek-bars="short ? 2 : 3"
      @close="emit('close')"
      @collapse="expanded = false"
      @back="emit('back')"
      @centre="emit('centre')"
      @select-site="emit('select-site', $event)"
      @highlight="emit('highlight', $event)"
    />
    <div v-if="!expanded" class="ms-a">
      <button type="button" @click="emit('centre')">
        <v-icon :icon="mdiCrosshairsGps" size="14" />
        {{ selection.kind === 'cluster' ? t('map.zoom_in') : t('map.centre') }}
      </button>
      <button type="button" @click="expanded = true">
        {{
          selection.kind === 'cluster'
            ? t('map.list_sites', { count: visibleSites }, visibleSites)
            : t('map.programs_count', programCount)
        }}
        <v-icon :icon="mdiChevronUp" size="14" />
      </button>
    </div>
  </aside>
</template>

<style scoped>
.ms {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 5;
  max-height: 100%;
  overflow-y: auto;
  background: var(--bg);
  border-top: 1px solid var(--border);
  animation: ms-up 0.2s ease-in-out;
}
.ms::before {
  content: '';
  position: sticky;
  top: 0;
  z-index: 2;
  display: block;
  height: 3px;
  background: var(--primary);
}
.ms.is-exp {
  top: 0;
}
@keyframes ms-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .ms {
    animation: none;
  }
}
.ms-a {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-top: 1px solid var(--border);
}
.ms-a button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 44px;
  border: 0;
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  font-size: 12.5px;
  cursor: pointer;
  transition: background var(--t-fast), color var(--t-fast);
}
.ms-a button + button {
  border-left: 1px solid var(--border);
  font-weight: 600;
}
.ms-a button:hover {
  background: var(--bg-subtle);
  color: var(--primary);
}
</style>
