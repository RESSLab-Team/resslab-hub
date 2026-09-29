<script setup lang="ts">
import type { MapCategory, MapSite } from '@/backend'
import EyebrowText from '@/components/commons/EyebrowText.vue'
import MapMix from '@/components/map/MapMix.vue'
import MapProgramRow from '@/components/map/MapProgramRow.vue'
import {
  formatCount,
  formatLatLng,
  labelFor,
  mergedCounts,
  sumCounts,
  visibleCounts,
  visiblePrograms,
  type ClusterSelection,
  type Counts,
  type Selection
} from '@/utils/mapSites'
import { mdiChevronDown, mdiChevronLeft, mdiClose, mdiCrosshairsGps } from '@mdi/js'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * What the panel (full variant) or the sheet (compact variant) shows for a
 * selection: a cluster lists its sites, a site lists its programs. The
 * container (side panel or bottom sheet) belongs to the parent.
 */
const props = withDefaults(
  defineProps<{
    selection: Selection
    sitesById: Map<string, MapSite>
    hidden: Set<MapCategory>
    /** compact variant: strip instead of treemap, no footer, collapse button */
    compact?: boolean
    /** the collapsed sheet: header and a short mix only */
    peek?: boolean
    /** bar rows in peek mode */
    peekBars?: number
  }>(),
  { compact: false, peek: false, peekBars: 3 }
)

const emit = defineEmits<{
  close: []
  collapse: []
  back: []
  centre: []
  'select-site': [sid: string]
  highlight: [sid: string | null]
}>()

const { t } = useI18n({ useScope: 'global' })

interface Row {
  site: MapSite
  n: number
  label: ReturnType<typeof labelFor>
}

function clusterRows(selection: ClusterSelection): Row[] {
  return selection.sids
    .map((sid) => props.sitesById.get(sid))
    .filter((site): site is MapSite => site !== undefined)
    .map((site) => ({
      site,
      n: sumCounts(visibleCounts(site.counts as Counts, props.hidden)),
      label: labelFor(site)
    }))
    .filter((row) => row.n > 0)
    .sort((a, b) => b.n - a.n)
}

const rows = computed(() =>
  props.selection.kind === 'cluster' ? clusterRows(props.selection) : []
)

const site = computed(() =>
  props.selection.kind === 'site' ? props.sitesById.get(props.selection.sid) ?? null : null
)
const label = computed(() => (site.value ? labelFor(site.value) : null))
const programs = computed(() => (site.value ? visiblePrograms(site.value, props.hidden) : []))

const counts = computed<Counts>(() =>
  site.value
    ? visibleCounts(site.value.counts as Counts, props.hidden)
    : mergedCounts(
        rows.value.map((row) => row.site),
        props.hidden
      )
)
const n = computed(() => sumCounts(counts.value))

const eyebrow = computed(() => {
  if (props.selection.kind === 'cluster') {
    return t('map.cluster_eyebrow', { count: rows.value.length }, rows.value.length)
  }
  if (!site.value || !label.value) return ''
  const place = label.value.known ? `${label.value.city} · ${label.value.cc}` : t('map.site')
  return props.compact ? place : `${place} · ${formatLatLng(site.value.lat, site.value.lng)}`
})

const backCount = computed(() => {
  if (props.selection.kind !== 'site' || !props.selection.back) return 0
  return clusterRows(props.selection.back).length
})

// One program open at a time, none when the selection changes.
const openProgram = ref<string | null>(null)
watch(
  () => props.selection.key,
  () => (openProgram.value = null)
)
const programKey = (p: { category: string; program: string; year?: number | null }) =>
  `${p.category}|${p.program}|${p.year ?? ''}`
function toggle(key: string) {
  openProgram.value = openProgram.value === key ? null : key
}

const treeHeight = computed(() => (Object.keys(counts.value).length > 1 ? 112 : 48))
</script>

<template>
  <div class="mpn" :class="{ 'is-compact': compact }">
    <button
      v-if="selection.kind === 'site' && selection.back"
      class="mpn-back"
      type="button"
      @click="emit('back')"
    >
      <v-icon :icon="mdiChevronLeft" size="14" />
      {{ t('map.cluster_eyebrow', { count: backCount }, backCount) }}
    </button>

    <div class="mpn-h">
      <div class="mpn-h-text">
        <div class="mpn-eye"><eyebrow-text :text="eyebrow" /></div>
        <h3 v-if="selection.kind === 'cluster'" class="mpn-t">
          {{ formatCount(n) }} <span>{{ t('map.tests', n) }}</span>
        </h3>
        <template v-else-if="label">
          <h3 class="mpn-t mpn-t-site">{{ label.inst }}</h3>
          <div class="mpn-sub">
            {{ formatCount(n) }} {{ t('map.tests', n) }} ·
            {{ t('map.programs_count', programs.length) }}
          </div>
        </template>
      </div>
      <div class="mpn-h-actions">
        <button
          v-if="compact && !peek"
          class="mpn-x"
          type="button"
          :aria-label="t('map.collapse')"
          @click="emit('collapse')"
        >
          <v-icon :icon="mdiChevronDown" size="16" />
        </button>
        <button class="mpn-x" type="button" :aria-label="t('map.close')" @click="emit('close')">
          <v-icon :icon="mdiClose" size="16" />
        </button>
      </div>
    </div>

    <div class="mpn-sec">
      <map-mix
        :counts="counts"
        :lead="compact ? 'strip' : 'tree'"
        :tree-height="selection.kind === 'site' ? treeHeight : 132"
        :max="peek ? peekBars : 9"
      />
    </div>

    <template v-if="!peek">
      <template v-if="selection.kind === 'cluster'">
        <div class="mpn-ix-h">
          <span>{{ t('map.sites') }} · {{ rows.length }}</span>
          <span>{{ t('map.tests_heading') }}</span>
        </div>
        <button
          v-for="(row, i) in rows"
          :key="row.site.sid"
          class="mpn-ix-r"
          type="button"
          @click="emit('select-site', row.site.sid)"
          @mouseenter="emit('highlight', row.site.sid)"
          @mouseleave="emit('highlight', null)"
          @focus="emit('highlight', row.site.sid)"
          @blur="emit('highlight', null)"
        >
          <span class="mpn-ix-nn">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="mpn-ix-tt">
            {{ row.label.inst }}
            <span v-if="row.label.known">{{ row.label.city }} · {{ row.label.cc }}</span>
          </span>
          <span class="mpn-ix-n">{{ formatCount(row.n) }}</span>
        </button>
      </template>

      <template v-else>
        <div class="mpn-ix-h">
          <span>{{ t('map.programs') }}</span>
          <span>{{ t('map.specimens') }}</span>
        </div>
        <map-program-row
          v-for="program in programs"
          :key="programKey(program)"
          :program="program"
          :open="openProgram === programKey(program)"
          @toggle="toggle(programKey(program))"
        />
        <div v-if="!compact" class="mpn-foot">
          <button class="mpn-link" type="button" @click="emit('centre')">
            <v-icon :icon="mdiCrosshairsGps" size="14" />
            {{ t('map.centre_on_site') }}
          </button>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.mpn {
  --mp-pad: 22px;
  color: var(--fg);
}
.mpn.is-compact {
  --mp-pad: 16px;
}
.mpn-back {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 14px var(--mp-pad) 0;
  border: 0;
  background: none;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--fg-muted);
  cursor: pointer;
}
.is-compact .mpn-back {
  padding-top: 10px;
}
.mpn-back:hover {
  color: var(--primary);
}
.mpn-h {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 18px var(--mp-pad) 16px;
}
.is-compact .mpn-h {
  padding-top: 12px;
  padding-bottom: 10px;
}
.mpn-h-text {
  min-width: 0;
}
.mpn-h-actions {
  display: flex;
  gap: 6px;
  align-items: flex-start;
}
.mpn-eye {
  font-family: var(--title-eyebrow-font);
  font-size: var(--title-eyebrow-size);
  font-weight: var(--title-eyebrow-weight);
  letter-spacing: var(--title-eyebrow-tracking);
  text-transform: uppercase;
}
.mpn-t {
  margin: 8px 0 0;
  font-size: 30px;
  font-weight: 300;
  line-height: 1.1;
  letter-spacing: -0.015em;
  font-feature-settings: 'tnum';
}
.mpn-t span {
  font-size: 15px;
  color: var(--fg-muted);
}
.mpn-t-site {
  font-size: 24px;
  text-wrap: balance;
}
.is-compact .mpn-t {
  margin-top: 5px;
  font-size: 22px;
}
.is-compact .mpn-t-site {
  font-size: 17px;
}
.mpn-sub {
  margin-top: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-muted);
}
.is-compact .mpn-sub {
  margin-top: 4px;
}
.mpn-x {
  flex: none;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--fg);
  cursor: pointer;
  transition: border-color var(--t-fast), color var(--t-fast);
}
.mpn-x:hover {
  border-color: var(--fg);
  color: var(--primary);
}
.mpn-sec {
  padding: 0 var(--mp-pad) 20px;
}
.is-compact .mpn-sec {
  padding-bottom: 12px;
}
.mpn-ix-h {
  display: flex;
  justify-content: space-between;
  padding: 10px var(--mp-pad);
  border-top: 1px solid var(--fg);
  border-bottom: 1px solid var(--border);
  background: var(--bg-subtle);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--fg-subtle);
}
.is-compact .mpn-ix-h {
  padding-top: 8px;
  padding-bottom: 8px;
}
.mpn-ix-r {
  width: 100%;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: baseline;
  padding: 12px var(--mp-pad);
  border: 0;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: background var(--t-fast);
}
.mpn-ix-r:hover,
.mpn-ix-r:focus-visible {
  background: var(--bg-subtle);
}
.mpn-ix-r:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: -2px;
}
.mpn-ix-nn {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--fg-subtle);
}
.mpn-ix-tt {
  font-size: 14.5px;
  letter-spacing: -0.008em;
  transition: color var(--t-fast);
}
.mpn-ix-r:hover .mpn-ix-tt {
  color: var(--primary);
}
.mpn-ix-tt span {
  display: block;
  margin-top: 4px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--fg-subtle);
}
.mpn-ix-n {
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-feature-settings: 'tnum';
}
.mpn-foot {
  padding: 16px var(--mp-pad) 22px;
}
.mpn-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  border: 0;
  background: none;
  font-size: 12.5px;
  color: var(--fg);
  cursor: pointer;
  transition: color var(--t-fast);
}
.mpn-link:hover {
  color: var(--primary);
}
</style>
