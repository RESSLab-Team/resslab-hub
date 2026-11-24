<script setup lang="ts">
import 'maplibre-gl/dist/maplibre-gl.css'

import type { MapCategory, MapSite } from '@/backend'
import MapLegend from '@/components/map/MapLegend.vue'
import MapPanel from '@/components/map/MapPanel.vue'
import MapSheet from '@/components/map/MapSheet.vue'
import MapTooltip from '@/components/map/MapTooltip.vue'
import { mapApi } from '@/plugins/axios'
import { MAP_CATEGORIES } from '@/utils/mapCategories'
import { COMPACT_SCALE, glyphElement, glyphSize, setGlyphState, truncate } from '@/utils/mapGlyph'
import {
  countsOf,
  formatCount,
  formatLatLng,
  labelFor,
  siteFeatures,
  sumCounts,
  totals,
  visibleCounts,
  visiblePrograms,
  type Counts,
  type Selection
} from '@/utils/mapSites'
import {
  SITES_HIT_LAYER,
  SITES_SOURCE,
  WORLD_BOUNDS,
  buildMapStyle,
  sitesSource
} from '@/utils/mapStyle'
import { mdiCrosshairsGps, mdiMinus, mdiPlus } from '@mdi/js'
import {
  AttributionControl,
  LngLatBounds,
  Map as MapLibre,
  Marker,
  setWorkerUrl,
  type GeoJSONSource
} from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
  useTemplateRef,
  watch
} from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * The home page's world map of the test sites. One square per site (or
 * cluster of sites), its area the number of tests, split by database. The
 * frame decides the variant: below 640px wide it is compact (chips instead of
 * the legend grid, a bottom sheet instead of the side panel).
 */
const { t } = useI18n({ useScope: 'global' })

// Back to the full variant only above 680px, so a width near the edge does
// not flip it at every resize.
const COMPACT_BELOW = 640
const FULL_ABOVE = 680
const TIP_WIDTH = 256

const touch = window.matchMedia('(hover: none)').matches
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
const duration = (ms: number) => (reducedMotion ? 0 : ms)

const root = useTemplateRef<HTMLElement>('root')
const area = useTemplateRef<HTMLElement>('area')
const canvasBox = useTemplateRef<HTMLElement>('canvasBox')
const sheet = useTemplateRef<InstanceType<typeof MapSheet>>('sheet')

const loadState = ref<'loading' | 'ready' | 'error'>('loading')
const noWebgl = ref(false)
const sites = shallowRef<MapSite[]>([])
const skipped = ref(0)
// Replaced on every change, never mutated in place.
const hidden = shallowRef(new Set<MapCategory>())
const selection = shallowRef<Selection | null>(null)
const hlSid = ref<string | null>(null)
const compact = ref(false)
const named = ref(false)
const cursor = ref<{ lat: number; lng: number } | null>(null)
const areaSize = ref({ width: 0, height: 0 })

const sitesById = computed(() => new Map(sites.value.map((site) => [site.sid, site])))
const tot = computed(() => totals(sites.value, hidden.value))
// The biggest site sets the scale of the squares, filter or not: hiding a
// category makes them smaller, which is how the map shows the filter.
const nref = computed(() => Math.max(0, ...sites.value.map((site) => site.n)))

interface MarkerInfo {
  /** c<cluster_id> or s<sid> */
  key: string
  kind: 'site' | 'cluster'
  /** sites only */
  sid: string
  /** clusters only */
  clusterId: number
  /** number of sites */
  count: number
  n: number
  counts: Counts
  size: number
  lngLat: [number, number]
}

interface Hover extends MarkerInfo {
  x: number
  y: number
  /** the first three sites of a cluster, loaded after the hover starts */
  names: string[] | null
}

const hover = shallowRef<Hover | null>(null)

const tip = computed(() => {
  const h = hover.value
  if (!h) return null
  const { width, height } = areaSize.value
  const right = h.x + h.size / 2 + 12
  const left = Math.max(8, right + TIP_WIDTH > width ? h.x - h.size / 2 - 12 - TIP_WIDTH : right)
  // In the lower half the card hangs upwards, so it stays inside the frame.
  const style =
    h.y > height / 2
      ? { left: `${left}px`, bottom: `${Math.max(8, height - h.y - 24)}px` }
      : { left: `${left}px`, top: `${Math.max(8, h.y - 24)}px` }
  if (h.kind === 'site') {
    const label = labelFor({ sid: h.sid })
    const site = sitesById.value.get(h.sid)
    return {
      style,
      kind: h.kind,
      eyebrow: label.known ? `${label.city} · ${label.cc}` : t('map.site'),
      title: label.inst,
      n: h.n,
      counts: h.counts,
      programs: site ? visiblePrograms(site, hidden.value).length : 0
    }
  }
  const rest = h.names ? h.count - h.names.length : 0
  return {
    style,
    kind: h.kind,
    eyebrow: t('map.cluster_eyebrow', { count: h.count }, h.count),
    title: h.names ? h.names.join(', ') + (rest > 0 ? ` + ${rest}` : '') : '…',
    n: h.n,
    counts: h.counts,
    programs: undefined
  }
})

// MapLibre 6 finds its worker next to its own file. Once bundled, that file is
// gone, so give it the worker as a Vite asset. `?worker&url` is the setup from
// the MapLibre docs: Vite bundles the worker as a `.js` file. A plain `?url`
// keeps the `.mjs` name, and our nginx has no MIME type for it.
setWorkerUrl(workerUrl)

let map: MapLibre | null = null
let mapLoaded = false
let resizeObserver: ResizeObserver | null = null
const markers = new Map<string, { marker: Marker; el: HTMLElement; sig: string }>()

function source(): GeoJSONSource | undefined {
  return map?.getSource<GeoJSONSource>(SITES_SOURCE)
}

function clearMarkers() {
  for (const { marker } of markers.values()) marker.remove()
  markers.clear()
}

/** (Re)create the sites source: at load, when the data comes, when the cluster radius changes. */
function addSites() {
  if (!map || !mapLoaded || sites.value.length === 0) return
  if (map.getLayer(SITES_HIT_LAYER.id)) map.removeLayer(SITES_HIT_LAYER.id)
  if (map.getSource(SITES_SOURCE)) map.removeSource(SITES_SOURCE)
  clearMarkers()
  map.addSource(SITES_SOURCE, sitesSource(siteFeatures(sites.value, hidden.value), compact.value))
  map.addLayer(SITES_HIT_LAYER)
}

function isHighlighted(key: string): boolean {
  return hlSid.value !== null && key === `s${hlSid.value}`
}

function buildMarker(info: MarkerInfo): HTMLElement {
  const label = info.kind === 'site' ? labelFor({ sid: info.sid }) : null
  const clusterName = t('map.n_sites', { count: info.count }, info.count)
  const el = glyphElement({
    counts: info.counts,
    n: info.n,
    size: info.size,
    cluster: info.kind === 'cluster',
    name: label ? truncate(label.inst, compact.value ? 16 : 26) : clusterName,
    label: `${label ? label.inst : clusterName}, ${formatCount(info.n)} ${t('map.tests', info.n)}`
  })
  setGlyphState(el, {
    selected: info.key === selection.value?.key,
    highlighted: isHighlighted(info.key)
  })
  if (!touch) {
    el.addEventListener('mouseenter', () => onEnter(info))
    el.addEventListener('mouseleave', () => (hover.value = null))
  }
  el.addEventListener('click', (event) => {
    // Or the map's own click handler clears the selection right away.
    event.stopPropagation()
    pick(info)
  })
  el.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      pick(info)
    }
  })
  return el
}

function wrapLng(lng: number): number {
  return ((((lng + 180) % 360) + 360) % 360) - 180
}

/**
 * The markers are DOM, one per site or cluster the source has in view. Runs
 * on every frame, so it only builds a glyph when its content changed.
 */
function syncMarkers() {
  if (!map || !source() || !map.isSourceLoaded(SITES_SOURCE)) return
  const seen = new Set<string>()
  const scale = compact.value ? COMPACT_SCALE : 1
  for (const feature of map.querySourceFeatures(SITES_SOURCE)) {
    const props = feature.properties
    const cluster = Boolean(props.cluster)
    const key = cluster ? `c${props.cluster_id}` : `s${props.sid}`
    if (seen.has(key) || feature.geometry.type !== 'Point') continue
    seen.add(key)
    const counts = countsOf(props)
    const n = sumCounts(counts)
    const site = cluster ? undefined : sitesById.value.get(String(props.sid))
    const [lng, lat] = feature.geometry.coordinates
    // Near the 180° line the source also gives a cluster shifted by 360° (the
    // tile buffer): bring it back, or it lands on the next copy of the world.
    const lngLat: [number, number] = site ? [site.lng, site.lat] : [wrapLng(lng), lat]
    // After setData a cluster id can come back for another cluster: compare the place too.
    const sig = `${JSON.stringify(counts)}|${lngLat[0].toFixed(3)},${lngLat[1].toFixed(3)}|${scale}`
    const existing = markers.get(key)
    if (existing?.sig === sig) continue
    existing?.marker.remove()
    const info: MarkerInfo = {
      key,
      kind: cluster ? 'cluster' : 'site',
      sid: String(props.sid ?? ''),
      clusterId: Number(props.cluster_id ?? -1),
      count: Number(props.point_count ?? 1),
      n,
      counts,
      size: glyphSize(n, nref.value, scale),
      lngLat
    }
    const el = buildMarker(info)
    const marker = new Marker({ element: el, anchor: 'center' }).setLngLat(lngLat).addTo(map)
    markers.set(key, { marker, el, sig })
  }
  for (const [key, { marker }] of markers) {
    if (seen.has(key)) continue
    marker.remove()
    markers.delete(key)
  }
}

function onEnter(info: MarkerInfo) {
  if (!map) return
  const point = map.project(info.lngLat)
  hover.value = { ...info, x: point.x, y: point.y, names: null }
  if (info.kind !== 'cluster') return
  source()
    ?.getClusterLeaves(info.clusterId, 3, 0)
    .then((leaves) => {
      const current = hover.value
      if (current?.key !== info.key) return
      const names = leaves.map((leaf) => labelFor({ sid: String(leaf.properties?.sid) }).inst)
      hover.value = { ...current, names }
    })
    // The cluster is gone (the map moved): the card keeps its "…".
    .catch(() => undefined)
}

function pick(info: MarkerInfo) {
  hover.value = null
  if (info.kind === 'site') {
    selection.value = { kind: 'site', key: info.key, sid: info.sid, back: null }
    if (compact.value) centreOn(info.lngLat)
    return
  }
  source()
    ?.getClusterLeaves(info.clusterId, Infinity, 0)
    .then((leaves) => {
      const sids = leaves.map((leaf) => String(leaf.properties?.sid))
      selection.value = { kind: 'cluster', key: info.key, sids }
      if (compact.value) centreOn(info.lngLat)
      else zoomTo(sids)
    })
    .catch(() => undefined)
}

interface Padding {
  top: number
  bottom: number
  left: number
  right: number
}

/** What the panel or the sheet covers, so a camera move keeps the sites in view. */
function pad(): Padding {
  const { width, height } = areaSize.value
  const open = selection.value !== null
  if (!compact.value) {
    return { top: 48, bottom: 48, left: 60, right: open ? Math.min(400, width * 0.45) : 60 }
  }
  if (!open) return { top: 28, bottom: 28, left: 28, right: 28 }
  const sheetHeight = sheet.value?.height() || (height < 340 ? 150 : 220)
  return {
    top: 28,
    left: 28,
    right: 28,
    bottom: Math.max(28, Math.min(height - 60, sheetHeight + 16))
  }
}

function zoomTo(sids: string[]) {
  if (!map) return
  const bounds = new LngLatBounds()
  for (const sid of sids) {
    const site = sitesById.value.get(sid)
    if (site) bounds.extend([site.lng, site.lat])
  }
  if (bounds.isEmpty()) return
  map.fitBounds(bounds, { padding: pad(), maxZoom: 8, duration: duration(700) })
}

/**
 * Put a point in the middle of what the panel or sheet leaves visible. An
 * offset, not easeTo's padding: that one stays on the map after the move.
 */
async function centreOn(lngLat: [number, number], zoom?: number) {
  // The sheet has its height once it is rendered.
  await nextTick()
  if (!map) return
  const p = pad()
  map.easeTo({
    center: lngLat,
    ...(zoom === undefined ? {} : { zoom }),
    offset: [(p.left - p.right) / 2, (p.top - p.bottom) / 2],
    duration: duration(500)
  })
}

/** "Centre on site" in the panel, "Zoom in" or "Centre" in the sheet. */
function onCentre() {
  const current = selection.value
  if (!map || !current) return
  if (current.kind === 'cluster') {
    // Once zoomed in the cluster is gone, so is its panel.
    selection.value = null
    zoomTo(current.sids)
    return
  }
  const site = sitesById.value.get(current.sid)
  if (site) centreOn([site.lng, site.lat], Math.max(map.getZoom(), 6))
}

function selectSite(sid: string) {
  const current = selection.value
  const back =
    current?.kind === 'cluster' ? current : current?.kind === 'site' ? current.back : null
  hlSid.value = null
  selection.value = { kind: 'site', key: `s${sid}`, sid, back }
}

function goBack() {
  const current = selection.value
  selection.value = current?.kind === 'site' ? current.back : null
}

function close() {
  selection.value = null
  hlSid.value = null
}

function zoomIn() {
  map?.zoomIn({ duration: duration(300) })
}

function zoomOut() {
  map?.zoomOut({ duration: duration(300) })
}

function resetView() {
  close()
  map?.fitBounds(WORLD_BOUNDS, { padding: compact.value ? 8 : 24, duration: duration(700) })
}

function toggleCategory(id: MapCategory) {
  const next = new Set(hidden.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  hidden.value = next
}

function onlyCategory(id: MapCategory) {
  hidden.value = new Set(MAP_CATEGORIES.map((category) => category.id).filter((x) => x !== id))
}

function showAll() {
  hidden.value = new Set()
}

function isVisible(sid: string): boolean {
  const site = sitesById.value.get(sid)
  return site !== undefined && sumCounts(visibleCounts(site.counts as Counts, hidden.value)) > 0
}

watch(hidden, () => {
  hover.value = null
  source()?.setData(siteFeatures(sites.value, hidden.value))
  // Drop a selection that has nothing left to show.
  const current = selection.value
  if (!current) return
  const sids = current.kind === 'cluster' ? current.sids : [current.sid]
  if (!sids.some(isVisible)) close()
})

watch(compact, (value) => {
  hover.value = null
  if (!map) return
  map.setMinZoom(value ? 0 : 0.4)
  named.value = map.getZoom() >= (value ? 3.8 : 3)
  // A new cluster radius and smaller squares.
  addSites()
})

watch([selection, hlSid], () => {
  for (const [key, { el }] of markers) {
    setGlyphState(el, {
      selected: key === selection.value?.key,
      highlighted: isHighlighted(key)
    })
  }
})

watch(sites, addSites)

function measure() {
  const el = area.value
  if (el) areaSize.value = { width: el.clientWidth, height: el.clientHeight }
}

function onResize() {
  const width = root.value?.clientWidth ?? 0
  if (!compact.value && width < COMPACT_BELOW) compact.value = true
  else if (compact.value && width > FULL_ABOVE) compact.value = false
  measure()
  map?.resize()
}

function createMap(container: HTMLElement) {
  try {
    map = new MapLibre({
      container,
      style: buildMapStyle(),
      center: [20, 20],
      zoom: compact.value ? 0.3 : 1,
      minZoom: compact.value ? 0 : 0.4,
      maxZoom: 11,
      // A flat frame (3:1 on a wide screen, see .map-frame in app.css) is
      // wider than the world at the world view: repeat it rather than leave
      // empty sides.
      renderWorldCopies: true,
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
      // On touch, one finger scrolls the page and two move the map.
      cooperativeGestures: touch
    })
  } catch {
    // MapLibre throws when the browser has no WebGL.
    noWebgl.value = true
    return
  }
  const m = map
  m.touchZoomRotate.disableRotation()
  m.addControl(new AttributionControl({ compact: true }), 'bottom-right')
  m.on('load', () => {
    mapLoaded = true
    m.resize()
    m.fitBounds(WORLD_BOUNDS, { padding: compact.value ? 8 : 24, duration: 0 })
    addSites()
  })
  m.on('render', syncMarkers)
  // With world copies on, MapLibre keeps a marker on the copy nearest its last
  // screen position. After a big resize (the map starts at 400px when its box
  // has no size yet) that can be the wrong copy. New markers take the copy
  // nearest the centre, so build them again.
  m.on('resize', () => {
    clearMarkers()
    syncMarkers()
  })
  m.on('zoom', () => {
    named.value = m.getZoom() >= (compact.value ? 3.8 : 3)
  })
  m.on('movestart', () => (hover.value = null))
  m.on('click', close)
  let frame = 0
  m.on('mousemove', (event) => {
    if (frame) return
    frame = requestAnimationFrame(() => {
      frame = 0
      cursor.value = { lat: event.lngLat.lat, lng: event.lngLat.lng }
    })
  })
  m.on('mouseout', () => {
    cancelAnimationFrame(frame)
    frame = 0
    cursor.value = null
  })
  // Tile errors repeat for every tile: say it once.
  let warned = false
  m.on('error', (event) => {
    if (warned) return
    warned = true
    console.warn('[overview-map]', event.error?.message ?? event)
  })
}

async function load() {
  try {
    const { data } = await mapApi.getMapSites()
    sites.value = data.sites
    skipped.value = data.skipped
    loadState.value = 'ready'
  } catch {
    loadState.value = 'error'
  }
}

onMounted(() => {
  const rootEl = root.value
  const box = canvasBox.value
  if (!rootEl || !box || !area.value) return
  compact.value = rootEl.clientWidth < COMPACT_BELOW
  measure()
  resizeObserver = new ResizeObserver(onResize)
  resizeObserver.observe(rootEl)
  // The legend and the chips differ in height: watch the map area too.
  resizeObserver.observe(area.value)
  createMap(box)
  load()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  clearMarkers()
  map?.remove()
  map = null
})
</script>

<template>
  <div
    ref="root"
    class="om"
    :class="{ 'is-compact': compact }"
    role="region"
    :aria-label="t('map.aria_label')"
    @keydown.esc="close"
  >
    <div ref="area" class="om-area" :class="{ 'is-named': named }">
      <div ref="canvasBox" class="om-map"></div>

      <template v-if="!noWebgl">
        <div class="om-ctrl">
          <button
            type="button"
            :aria-label="t('map.zoom_in')"
            :title="t('map.zoom_in')"
            @click="zoomIn"
          >
            <v-icon :icon="mdiPlus" size="16" />
          </button>
          <button
            type="button"
            :aria-label="t('map.zoom_out')"
            :title="t('map.zoom_out')"
            @click="zoomOut"
          >
            <v-icon :icon="mdiMinus" size="16" />
          </button>
          <button
            v-if="!compact"
            type="button"
            :aria-label="t('map.reset_view')"
            :title="t('map.reset_view')"
            @click="resetView"
          >
            <v-icon :icon="mdiCrosshairsGps" size="14" />
          </button>
        </div>
        <div
          v-if="loadState === 'ready'"
          class="om-crn om-tr"
          :class="{ 'is-shifted': selection && !compact }"
        >
          {{ t('map.n_sites', { count: tot.sites }, tot.sites) }} · {{ formatCount(tot.tests) }}
          {{ t('map.tests', tot.tests) }}
          <template v-if="skipped > 0 && !compact">
            <br />{{ t('map.hidden_tests', { n: formatCount(skipped) }, skipped) }}
          </template>
        </div>
        <div v-if="!compact" class="om-crn om-bl">
          {{ cursor ? formatLatLng(cursor.lat, cursor.lng) : t('map.hint') }}
        </div>
      </template>

      <div v-if="noWebgl || loadState !== 'ready'" class="om-state" role="status">
        {{
          noWebgl
            ? t('map.no_webgl')
            : loadState === 'error'
            ? t('map.load_error')
            : t('map.loading')
        }}
      </div>

      <map-tooltip
        v-if="tip"
        :style="tip.style"
        :kind="tip.kind"
        :eyebrow="tip.eyebrow"
        :title="tip.title"
        :n="tip.n"
        :counts="tip.counts"
        :programs="tip.programs"
      />

      <aside v-if="selection && !compact" :key="selection.key" class="om-panel">
        <map-panel
          :selection="selection"
          :sites-by-id="sitesById"
          :hidden="hidden"
          @close="close"
          @back="goBack"
          @centre="onCentre"
          @select-site="selectSite"
          @highlight="hlSid = $event"
        />
      </aside>
      <map-sheet
        v-if="selection && compact"
        ref="sheet"
        :selection="selection"
        :sites-by-id="sitesById"
        :hidden="hidden"
        :short="areaSize.height < 340"
        @close="close"
        @back="goBack"
        @centre="onCentre"
        @select-site="selectSite"
        @highlight="hlSid = $event"
      />
    </div>

    <map-legend
      v-if="loadState === 'ready'"
      :hidden="hidden"
      :counts="tot.perCategory"
      :compact="compact"
      @toggle="toggleCategory"
      @only="onlyCategory"
      @reset="showAll"
    />
  </div>
</template>

<style scoped>
.om {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--fg);
}
.om-area {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: var(--map-paper);
}
/* Its own stacking context: the markers' z-index stays under the controls,
   the tooltip and the panel. */
.om-map {
  position: absolute;
  inset: 0;
  z-index: 0;
  isolation: isolate;
}
.om-map :deep(.maplibregl-canvas) {
  outline: none;
}

/* The glyph, built by utils/mapGlyph.ts. It sits on the basemap, so it keeps
   the light map colours in dark mode. */
.om-map :deep(.mg) {
  cursor: pointer;
  line-height: 0;
}
/* !important beats the inline z-index glyphElement sets (small above big). */
.om-map :deep(.mg:hover) {
  z-index: 900 !important;
}
.om-map :deep(.mg.is-sel) {
  z-index: 950 !important;
}
.om-map :deep(.mg:focus-visible) {
  outline: 2px solid var(--primary);
  outline-offset: 5px;
}
.om-map :deep(.mg-wrap) {
  position: absolute;
  left: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.om-map :deep(.mg-shadow) {
  position: absolute;
  left: 4px;
  box-sizing: border-box;
  border: 1px solid var(--map-shadow);
  background: var(--map-paper);
}
.om-map :deep(.mg-head) {
  display: flex;
  height: 16px;
}
.om-map :deep(.mg-tab) {
  padding: 0 6px;
  background: var(--map-ink);
  color: var(--map-paper);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
  font-feature-settings: 'tnum';
  white-space: nowrap;
}
.om-map :deep(.mg-name) {
  display: none;
  box-sizing: border-box;
  height: 16px;
  padding: 0 8px;
  border: 1px solid var(--map-ink);
  background: var(--map-paper);
  color: var(--map-ink);
  font-family: var(--font-sans);
  font-size: 10.5px;
  font-weight: 500;
  line-height: 14px;
  letter-spacing: -0.005em;
  white-space: nowrap;
}
.om-area.is-named :deep(.mg-name) {
  display: block;
}
.om-map :deep(.mg-box) {
  position: relative;
  box-sizing: border-box;
  border: 1px solid var(--map-ink);
  background: var(--map-paper);
}
.om-map :deep(.mg-cell) {
  position: absolute;
}
.om-map :deep(.mg-sel) {
  display: none;
  position: absolute;
  inset: -4px;
  border: 1.5px solid var(--primary);
  pointer-events: none;
}
.om-map :deep(.mg.is-sel .mg-sel) {
  display: block;
}
.om-map :deep(.mg.is-hl .mg-sel) {
  display: block;
  border-style: dashed;
}
.om-map :deep(.mg.is-sel .mg-tab) {
  background: var(--primary);
  color: var(--on-primary);
}

/* MapLibre's attribution, squared and in the caption voice. */
.om-map :deep(.maplibregl-ctrl-attrib),
.om-map :deep(.maplibregl-ctrl-attrib.maplibregl-compact),
.om-map :deep(.maplibregl-ctrl-attrib-button) {
  border-radius: 0;
}
.om-map :deep(.maplibregl-ctrl-attrib) {
  font-family: var(--font-mono);
  font-size: 9px;
}

.om-ctrl {
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 4;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--fg);
  background: var(--bg);
}
.om-ctrl button {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 0;
  background: var(--bg);
  color: var(--fg);
  cursor: pointer;
  transition: background var(--t-fast), color var(--t-fast);
}
.om-ctrl button + button {
  border-top: 1px solid var(--border);
}
.om-ctrl button:hover {
  background: var(--bg-subtle);
  color: var(--primary);
}
.is-compact .om-ctrl {
  top: 10px;
  left: 10px;
}
.is-compact .om-ctrl button {
  width: 32px;
  height: 32px;
}

.om-crn {
  position: absolute;
  z-index: 3;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.07em;
  line-height: 1.55;
  text-transform: uppercase;
  font-feature-settings: 'tnum';
  color: var(--map-muted);
  pointer-events: none;
}
.om-tr {
  top: 14px;
  right: 16px;
  text-align: right;
  transition: right 0.2s ease-in-out;
}
/* Beside the open panel (min(376px, 46%) wide). */
.om-tr.is-shifted {
  right: min(392px, 46%);
}
.is-compact .om-tr {
  top: 12px;
  right: 12px;
}
.om-bl {
  bottom: 12px;
  left: 14px;
}

.om-state {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-items: center;
  padding: 24px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  text-align: center;
  color: var(--map-muted);
  pointer-events: none;
}

.om-panel {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 5;
  width: min(376px, 46%);
  overflow-y: auto;
  background: var(--bg);
  border-left: 1px solid var(--border);
  animation: om-in 0.2s ease-in-out;
}
.om-panel::before {
  content: '';
  position: sticky;
  top: 0;
  z-index: 2;
  display: block;
  height: 3px;
  background: var(--primary);
}
@keyframes om-in {
  from {
    opacity: 0;
    transform: translateX(12px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .om-panel {
    animation: none;
  }
  .om-tr {
    transition: none;
  }
}
</style>
