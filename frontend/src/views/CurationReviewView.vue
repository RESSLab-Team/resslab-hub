<script setup lang="ts">
import ProgressLine from '@/components/commons/ProgressLine.vue'
import type { CurationDetail, Type, VerificationBatch, VerificationPull } from '@/backend'
import CohortPanel from '@/components/curation/CohortPanel.vue'
import DataPreviewPanel from '@/components/curation/DataPreviewPanel.vue'
import MetadataPanel from '@/components/curation/MetadataPanel.vue'
import QualityFlagsRail from '@/components/curation/QualityFlagsRail.vue'
import ReviewThread from '@/components/curation/ReviewThread.vue'
import { cohortQueryFor, GHOST_CONFIGS, mergeBrush } from '@/components/curation/ghost'
import { spliceQueryClause, type ParallelSelection } from '@/composables/chart'
import { useDataset } from '@/composables/useDataset'
import { useAuthStore } from '@/stores/auth'
import { useCurationStore } from '@/stores/curation'
import { useDictionaryStore } from '@/stores/dictionary'
import { errorDetail, useVerificationStore } from '@/stores/verification'
import { databaseIdForType, formatAge, withDerivedExperiments } from '@/utils/curation'
import { idsSearch, STATUS_COLUMN, VERIFIED } from '@/utils/curationStatus'
import { DATABASES } from '@/utils/navigation'
import {
  mdiAlertOutline,
  mdiArrowLeft,
  mdiCheck,
  mdiClose,
  mdiOpenInNew,
  mdiPencilOutline,
  mdiSendOutline
} from '@mdi/js'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

/**
 * One page, two reviews. A submission (`prNumber`): the rows of an open pull
 * request, before it is merged. A verification (`type`, with
 * `?reference=` and an optional `?id=` to start on, #253): rows already live
 * and still unverified, read from the data repository, with the button that
 * marks them as verified. The panels are the same, because this second check
 * is where most of the scientific review happens.
 */
const props = defineProps<{
  prNumber?: string
  /** Backend uploader Type value, e.g. `all-columns`. */
  type?: string
}>()

const { locale } = useI18n({ useScope: 'global' })
const store = useCurationStore()
const verification = useVerificationStore()
const dictionary = useDictionaryStore()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const verifying = computed(() => props.type !== undefined)
const reference = computed(() => String(route.query.reference ?? ''))

const number = computed(() => Number(props.prNumber))
const detail = ref<CurationDetail | null>(null)
const verifyBatch = ref<VerificationBatch | null>(null)
/** What the panels read, in either mode. */
const batch = computed(() => detail.value ?? verifyBatch.value)
const state = ref<'loading' | 'ready' | 'error'>('loading')
/** The backend's sentence when the verification rows could not be loaded. */
const loadError = ref<string | undefined>(undefined)

const database = computed(() => (batch.value ? databaseIdForType(batch.value.type) : null))
const databaseEntry = computed(() => DATABASES.find((entry) => entry.id === database.value))
const databaseName = computed(() => databaseEntry.value?.name ?? batch.value?.type ?? '')

const selectedUid = ref(0)
const selected = computed(() => batch.value?.experiments[selectedUid.value])

const selectedFiles = computed(() => {
  if (!batch.value || !selected.value) return []
  return batch.value.files.filter(
    (file) => file.kind === 'timeseries' && file.experiment_id === selected.value?.id
  )
})

// Comparison cohort: which similarity criteria are switched on. Owned here
// because both the ghost chart and the test-data curve overlays draw from the
// same cohort — refining it in one place refines both.
const cohortFields = ref<string[]>([])
const restrictCohort = ref(true)
const criteriaQuery = computed(() => {
  const criteria =
    restrictCohort.value && selected.value
      ? cohortQueryFor(selected.value.cells, cohortFields.value)
      : undefined
  // Live rows are compared with the verified ones only: the rows under
  // review are in the database too, and the batch would be its own cohort.
  return verifying.value ? spliceQueryClause(criteria, STATUS_COLUMN, `${VERIFIED},`) : criteria
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
    if (props.type !== undefined) {
      const loaded = withDerivedExperiments(
        await verification.fetchBatch(props.type as Type, reference.value)
      )
      const start = loaded.experiments.findIndex((experiment) => experiment.id === route.query.id)
      if (start >= 0) selectedUid.value = start
      verifyBatch.value = loaded
    } else {
      detail.value = withDerivedExperiments(await store.fetchDetail(number.value))
    }
    state.value = 'ready'
    const config = database.value ? GHOST_CONFIGS[database.value] : undefined
    cohortFields.value = config ? [...config.cohortDefaults] : []
    loadRanges()
  } catch (caught: unknown) {
    // A contributor opened someone else's submission: the router let them
    // through on the role, the backend knows whose it is (#248).
    if ((caught as { response?: { status?: number } })?.response?.status === 403) {
      router.replace({
        name: 'Forbidden',
        query: { next: route.fullPath, need: 'curator', reason: 'not_yours' }
      })
      return
    }
    loadError.value = errorDetail(caught)
    state.value = 'error'
  }
})

// The panels load their files and checks through these, so they do not need
// to know which review they are in.
const loadFile = computed(() => {
  const submission = detail.value
  if (submission) return (path: string) => store.fetchFileText(submission.pr_number, path)
  const live = verifyBatch.value
  return (path: string) =>
    live ? verification.fetchFileText(live.type as Type, live.base_sha, path) : Promise.reject()
})
const loadValidation = computed(() => {
  const submission = detail.value
  if (submission) return () => store.fetchValidation(submission.pr_number)
  const live = verifyBatch.value
  return () =>
    live ? verification.fetchValidation(live.type as Type, live.reference) : Promise.reject()
})

// ── verification (#253) ──

/** The open verification pull request of a row: the backend's, or one opened here. */
function pullFor(id: string): VerificationPull | undefined {
  const live = verifyBatch.value
  if (!live) return undefined
  return verification.pendingFor(live.type, id) ?? live.pending[id]
}

/** Verified in the data repository already, waiting for the next upload. */
const alreadyVerified = computed(
  () =>
    verifyBatch.value?.experiments
      .filter((experiment) => experiment.cells[STATUS_COLUMN]?.trim() === VERIFIED)
      .map((experiment) => experiment.id) ?? []
)

/** The rows the button would mark: not verified yet, not in a pull request. */
const toVerify = computed(
  () =>
    verifyBatch.value?.experiments
      .map((experiment) => experiment.id)
      .filter((id) => !pullFor(id) && !alreadyVerified.value.includes(id)) ?? []
)

/** The pull requests that cover rows of this page, once each. */
const pulls = computed(() => {
  const byNumber = new Map<number, VerificationPull>()
  for (const experiment of verifyBatch.value?.experiments ?? []) {
    const pull = pullFor(experiment.id)
    if (pull) byNumber.set(pull.pr_number, pull)
  }
  return [...byNumber.values()]
})

const dashboardLink = computed(() => {
  const live = verifyBatch.value
  if (!live || !databaseEntry.value || !live.experiments.length) return null
  return {
    path: databaseEntry.value.to,
    query: { id: idsSearch(live.experiments.map((experiment) => experiment.id)) }
  }
})

const verifyBusy = ref(false)
/** `null` when nothing failed, else the backend's sentence (may be empty). */
const verifyError = ref<string | null>(null)

async function markVerified(ids: string[]): Promise<void> {
  const live = verifyBatch.value
  if (!live || !ids.length) return
  verifyBusy.value = true
  verifyError.value = null
  try {
    await verification.verify(live.type as Type, ids)
  } catch (caught) {
    verifyError.value = errorDetail(caught) ?? ''
  } finally {
    verifyBusy.value = false
  }
}

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
    <progress-line
      v-if="state === 'loading'"
      class="pad"
      :active="true"
      :label="$t(verifying ? 'curation.verify_review.loading' : 'curation.review.loading')"
    />

    <template v-else-if="state === 'error'">
      <p class="state pad">
        <v-icon :icon="mdiAlertOutline" size="15" />
        <span>
          {{ $t(verifying ? 'curation.verify_review.not_found' : 'curation.review.not_found') }}
          <span v-if="verifying && loadError" class="state-detail">{{ loadError }}</span>
        </span>
      </p>
      <router-link
        v-if="auth.hasRole('curator')"
        class="cp-btn back"
        :to="verifying ? { path: '/curation', query: { tab: 'verify' } } : '/curation'"
      >
        <v-icon :icon="mdiArrowLeft" size="14" />
        {{ $t('curation.review.back') }}
      </router-link>
    </template>

    <div v-else-if="batch && database" class="val">
      <div class="val-main">
        <div v-if="verifyBatch" class="val-head">
          <p class="k">
            {{ $t('curation.verify_review.eyebrow') }} · {{ databaseName }} ·
            {{ $t('commons.unverified.tag') }}
          </p>
          <div class="hrow">
            <h2>
              {{ verifyBatch.experiments[0]?.id ?? verifyBatch.reference }}
              <span v-if="verifyBatch.experiments.length > 1" class="more">
                {{
                  $t('curation.review.more_experiments', {
                    count: verifyBatch.experiments.length - 1
                  })
                }}
              </span>
            </h2>
            <div class="hrow-actions">
              <router-link v-if="dashboardLink" class="cp-btn" :to="dashboardLink">
                <v-icon :icon="mdiOpenInNew" size="14" />
                {{ $t('curation.verify_review.open_dashboard') }}
              </router-link>
            </div>
          </div>
          <p class="sub">
            {{ verifyBatch.reference || $t('curation.verify.no_reference') }} ·
            <span class="mono">{{
              $t('curation.verify_review.read_at', { sha: verifyBatch.base_sha.slice(0, 7) })
            }}</span>
          </p>
        </div>
        <div v-else-if="detail" class="val-head">
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
            <div class="hrow-actions">
              <router-link
                v-if="detail.mine || auth.hasRole('curator')"
                class="cp-btn"
                :to="{ name: 'ContributeEdit', params: { prNumber: detail.pr_number } }"
              >
                <v-icon :icon="mdiPencilOutline" size="14" />
                {{ $t('curation.review.edit_on_hub') }}
              </router-link>
              <a class="cp-btn" :href="detail.pr_url" target="_blank" rel="noopener noreferrer">
                <v-icon :icon="mdiOpenInNew" size="14" />
                {{ $t('curation.review.open_pr') }}
              </a>
            </div>
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
          <p v-if="detail?.reconstruction_warning" class="reconstruction">
            <v-icon :icon="mdiAlertOutline" size="15" />
            {{ detail.reconstruction_warning }}
          </p>
          <template v-if="verifyBatch">
            <p v-if="verifyBatch.missing_ids.length" class="reconstruction">
              <v-icon :icon="mdiAlertOutline" size="15" />
              {{
                $t('curation.verify_review.missing', { ids: verifyBatch.missing_ids.join(', ') })
              }}
            </p>
            <p v-if="alreadyVerified.length" class="reconstruction">
              <v-icon :icon="mdiAlertOutline" size="15" />
              {{
                $t('curation.verify_review.already_verified', { ids: alreadyVerified.join(', ') })
              }}
            </p>
          </template>

          <div v-if="batch.experiments.length > 1" class="selector">
            <p class="selector-label">
              {{
                $t(
                  verifying
                    ? 'curation.verify_review.experiments_label'
                    : 'curation.review.experiments_label',
                  { count: batch.experiments.length }
                )
              }}
            </p>
            <div class="selector-chips">
              <button
                v-for="(experiment, index) in batch.experiments"
                :key="experiment.id"
                class="chip"
                :class="{
                  sel: index === selectedUid,
                  pending: verifying && !!pullFor(experiment.id)
                }"
                :title="
                  verifying && pullFor(experiment.id)
                    ? $t('commons.unverified.pending', {
                        number: pullFor(experiment.id)?.pr_number
                      })
                    : undefined
                "
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
            :columns="batch.columns"
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
            :detail="batch"
            :selected-uid="selectedUid"
          />
          <data-preview-panel
            v-if="selected"
            :cells="selected.cells"
            :cohort-query="cohortQuery"
            :database="database"
            :files="selectedFiles"
            :load-file="loadFile"
          />
        </div>
      </div>

      <aside class="val-rail">
        <div class="rail-scroll">
          <quality-flags-rail
            :database="database"
            :detail="batch"
            :load-validation="loadValidation"
            @select="selectIssue"
          />

          <review-thread v-if="detail" :pr-number="detail.pr_number" :pr-url="detail.pr_url" />
        </div>

        <div v-if="verifyBatch" class="val-actions">
          <button
            v-if="toVerify.length"
            class="cp-btn primary full"
            :disabled="verifyBusy"
            type="button"
            @click="markVerified(toVerify)"
          >
            <v-icon :icon="mdiCheck" size="14" />
            {{
              verifyBusy
                ? $t('commons.unverified.opening')
                : $t('curation.verify.button', { count: toVerify.length }, toVerify.length)
            }}
          </button>
          <button
            v-if="selected && toVerify.length > 1 && toVerify.includes(selected.id)"
            class="cp-btn full"
            :disabled="verifyBusy"
            type="button"
            @click="markVerified([selected.id])"
          >
            {{ $t('curation.verify_review.only', { id: selected.id }) }}
          </button>
          <p v-if="!toVerify.length" class="actions-note">
            {{ $t('curation.verify_review.nothing_left') }}
          </p>
          <a
            v-for="pull in pulls"
            :key="pull.pr_number"
            class="pull"
            :href="pull.pr_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ $t('commons.unverified.pending', { number: pull.pr_number }) }}
            <v-icon :icon="mdiOpenInNew" size="13" />
          </a>
          <p v-if="verifyError !== null" class="fail" role="alert">
            {{ $t('commons.unverified.failed') }}
            <span v-if="verifyError" class="state-detail">{{ verifyError }}</span>
          </p>
          <p class="actions-note">{{ $t('curation.verify_review.note') }}</p>
        </div>
        <div v-else class="val-actions" :title="$t('curation.actions.disabled_tooltip')">
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
  padding: 30px clamp(16px, 4vw, 40px);
}
.back {
  margin: 0 clamp(16px, 4vw, 40px);
  text-decoration: none;
}
.state-detail {
  display: block;
  font-size: 12.5px;
  color: var(--fg-subtle);
  margin-top: 4px;
}
.mono {
  font-family: var(--font-mono);
  font-size: 12px;
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
.hrow-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
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
/* In a verification pull request already: still there to look at. */
.chip.pending:not(.sel) {
  color: var(--fg-subtle);
  border-style: dashed;
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
/* Phone: the two buttons stack, still joined by one shared border. */
@media (max-width: 480px) {
  .row2 {
    grid-template-columns: 1fr;
  }
  .row2 .cp-btn + .cp-btn {
    border-left: 1px solid var(--fg);
    border-top: 0;
  }
}
.pull {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--fg);
  text-decoration: none;
}
.pull:hover {
  color: var(--epfl-red);
}
.fail {
  font-size: 12.5px;
  margin: 0;
}
.actions-note {
  font-size: 11.5px;
  color: var(--fg-subtle);
  line-height: 1.45;
  margin: 2px 0 0;
}
</style>
