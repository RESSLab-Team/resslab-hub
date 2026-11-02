<script setup lang="ts">
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { GHOST_CONFIGS, isEmptyBrush, requestFieldsFor } from '@/components/curation/ghost'
import type { ParallelSelection } from '@/composables/chart'
import ToolSwitch from '@/components/commons/tools/ToolSwitch.vue'
import { useDataset } from '@/composables/useDataset'
import { CONTRIBUTION_DATABASES, fieldLabel } from '@/utils/contribution'
import { cellValue, isMissing, type ReviewBatch } from '@/utils/curation'
import type { DatabaseId } from '@/utils/navigation'
import { mdiAccountGroupOutline, mdiAlertOutline, mdiInformationOutline } from '@mdi/js'
import { computed, ref, watch } from 'vue'

/**
 * Ghost mode (prototype "comparison with similar experiments" section): the
 * submitted specimen(s) drawn in red over the existing database (grey ghost
 * lines) on the same parallel-coordinates axes as the public dashboard,
 * introduced by a cohort banner that spells out the like-for-like criteria.
 *
 * The chart is also the cohort's second filter: brushing an axis narrows the
 * cohort that the count and the test-data overlays below draw from, without
 * narrowing the chart itself — the brush origin keeps showing the criteria
 * cohort so the bands stay meaningful (the dashboards' self-exclusion idiom).
 * "Zoom to selection" is what redraws the axes on the brushed rows.
 */
const props = defineProps<{
  database: DatabaseId
  detail: ReviewBatch
  selectedUid: number
  /** Criteria the curator has switched on (owned by the review view). */
  fields: string[]
  restrict: boolean
  /** What the criteria alone compile to — `undefined` = the whole database. */
  criteriaQuery?: string
  /** Criteria narrowed by the brush: what the rest of the review screen uses. */
  cohortQuery?: string
  /** Committed brush, owned by the review view (it feeds the data preview). */
  brush: ParallelSelection | null
}>()

const emit = defineEmits<{
  (e: 'update:fields', value: string[]): void
  (e: 'update:restrict', value: boolean): void
  (e: 'update:brush', value: ParallelSelection | null): void
}>()

const config = GHOST_CONFIGS[props.database]

const state = ref<'loading' | 'ready' | 'error'>('loading')
const dataset = config ? useDataset<{ id: string }>(config.key, config.fetchAll) : null

// One-shot readiness: the dataset is cached for the session, so this resolves
// instantly on revisits (and pre-warms the public dashboard's charts).
const readyTick = ref(0)
dataset
  ?.ready()
  .then(() => {
    state.value = 'ready'
    readyTick.value++
  })
  .catch(() => {
    state.value = 'error'
  })

const restrictModel = computed({
  get: () => props.restrict,
  set: (value: boolean) => emit('update:restrict', value)
})

const selected = computed(
  () => props.detail.experiments[props.selectedUid] ?? props.detail.experiments[0]
)

interface Candidate {
  field: string
  label: string
  value: string
  /** Not reported by this specimen — nothing to match on, so not selectable. */
  missing: boolean
  active: boolean
}

/**
 * Every field the curator may use as a similarity criterion, with the selected
 * specimen's value. Fields the specimen leaves at NR stay visible but inert, so
 * it is obvious *why* a criterion cannot be applied.
 */
const candidates = computed<Candidate[]>(() => {
  if (!config || !selected.value) return []
  return config.cohortCandidates.map((field) => {
    const missing = isMissing(selected.value.cells[field])
    return {
      field,
      label: fieldLabel(props.database, field),
      value: (selected.value.cells[field] ?? '').trim(),
      missing,
      active: !missing && props.fields.includes(field)
    }
  })
})

function toggle(candidate: Candidate): void {
  if (candidate.missing || !props.restrict) return
  const next = candidate.active
    ? props.fields.filter((field) => field !== candidate.field)
    : [...props.fields, candidate.field]
  emit('update:fields', next)
}

const requestFields = computed(() => (config ? requestFieldsFor(config.fields) : []))

// Zoom is the chart's own affair — it only swaps which rows the axes are drawn
// on. A brush reset (criteria change, another experiment) drops it too.
const zoomed = ref(false)
watch(
  () => props.brush,
  (brush) => {
    if (!brush) zoomed.value = false
  }
)

/**
 * Rows the chart itself draws: the criteria cohort while brushing (so the
 * bands keep their full domain), the brushed subset once zoomed.
 */
const chartQuery = computed(() => (zoomed.value ? props.cohortQuery : props.criteriaQuery))

const chart = computed(() => {
  if (!config || !dataset || state.value !== 'ready') return null
  void readyTick.value
  const cohort = dataset.matrixSync(requestFields.value, chartQuery.value)
  const cohortIds = (cohort.ids ?? []) as string[]
  const cohortData = (cohort.data ?? []) as unknown as (string | number)[][]
  const submissionIds = props.detail.experiments.map((experiment) => experiment.id)
  const submissionData = props.detail.experiments.map((experiment) =>
    requestFields.value.map((field) => cellValue(experiment.cells[field]) as string | number)
  )
  // Submitted rows are appended after the filter, so no brush and no zoom can
  // drop the specimen under review from its own comparison.
  return {
    ids: [...cohortIds, ...submissionIds],
    data: [...cohortData, ...submissionData],
    drawnCount: cohortIds.length,
    pinnedIds: submissionIds
  }
})

/** Cohort sizes: criteria alone, and what the brush leaves of it. */
const similarCount = computed(() => {
  if (!dataset || state.value !== 'ready') return 0
  void readyTick.value
  return dataset.countRowsSync(props.criteriaQuery)
})
const brushedCount = computed(() => {
  if (!dataset || state.value !== 'ready' || !props.brush) return null
  void readyTick.value
  return dataset.countRowsSync(props.cohortQuery)
})

function onBrushCommit(selection: ParallelSelection): void {
  emit('update:brush', isEmptyBrush(selection) ? null : selection)
}

const labelPrefix = computed(() => `${CONTRIBUTION_DATABASES[props.database].namespace}.`)
</script>

<template>
  <section v-if="config" class="cohort-section">
    <p class="sech">{{ $t('curation.cohort.title') }}</p>

    <p v-if="state === 'loading'" class="state">{{ $t('curation.cohort.loading') }}</p>
    <p v-else-if="state === 'error'" class="state">
      <v-icon :icon="mdiAlertOutline" size="14" />
      {{ $t('curation.cohort.unavailable') }}
    </p>

    <template v-else-if="chart">
      <div class="cohort">
        <div class="cohort-h">
          <v-icon :icon="mdiAccountGroupOutline" size="16" />
          <b>{{ $t('curation.cohort.banner_title') }}</b>
          <span class="ct">
            {{ $t('curation.cohort.count', { count: similarCount }) }}
            <template v-if="brushedCount !== null">
              · {{ $t('curation.cohort.brushed', { count: brushedCount }) }}
            </template>
          </span>
        </div>
        <p class="cohort-lead">{{ $t('curation.cohort.lead') }}</p>
        <p class="cohort-hint">{{ $t('curation.cohort.criteria_hint') }}</p>
        <div class="cohort-chips" :class="{ inert: !restrict }">
          <button
            v-for="entry in candidates"
            :key="entry.field"
            class="cchip"
            :class="{ on: entry.active, missing: entry.missing }"
            :disabled="entry.missing || !restrict"
            type="button"
            @click="toggle(entry)"
          >
            {{ entry.label }}:
            <b v-if="!entry.missing">{{ entry.value }}</b>
            <span v-else class="nr">{{ $t('curation.cohort.not_reported') }}</span>
          </button>
        </div>
        <div class="cohort-foot">
          <tool-switch v-model="restrictModel" :label="$t('curation.cohort.restrict')" />
        </div>
        <p v-if="restrict && !criteriaQuery" class="cohort-note">
          <v-icon :icon="mdiInformationOutline" size="14" />
          {{ $t('curation.cohort.no_criteria') }}
        </p>
      </div>

      <div class="chartframe">
        <div class="ch">
          <span>{{ $t('curation.cohort.chart_title') }}</span>
          <span>
            {{
              $t('curation.cohort.ghosts', {
                count: chart.drawnCount,
                added: detail.experiments.length
              })
            }}
          </span>
        </div>
        <simple-parallel-chart
          :animate="false"
          :data="chart.data"
          :fields="config.fields"
          :ids="chart.ids"
          :is-filtered="brush !== null"
          :label-prefix="labelPrefix"
          :pinned-ids="chart.pinnedIds"
          :request-fields="requestFields"
          :zoomed="zoomed"
          @brush:commit="onBrushCommit"
          @update:zoomed="zoomed = $event"
        />
        <div class="chartleg">
          <span class="li">
            <span class="sw sel"></span>
            {{ $t('curation.cohort.legend_new', { id: selected?.id ?? '' }) }}
          </span>
          <span v-if="brushedCount !== null" class="li">
            <span class="sw brushed"></span>
            {{ $t('curation.cohort.legend_brushed', { count: brushedCount }) }}
          </span>
          <span class="li">
            <span class="sw ghost"></span>
            {{ $t('curation.cohort.legend_ghost', { count: chart.drawnCount }) }}
          </span>
        </div>
        <p class="charthint">{{ $t('curation.cohort.hint') }}</p>
        <p class="charthint">{{ $t('curation.cohort.brush_hint') }}</p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.cohort-section {
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
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0;
  font-size: 13.5px;
  color: var(--fg-muted);
}

/* ── cohort banner (prototype .cp-cohort) ── */
.cohort {
  border: 1px solid var(--border);
  border-left: 2px solid var(--fg);
  padding: 15px 18px;
  background: var(--bg-subtle);
}
.cohort-h {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 14px;
}
.cohort-h b {
  font-weight: 600;
}
.cohort-h .ct {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-subtle);
}
.cohort-lead {
  font-size: 13px;
  color: var(--fg-muted);
  line-height: 1.5;
  margin: 9px 0 12px;
}
.cohort-hint {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-subtle);
  margin: 0 0 8px;
}
.cohort-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.cohort-chips.inert {
  opacity: 0.45;
}
/* Criterion toggles — same square chip idiom as the experiment picker; an
   active criterion inverts so the applied filter reads at a glance. */
.cchip {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.02em;
  padding: 5px 9px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg-muted);
  cursor: pointer;
}
.cchip b {
  font-weight: 700;
  color: var(--fg);
}
.cchip:hover:not([disabled]) {
  border-color: var(--fg);
}
.cchip.on {
  background: var(--fg);
  border-color: var(--fg);
  color: var(--bg);
}
.cchip.on b {
  color: var(--bg);
}
.cchip[disabled] {
  cursor: default;
}
.cchip.missing {
  border-style: dashed;
  color: var(--fg-subtle);
}
.cchip .nr {
  color: var(--fg-subtle);
}
.cohort-foot {
  margin-top: 12px;
}
.cohort-note {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  font-size: 12px;
  color: var(--fg-subtle);
  margin: 12px 0 0;
  line-height: 1.45;
}

/* ── chart frame + legend (prototype .cp-previewchart / .cp-chartleg) ── */
.chartframe {
  border: 1px solid var(--border);
  padding: 16px 18px;
  margin-top: 16px;
}
.ch {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.chartleg {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}
.chartleg .li {
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-muted);
}
.chartleg .sw {
  flex: 0 0 auto;
}
.chartleg .sw.sel {
  width: 12px;
  height: 12px;
  background: var(--epfl-red);
}
.chartleg .sw.brushed {
  width: 16px;
  height: 0;
  border-top: 2px solid var(--epfl-red);
  opacity: 0.75;
}
.chartleg .sw.ghost {
  width: 16px;
  height: 0;
  border-top: 2px solid var(--border-strong);
}
.charthint {
  font-size: 12.5px;
  color: var(--fg-muted);
  line-height: 1.5;
  margin: 12px 0 0;
}
</style>
