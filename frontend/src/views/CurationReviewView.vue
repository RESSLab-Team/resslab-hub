<script setup lang="ts">
import type { CurationDetail } from '@/backend'
import CohortPanel from '@/components/curation/CohortPanel.vue'
import DataPreviewPanel from '@/components/curation/DataPreviewPanel.vue'
import MetadataPanel from '@/components/curation/MetadataPanel.vue'
import QualityFlagsRail from '@/components/curation/QualityFlagsRail.vue'
import ReviewThread from '@/components/curation/ReviewThread.vue'
import { cohortQueryFor, GHOST_CONFIGS, mergeBrush } from '@/components/curation/ghost'
import type { ParallelSelection } from '@/composables/chart'
import { useDataset } from '@/composables/useDataset'
import { useCurationStore } from '@/stores/curation'
import { useDictionaryStore } from '@/stores/dictionary'
import { databaseIdForType, formatAge, withDerivedExperiments } from '@/utils/curation'
import { DATABASES } from '@/utils/navigation'
import {
  mdiAlertOutline,
  mdiArrowLeft,
  mdiCheck,
  mdiClose,
  mdiOpenInNew,
  mdiSendOutline
} from '@mdi/js'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  prNumber: string
}>()

const { locale } = useI18n({ useScope: 'global' })
const store = useCurationStore()
const dictionary = useDictionaryStore()

const number = computed(() => Number(props.prNumber))
const detail = ref<CurationDetail | null>(null)
const state = ref<'loading' | 'ready' | 'error'>('loading')

const database = computed(() => (detail.value ? databaseIdForType(detail.value.type) : null))
const databaseName = computed(
  () => DATABASES.find((entry) => entry.id === database.value)?.name ?? detail.value?.type ?? ''
)

const selectedUid = ref(0)
const selected = computed(() => detail.value?.experiments[selectedUid.value])

const selectedFiles = computed(() => {
  if (!detail.value || !selected.value) return []
  return detail.value.files.filter(
    (file) => file.kind === 'timeseries' && file.experiment_id === selected.value?.id
  )
})

// Comparison cohort: which similarity criteria are switched on. Owned here
// because both the ghost chart and the test-data curve overlays draw from the
// same cohort — refining it in one place refines both.
const cohortFields = ref<string[]>([])
const restrictCohort = ref(true)
const criteriaQuery = computed(() => {
  if (!restrictCohort.value || !selected.value) return undefined
  return cohortQueryFor(selected.value.cells, cohortFields.value)
})

// Second cohort filter: the committed brush on the parallel chart. It lives
// here rather than in the cohort panel because the data preview's overlay
// candidates have to follow it too.
const brush = ref<ParallelSelection | null>(null)
const cohortQuery = computed(() => mergeBrush(criteriaQuery.value, brush.value))

// A brush is only meaningful against the axes it was drawn on: changing the
// criteria or the experiment redraws them, so drop it. Nulling it also flips
// the chart's `isFiltered` prop, whose watch clears the covers and the zoom.
watch([selectedUid, criteriaQuery], () => {
  brush.value = null
})

// "Existing range" ghost hints: observed min–max of each numeric dictionary
// field across the database the submission targets (same dataset instance as
// the cohort panel — the module cache dedupes the fetch).
const ranges = ref<Record<string, { min: number; max: number }>>({})
async function loadRanges(): Promise<void> {
  const databaseId = database.value
  const config = databaseId ? GHOST_CONFIGS[databaseId] : undefined
  if (!databaseId || !config) return
  const dataset = useDataset<{ id: string }>(config.key, config.fetchAll)
  try {
    await dataset.ready()
  } catch {
    return
  }
  const numeric = new Set(['Numeric', 'DecimalFloat', 'SmallInteger', 'Integer', 'BigInteger'])
  const next: Record<string, { min: number; max: number }> = {}
  for (const column of dictionary.columnsFor(databaseId)) {
    if (!numeric.has(column.type)) continue
    const { data } = await dataset.getRange(column.name)
    const min = Number(data.min)
    const max = Number(data.max)
    // An all-zero range is `extent()`'s empty fallback — no signal, skip it.
    if (Number.isNaN(min) || Number.isNaN(max) || (min === 0 && max === 0)) continue
    next[column.name] = { min, max }
  }
  ranges.value = next
}

onMounted(async () => {
  dictionary.fetch()
  try {
    // Derived columns (the material `type`) are added here once, so the cohort
    // chips, the cohort query and the ghost chart all read them as cells.
    detail.value = withDerivedExperiments(await store.fetchDetail(number.value))
    state.value = 'ready'
    const config = database.value ? GHOST_CONFIGS[database.value] : undefined
    cohortFields.value = config ? [...config.cohortDefaults] : []
    loadRanges()
  } catch {
    state.value = 'error'
  }
})

const metadataPanel = ref<InstanceType<typeof MetadataPanel> | null>(null)

/** A quality flag was clicked: show that experiment and flash the field. */
async function selectIssue(uid: number, column: string): Promise<void> {
  selectedUid.value = uid
  await nextTick()
  metadataPanel.value?.flash(column)
}
</script>

<template>
  <div class="curation-review">
    <p v-if="state === 'loading'" class="state pad">{{ $t('curation.review.loading') }}</p>

    <template v-else-if="state === 'error'">
      <p class="state pad">
        <v-icon :icon="mdiAlertOutline" size="15" />
        {{ $t('curation.review.not_found') }}
      </p>
      <router-link class="cp-btn back" to="/curation">
        <v-icon :icon="mdiArrowLeft" size="14" />
        {{ $t('curation.review.back') }}
      </router-link>
    </template>

    <div v-else-if="detail && database" class="val">
      <div class="val-main">
        <div class="val-head">
          <p class="k">
            {{ $t('curation.review.eyebrow', { number: detail.pr_number }) }} · {{ databaseName }} ·
            {{ $t('curation.review.in_review') }}
          </p>
          <div class="hrow">
            <h2>
              {{ detail.experiments[0]?.id ?? detail.title }}
              <span v-if="detail.experiments.length > 1" class="more">
                {{
                  $t('curation.review.more_experiments', { count: detail.experiments.length - 1 })
                }}
              </span>
            </h2>
            <a class="cp-btn" :href="detail.pr_url" target="_blank" rel="noreferrer">
              <v-icon :icon="mdiOpenInNew" size="14" />
              {{ $t('curation.review.open_pr') }}
            </a>
          </div>
          <p class="sub">
            <template v-if="detail.contributor?.name">
              {{ $t('curation.review.submitted_by', { name: detail.contributor.name })
              }}<template v-if="detail.contributor.institution">
                · {{ detail.contributor.institution }}</template
              >
              <template v-if="detail.contributor.orcid">
                · ORCID {{ detail.contributor.orcid }}</template
              >
            </template>
            <template v-else>{{ $t('curation.review.unknown_contributor') }}</template>
            · {{ formatAge(detail.submitted_at || detail.created_at, locale) }}
          </p>
        </div>

        <div class="val-body">
          <p v-if="detail.reconstruction_warning" class="reconstruction">
            <v-icon :icon="mdiAlertOutline" size="15" />
            {{ detail.reconstruction_warning }}
          </p>

          <div v-if="detail.experiments.length > 1" class="selector">
            <p class="selector-label">
              {{ $t('curation.review.experiments_label', { count: detail.experiments.length }) }}
            </p>
            <div class="selector-chips">
              <button
                v-for="(experiment, index) in detail.experiments"
                :key="experiment.id"
                class="chip"
                :class="{ sel: index === selectedUid }"
                type="button"
                @click="selectedUid = index"
              >
                {{ experiment.id }}
              </button>
            </div>
          </div>

          <metadata-panel
            v-if="selected"
            ref="metadataPanel"
            :columns="detail.columns"
            :database="database"
            :experiment="selected"
            :ranges="ranges"
          />
          <cohort-panel
            v-model:brush="brush"
            v-model:fields="cohortFields"
            v-model:restrict="restrictCohort"
            :cohort-query="cohortQuery"
            :criteria-query="criteriaQuery"
            :database="database"
            :detail="detail"
            :selected-uid="selectedUid"
          />
          <data-preview-panel
            v-if="selected"
            :cohort-query="cohortQuery"
            :database="database"
            :files="selectedFiles"
            :pr-number="detail.pr_number"
          />
        </div>
      </div>

      <aside class="val-rail">
        <div class="rail-scroll">
          <quality-flags-rail
            :database="database"
            :detail="detail"
            :pr-number="detail.pr_number"
            @select="selectIssue"
          />

          <review-thread :pr-number="detail.pr_number" :pr-url="detail.pr_url" />
        </div>

        <div class="val-actions" :title="$t('curation.actions.disabled_tooltip')">
          <button class="cp-btn primary full" disabled type="button">
            <v-icon :icon="mdiSendOutline" size="14" />
            {{ $t('curation.actions.request_changes') }}
          </button>
          <div class="row2">
            <button class="cp-btn teal" disabled type="button">
              <v-icon :icon="mdiCheck" size="14" />{{ $t('curation.actions.approve') }}
            </button>
            <button class="cp-btn" disabled type="button">
              <v-icon :icon="mdiClose" size="14" />{{ $t('curation.actions.reject') }}
            </button>
          </div>
          <p class="actions-note">{{ $t('curation.actions.disabled_tooltip') }}</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.curation-review {
  min-height: 100%;
  background: var(--bg);
}
.state {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--fg-muted);
}
.pad {
  padding: 30px 40px;
}
.back {
  margin: 0 40px;
  text-decoration: none;
}

/* ── two-pane validation layout (prototype .cp-val) ──
   The rail scales with the viewport so huge screens don't leave a skinny
   fixed-width column beside an ocean of main pane. */
.val {
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(340px, 26vw, 480px);
  min-height: 100%;
}
@media (max-width: 1100px) {
  .val {
    grid-template-columns: minmax(0, 1fr);
  }
  .val-main {
    border-right: 0 !important;
  }
  .val-rail {
    position: static !important;
    max-height: none !important;
    border-top: 1px solid var(--fg);
  }
}
.val-main {
  min-width: 0;
  border-right: 1px solid var(--fg);
}
.val-head {
  padding: 26px clamp(22px, 3vw, 56px) 20px;
  border-bottom: 1px solid var(--border);
}
.val-head .k {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--epfl-red);
  text-transform: uppercase;
  margin: 0;
}
.hrow {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
}
.val-head h2 {
  font-size: 28px;
  font-weight: 300;
  letter-spacing: -0.01em;
  margin: 10px 0 6px;
}
.val-head .more {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 400;
  color: var(--fg-muted);
  margin-left: 8px;
}
.val-head .sub {
  font-size: 13px;
  color: var(--fg-muted);
  margin: 0;
}
.val-body {
  padding: 24px clamp(22px, 3vw, 56px) 40px;
}

/* prototype button */
.cp-btn {
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  padding: 11px 18px;
  border: 1px solid var(--fg);
  background: var(--bg);
  color: var(--fg);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  white-space: nowrap;
  text-decoration: none;
}
.cp-btn:hover:not([disabled]) {
  border-color: var(--epfl-red);
  color: var(--epfl-red);
}
.cp-btn.primary {
  background: var(--epfl-red);
  color: #fff;
  border-color: var(--epfl-red);
}
.cp-btn.teal {
  background: var(--epfl-canard, #007480);
  color: #fff;
  border-color: var(--epfl-canard, #007480);
}
.cp-btn[disabled] {
  background: var(--bg-subtle);
  color: var(--fg-disabled, var(--fg-subtle));
  border-color: var(--border);
  cursor: not-allowed;
}

.reconstruction {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 20px;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-left: 3px solid var(--epfl-orange);
  background: var(--bg-subtle);
  font-size: 13px;
  color: var(--fg-muted);
}
/* Experiment picker — wrapping chip select (prototype .cp-chips): batches of
   any size stay reachable instead of a segmented row overflowing the pane. */
.selector {
  margin-bottom: 24px;
}
.selector-label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-subtle);
  margin: 0 0 8px;
}
.selector-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.chip {
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 6px 11px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--fg);
  cursor: pointer;
}
.chip:hover {
  border-color: var(--fg);
}
.chip.sel {
  background: var(--fg);
  color: var(--bg);
  border-color: var(--fg);
}

/* ── right rail ── */
.val-rail {
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: sticky;
  top: 0;
  max-height: 100vh;
  background: var(--bg);
}
.rail-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 22px clamp(20px, 1.8vw, 32px);
}
.val-actions {
  padding: 18px 24px;
  border-top: 1px solid var(--fg);
  background: var(--bg-subtle);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.val-actions .full {
  width: 100%;
  justify-content: center;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}
.row2 .cp-btn {
  justify-content: center;
}
.row2 .cp-btn + .cp-btn {
  border-left: 0;
}
.actions-note {
  font-size: 11.5px;
  color: var(--fg-subtle);
  line-height: 1.45;
  margin: 2px 0 0;
}
</style>
