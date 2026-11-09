<script setup lang="ts">
import type { CurationFile } from '@/backend'
import UnitLineChart from '@/components/commons/charts/UnitLineChart.vue'
import ToolSelect from '@/components/commons/tools/ToolSelect.vue'
import ToolSwitch from '@/components/commons/tools/ToolSwitch.vue'
import DataLegend, { type DataLegendItem } from '@/components/curation/DataLegend.vue'
import {
  countFieldsFor,
  curveSourceFor,
  EXISTING_OPACITY,
  EXISTING_WIDTH,
  fetchCurve,
  ghostColor,
  SUBMITTED_COLOR,
  SUBMITTED_WIDTH
} from '@/components/curation/curves'
import { GHOST_CONFIGS } from '@/components/curation/ghost'
import { useDataset } from '@/composables/useDataset'
import { INK } from '@/plugins/echarts-theme'
import { kindForFile } from '@/utils/curation'
import {
  missingUvcColumns,
  uvcCalibrationError,
  uvcModelCurve,
  uvcParametersFrom
} from '@/utils/material'
import { requiredColumns } from '@/utils/timeseries'
import { parseCsv } from '@/utils/csv'
import type { DatabaseId } from '@/utils/navigation'
import { mdiAlertOutline, mdiClose } from '@mdi/js'
import type { LineSeriesOption } from 'echarts'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * Line-chart previews of the time-series files attached to one experiment
 * (prototype `.cp-previewchart` frames), fetched from the submission's PR
 * branch through the backend proxy.
 *
 * Existing specimens drawn from the comparison cohort can be overlaid as grey
 * ghost curves, so a curator sees at a glance whether a submitted response
 * behaves like the experiments it claims to be comparable to.
 */
const props = defineProps<{
  database: DatabaseId
  /** Text of one file: from the pull request, or from the base branch (#253). */
  loadFile: (path: string) => Promise<string>
  files: CurationFile[]
  /** Cohort restriction from the review view; `undefined` = whole database. */
  cohortQuery?: string
  /** The selected experiment's submitted row, keyed by repo column name. */
  cells?: Record<string, string>
}>()

const { t, te, n } = useI18n({ useScope: 'global' })

// The model is the reference the data is judged against, not one more specimen:
// the theme's soft black keeps it clear of both the red submission and the
// muted palette hues the cohort curves take.
const UVC_COLOR = INK
/** Enough curves to see a trend without turning the frame into a hairball. */
const MAX_OVERLAYS = 6
/** The one curve kind the material model can be drawn on. */
const UVC_KIND = 'stress_strain'

interface Preview {
  path: string
  kindKey?: string
  title: string
  xAxisName: string
  yAxisName: string
  rows: number
  /** The x column on its own — the strain history the UVC model runs on. */
  x: number[]
  series: LineSeriesOption[]
}

const previews = ref<Preview[]>([])
const failed = ref<string[]>([])
const loading = ref(false)

function kindLabel(key: string | undefined): string {
  const i18nKey = `contribute.timeseries.kind.${key}`
  return key && te(i18nKey) ? t(i18nKey) : key ?? ''
}

function buildPreview(file: CurationFile, text: string): Preview | null {
  const parsed = parseCsv(text)
  if (parsed.length < 2) return null
  const headers = parsed[0].map((header) => header.trim())
  const kind = kindForFile(props.database, file)
  // Prefer the kind's declared columns; fall back to the first two.
  const wanted = kind?.columns.length ? requiredColumns(kind) : headers.slice(0, 2)
  const xIndex = Math.max(headers.indexOf(wanted[0]), 0)
  const yIndex = wanted.length > 1 ? Math.max(headers.indexOf(wanted[1]), 1) : 1
  const data: number[][] = []
  for (const row of parsed.slice(1)) {
    const x = Number(row[xIndex])
    const y = Number(row[yIndex])
    if (!Number.isNaN(x) && !Number.isNaN(y)) data.push([x, y])
  }
  if (!data.length) return null
  return {
    path: file.path,
    kindKey: kind?.key,
    title: kindLabel(kind?.key),
    xAxisName: headers[xIndex] ?? '',
    yAxisName: headers[yIndex] ?? '',
    rows: parsed.length - 1,
    x: data.map((point) => point[0]),
    series: [
      {
        name: specimenId(file),
        data,
        showSymbol: false,
        lineStyle: { color: SUBMITTED_COLOR, width: SUBMITTED_WIDTH },
        itemStyle: { color: SUBMITTED_COLOR },
        z: 3
      }
    ]
  }
}

function specimenId(file: CurationFile): string {
  return (
    file.experiment_id ?? file.path.slice(file.path.lastIndexOf('/') + 1).replace(/\.csv$/i, '')
  )
}

watch(
  () => [props.loadFile, props.files] as const,
  async ([loadFile, files]) => {
    loading.value = true
    previews.value = []
    failed.value = []
    const next: Preview[] = []
    const errors: string[] = []
    await Promise.all(
      files.map(async (file) => {
        try {
          const text = await loadFile(file.path)
          const preview = buildPreview(file, text)
          if (preview) next.push(preview)
          else errors.push(file.path)
        } catch {
          errors.push(file.path)
        }
      })
    )
    next.sort((a, b) => a.path.localeCompare(b.path))
    previews.value = next
    failed.value = errors
    loading.value = false
  },
  { immediate: true }
)

// ── comparison overlays ────────────────────────────────────────────────────
// Candidates come from the same in-browser dataset the cohort chart uses (the
// module cache dedupes the fetch), gated on the `*_count` column that says the
// specimen actually has this curve.

const config = GHOST_CONFIGS[props.database]
const countFields = countFieldsFor(props.database)
const datasetReady = ref(0)
const dataset =
  config && countFields.length ? useDataset<{ id: string }>(config.key, config.fetchAll) : null
dataset?.ready().then(() => datasetReady.value++)

const overlayIds = ref<string[]>([])

/** Kind keys currently on screen that have an existing-data endpoint. */
const previewedKinds = computed(() =>
  previews.value
    .map((preview) => preview.kindKey)
    .filter((key): key is string => !!key && !!curveSourceFor(props.database, key))
)

/**
 * Cohort specimens holding at least one of the curves on screen, mapped to the
 * kinds they can be drawn on. Submitted ids are excluded — the submission is
 * already the red line.
 */
const candidates = computed<{ id: string; kinds: Set<string> }[]>(() => {
  if (!dataset || !previewedKinds.value.length) return []
  void datasetReady.value
  const matrix = dataset.matrixSync(countFields, props.cohortQuery)
  const ids = (matrix.ids ?? []) as string[]
  const data = (matrix.data ?? []) as unknown as (number | string | null)[][]
  const submitted = new Set(previews.value.map((preview) => preview.series[0]?.name as string))
  const result: { id: string; kinds: Set<string> }[] = []
  ids.forEach((id, index) => {
    if (submitted.has(id)) return
    const kinds = new Set<string>()
    for (const key of previewedKinds.value) {
      const source = curveSourceFor(props.database, key)
      if (!source) continue
      const column = countFields.indexOf(source.countField)
      if (column >= 0 && Number(data[index]?.[column]) > 0) kinds.add(key)
    }
    if (kinds.size) result.push({ id, kinds })
  })
  return result.sort((a, b) => a.id.localeCompare(b.id))
})

const atLimit = computed(() => overlayIds.value.length >= MAX_OVERLAYS)

const pickerItems = computed(() =>
  atLimit.value
    ? []
    : candidates.value
        .filter((candidate) => !overlayIds.value.includes(candidate.id))
        .map((candidate) => ({ title: candidate.id, value: candidate.id }))
)

const pickerValue = ref('')
function addOverlay(id: string): void {
  if (id && !overlayIds.value.includes(id) && overlayIds.value.length < MAX_OVERLAYS) {
    overlayIds.value = [...overlayIds.value, id]
  }
  pickerValue.value = ''
}
function removeOverlay(id: string): void {
  overlayIds.value = overlayIds.value.filter((entry) => entry !== id)
}

/** Fetched overlay curves, keyed `kind:id`. Failures drop out silently. */
const curves = ref<Record<string, number[][]>>({})
watch(
  () => [overlayIds.value, previewedKinds.value] as const,
  async ([ids, kinds]) => {
    await Promise.all(
      ids.flatMap((id) =>
        kinds.map(async (kind) => {
          const key = `${kind}:${id}`
          if (curves.value[key]) return
          const available = candidates.value.find((candidate) => candidate.id === id)
          if (!available?.kinds.has(kind)) return
          try {
            const data = await fetchCurve(props.database, kind, id)
            if (data.length) curves.value = { ...curves.value, [key]: data }
          } catch {
            // One unavailable curve must not break the frame.
          }
        })
      )
    )
  },
  { deep: true }
)

// ── UVC material model ─────────────────────────────────────────────────────
// The submitted row carries its calibrated UVC parameters; run them over the
// submitted strain history and draw the answer on the same frame, exactly like
// the Model feature of the Materials tab (#306). No extra request: the strain
// history is the x column already parsed out of the file.

const uvcParameters = computed(() =>
  props.database === 'cyclic' ? uvcParametersFrom(props.cells ?? {}) : null
)
/** Calibration error, already rendered — two decimals like the dictionary. */
const uvcPhi = computed(() => {
  const phi = props.database === 'cyclic' ? uvcCalibrationError(props.cells ?? {}) : null
  return phi === null ? null : phi.toFixed(2)
})

/** Model responses keyed by file path. Kept apart from `charts` so adding or
 *  removing a cohort curve does not re-run the solver. */
const uvcCurves = computed<Record<string, number[][]>>(() => {
  const parameters = uvcParameters.value
  if (!parameters) return {}
  const result: Record<string, number[][]> = {}
  for (const preview of previews.value) {
    if (preview.kindKey !== UVC_KIND || !preview.x.length) continue
    try {
      result[preview.path] = uvcModelCurve(preview.x, parameters)
    } catch {
      // A strain history the return mapping cannot integrate: skip the curve,
      // the measured data still shows.
    }
  }
  return result
})

const showUvc = ref(true)
/** A stress-strain frame is on screen, so the model is relevant to this row. */
const uvcRelevant = computed(
  () => props.database === 'cyclic' && previews.value.some((p) => p.kindKey === UVC_KIND)
)
/** True once a frame can actually take the model — drives the toggle's row. */
const uvcAvailable = computed(() => uvcRelevant.value && !!uvcParameters.value)
/**
 * Parameters the row is missing, listed for the reviewer rather than left
 * silent: a submission opened before a dictionary rename looks identical to one
 * that simply has no model, and only the column names tell them apart.
 */
const uvcMissing = computed(() =>
  uvcRelevant.value && !uvcParameters.value ? missingUvcColumns(props.cells ?? {}) : []
)
/** Parameters are there but no frame got a curve: the solver gave up. */
const uvcFailed = computed(
  () => uvcAvailable.value && !Object.keys(uvcCurves.value).length && !loading.value
)

/** Previews with the selected cohort curves appended underneath. */
const charts = computed(() =>
  previews.value.map((preview) => {
    if (!preview.kindKey) return { ...preview, ghosts: 0 }
    const overlays: LineSeriesOption[] = []
    overlayIds.value.forEach((id, index) => {
      const data = curves.value[`${preview.kindKey}:${id}`]
      if (!data) return
      const color = ghostColor(index)
      overlays.push({
        name: id,
        data,
        showSymbol: false,
        lineStyle: { color, width: EXISTING_WIDTH, opacity: EXISTING_OPACITY },
        itemStyle: { color, opacity: EXISTING_OPACITY },
        z: 1
      })
    })
    const model = showUvc.value ? uvcCurves.value[preview.path] : undefined
    const uvc: LineSeriesOption[] = model
      ? [
          {
            name: t('curation.preview.uvc_model'),
            data: model,
            showSymbol: false,
            lineStyle: { color: UVC_COLOR, width: 1.4, type: 'dashed' },
            itemStyle: { color: UVC_COLOR },
            z: 2
          }
        ]
      : []
    // Drawing order comes from `z`; this order is the legend's and the
    // tooltip's: the submission first, then its model, then the cohort.
    return {
      ...preview,
      ghosts: overlays.length,
      series: [...preview.series, ...uvc, ...overlays]
    }
  })
)

/** Names the submitted-vs-existing colours (#268); only what the frames draw. */
const legendItems = computed<DataLegendItem[]>(() => {
  const items: DataLegendItem[] = [{ kind: 'submitted', label: t('curation.legend.submitted') }]
  if (showUvc.value && charts.value.some((chart) => !!uvcCurves.value[chart.path])) {
    items.push({ kind: 'model', label: t('curation.preview.uvc_model') })
  }
  if (charts.value.some((chart) => chart.ghosts > 0)) {
    items.push({ kind: 'existing', label: t('curation.legend.existing_compared') })
  }
  return items
})

const fileName = (path: string) => path.slice(path.lastIndexOf('/') + 1)
const empty = computed(() => !loading.value && !previews.value.length && !failed.value.length)
// Kept open while overlays are selected even if a criteria change empties the
// cohort — otherwise the chips would vanish with no way to clear them.
const showPicker = computed(() => !!candidates.value.length || !!overlayIds.value.length)
</script>

<template>
  <section class="preview-section">
    <p class="sech">{{ $t('curation.preview.title') }}</p>

    <p v-if="loading" class="state">{{ $t('curation.preview.loading') }}</p>
    <p v-else-if="empty" class="state">{{ $t('curation.preview.none') }}</p>

    <div v-if="showPicker" class="compare">
      <p class="compare-label">{{ $t('curation.preview.compare_title') }}</p>
      <div class="compare-row">
        <tool-select
          class="compare-select"
          :items="pickerItems"
          :model-value="pickerValue"
          :placeholder="
            atLimit
              ? $t('curation.preview.compare_limit', { count: MAX_OVERLAYS })
              : $t('curation.preview.compare_add')
          "
          @update:model-value="addOverlay"
        />
        <span class="compare-count">
          {{ $t('curation.preview.compare_candidates', { count: candidates.length }) }}
        </span>
      </div>
      <div v-if="overlayIds.length" class="compare-chips">
        <button
          v-for="(id, index) in overlayIds"
          :key="id"
          class="ochip"
          type="button"
          @click="removeOverlay(id)"
        >
          <span class="odot" :style="{ background: ghostColor(index) }" />
          {{ id }}
          <v-icon :icon="mdiClose" size="12" />
        </button>
      </div>
    </div>

    <div v-if="uvcAvailable || uvcMissing.length" class="model">
      <p class="compare-label">{{ $t('curation.preview.uvc_title') }}</p>
      <template v-if="uvcAvailable">
        <div class="compare-row">
          <tool-switch v-model="showUvc" :label="$t('curation.preview.uvc_model')" />
          <span v-if="uvcPhi !== null" class="compare-count">
            {{ $t('curation.preview.uvc_phi', { value: uvcPhi }) }}
          </span>
        </div>
        <p v-if="uvcFailed" class="state">{{ $t('curation.preview.uvc_unavailable') }}</p>
      </template>
      <p v-else class="state">
        {{ $t('curation.preview.uvc_missing', { columns: uvcMissing.join(', ') }) }}
      </p>
    </div>

    <data-legend v-if="charts.length" class="legend" :items="legendItems" />
    <div class="grid">
      <div v-for="chart in charts" :key="chart.path" class="previewchart">
        <div class="ch">
          <span>{{ chart.title }}</span>
          <span>
            {{ n(chart.rows) }} {{ $t('curation.preview.rows') }} · {{ fileName(chart.path) }}
            <template v-if="chart.ghosts">
              · {{ $t('curation.preview.ghosts', { count: chart.ghosts }) }}
            </template>
          </span>
        </div>
        <unit-line-chart
          :aspect-ratio="2"
          :legend-side="false"
          :series="chart.series"
          :x-axis-name="chart.xAxisName"
          :y-axis-name="chart.yAxisName"
        />
      </div>
    </div>

    <p v-for="path in failed" :key="path" class="state error">
      <v-icon :icon="mdiAlertOutline" size="14" />
      {{ $t('curation.preview.unavailable', { file: fileName(path) }) }}
    </p>
  </section>
</template>

<style scoped>
.preview-section {
  margin-top: 32px;
}
.sech {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.state {
  margin: 4px 0;
  font-size: 13.5px;
  color: var(--fg-muted);
}
.state.error {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--epfl-orange);
}

/* ── cohort curve picker ── */
.compare {
  margin-bottom: 16px;
}
.compare-label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-subtle);
  margin: 0 0 8px;
}
.compare-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.compare-select {
  flex: 0 1 320px;
  min-width: 200px;
}
.compare-count {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-subtle);
}
.compare-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 10px;
}
.ochip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 5px 9px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg);
  cursor: pointer;
}
.ochip:hover {
  border-color: var(--epfl-red);
  color: var(--epfl-red);
}

.odot {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  background: var(--border-strong);
}
.model {
  margin-bottom: 16px;
}

/* Frames tile side-by-side once the pane can fit two — on wide screens a
   multi-curve experiment reads as a gallery instead of a scroll of oversized
   charts. */
.legend {
  margin-bottom: 12px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(420px, 100%), 1fr));
  gap: 16px;
}
.previewchart {
  border: 1px solid var(--border);
  padding: 16px 18px;
  min-width: 0;
}
.ch {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 12px;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 2px 12px;
}
.ch > span:last-child {
  min-width: 0;
  overflow-wrap: anywhere;
}
</style>
