<script setup lang="ts">
/**
 * What the last bulk drop did, and what is left to sort out — shown under the
 * intake zone, in the spirit of the BIDS validator's report: a few summary
 * lines, then the files that could not be placed, grouped by why, each with
 * the two choices (response type, experiment) that place it.
 */
import ToolSelect from '@/components/commons/tools/ToolSelect.vue'
import { useContributionStore } from '@/stores/contribution'
import type { IntakePending } from '@/utils/intake'
import { timeSeriesKindsFor, type TimeSeriesKind } from '@/utils/timeseries'
import { mdiClose } from '@mdi/js'
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()

const kinds = computed(() => timeSeriesKindsFor(store.database))
const summary = computed(() => store.lastIntake)

const experiments = computed(() =>
  store.rows
    .map((row) => ({ uid: row.uid, id: (row.cells.id ?? '').trim() }))
    .filter((entry) => entry.id !== '')
)

/** Curve files still expected on experiments that have an id, per required kind. */
const stillMissing = computed(() =>
  kinds.value
    .filter((kind) => kind.required)
    .map((kind) => ({
      kind,
      count: experiments.value.filter((entry) => !store.timeSeries[`${entry.uid}:${kind.key}`])
        .length
    }))
    .filter((entry) => entry.count > 0)
)

/**
 * Files placed by a guess (no folder name, headers shared with other types),
 * with the types they could also have been, to say what to check.
 */
const assumed = computed(() =>
  Object.entries(summary.value?.assumed ?? {}).map(([key, count]) => {
    const kind = kinds.value.find((candidate) => candidate.key === key)
    const names = (entry: TimeSeriesKind) => entry.columns.map((column) => column.name).join('|')
    const others = kind
      ? kinds.value.filter((other) => other !== kind && names(other) === names(kind))
      : []
    return {
      key,
      count,
      other: others.map((other) => t(`contribute.timeseries.kind.${other.key}`)).join(', ')
    }
  })
)

/** Files only a folder name could place, and the drop lost it (#437). */
const lostFolders = computed(() => store.pendingFiles.filter((entry) => entry.lostFolder).length)

const REASONS = ['orphan', 'ambiguous', 'unknown', 'foreign'] as const

const groups = computed(() =>
  REASONS.map((reason) => ({
    reason,
    items: store.pendingFiles.filter((entry) => entry.reason === reason)
  })).filter((group) => group.items.length > 0)
)

// --- Choices ---------------------------------------------------------------
// What the contributor has picked for each pending file. Seeded when the file
// arrives: the only possible response type, and the experiment whose id the
// file name contains, when there is exactly one.

interface Choice {
  kind: string
  /** Uid as a string, the select's currency; '' for none. */
  uid: string
}

const choices = reactive<Record<number, Choice>>({})

function guessUid(entry: IntakePending): string {
  const stem = entry.file.name.replace(/\.csv$/i, '').toLowerCase()
  const hits = experiments.value.filter(
    ({ id }) => stem.includes(id.toLowerCase()) || id.toLowerCase().includes(stem)
  )
  return hits.length === 1 ? String(hits[0].uid) : ''
}

watch(
  () => store.pendingFiles,
  (list) => {
    for (const entry of list) {
      if (!choices[entry.id]) {
        choices[entry.id] = {
          kind: entry.kinds.length === 1 ? entry.kinds[0].key : '',
          uid: guessUid(entry)
        }
      }
    }
  },
  { immediate: true }
)

function kindOptions(entry: IntakePending): TimeSeriesKind[] {
  return entry.kinds.length ? entry.kinds : kinds.value
}

function kindItems(list: TimeSeriesKind[]) {
  return list.map((kind) => ({
    title: t(`contribute.timeseries.kind.${kind.key}`),
    value: kind.key
  }))
}

const experimentItems = computed(() =>
  experiments.value.map((entry) => ({ title: entry.id, value: String(entry.uid) }))
)

function canAttach(entry: IntakePending): boolean {
  const choice = choices[entry.id]
  return !!choice && choice.kind !== '' && choice.uid !== ''
}

function attach(entry: IntakePending): void {
  const choice = choices[entry.id]
  const kind = kinds.value.find((candidate) => candidate.key === choice?.kind)
  if (!choice || !kind) return
  store.assignPending(entry.id, Number(choice.uid), kind)
}

/** The same response type for every file of a group (F2 for all of these). */
function setAllKinds(items: IntakePending[], key: string): void {
  for (const entry of items) if (choices[entry.id]) choices[entry.id].kind = key
}

function ignoreAll(): void {
  for (const entry of [...store.pendingFiles]) store.ignorePending(entry.id)
}

/** The kinds every file of a group could take, for the "set all" select. */
function sharedKinds(items: IntakePending[]): TimeSeriesKind[] {
  const first = kindOptions(items[0])
  return first.filter((kind) => items.every((entry) => kindOptions(entry).includes(kind)))
}
</script>

<template>
  <section class="intake-report">
    <div class="report-head">
      <h3>{{ $t('contribute.intake.report_title') }}</h3>
      <button
        v-if="store.pendingFiles.length === 0"
        class="btn btn-ghost btn-sm"
        type="button"
        @click="store.clearIntake()"
      >
        <v-icon :icon="mdiClose" size="13" />{{ $t('contribute.intake.dismiss') }}
      </button>
    </div>

    <ul v-if="summary" class="lines">
      <li v-if="lostFolders" class="warn">
        {{ $t('contribute.intake.line_lost_folders', { count: lostFolders }) }}
      </li>
      <li v-if="summary.primaryName" class="ok">
        {{
          $t('contribute.intake.line_primary', {
            name: summary.primaryName,
            added: summary.added,
            updated: summary.updated
          })
        }}
      </li>
      <li v-for="(count, key) in summary.attached" :key="key" class="ok">
        {{
          $t('contribute.intake.line_attached', {
            kind: $t(`contribute.timeseries.kind.${key}`),
            count
          })
        }}
      </li>
      <li v-for="entry in assumed" :key="`assumed-${entry.key}`" class="warn">
        {{
          $t('contribute.intake.line_assumed', {
            kind: $t(`contribute.timeseries.kind.${entry.key}`),
            other: entry.other,
            count: entry.count
          })
        }}
      </li>
      <li v-for="entry in stillMissing" :key="entry.kind.key" class="warn">
        {{
          $t('contribute.intake.line_missing', {
            kind: $t(`contribute.timeseries.kind.${entry.kind.key}`),
            count: entry.count
          })
        }}
      </li>
      <li v-if="summary.primaryCandidates.length" class="warn">
        {{
          $t('contribute.intake.line_candidates', { files: summary.primaryCandidates.join(', ') })
        }}
      </li>
      <li v-if="summary.skipped.length" class="muted">
        {{ $t('contribute.intake.line_skipped', { files: summary.skipped.join(', ') }) }}
      </li>
    </ul>

    <div v-for="group in groups" :key="group.reason" class="group">
      <div class="group-head">
        <strong>{{
          $t(`contribute.intake.reason.${group.reason}`, { count: group.items.length })
        }}</strong>
        <span class="group-hint">{{ $t(`contribute.intake.reason_hint.${group.reason}`) }}</span>
        <label
          v-if="
            group.reason !== 'foreign' && group.items.length > 1 && sharedKinds(group.items).length
          "
          class="set-all"
        >
          {{ $t('contribute.intake.set_all') }}
          <tool-select
            class="pick"
            :items="kindItems(sharedKinds(group.items))"
            :model-value="''"
            :placeholder="$t('contribute.intake.pick_kind')"
            @update:model-value="setAllKinds(group.items, $event)"
          />
        </label>
      </div>
      <div v-for="entry in group.items" :key="entry.id" class="row">
        <code class="file" :title="entry.file.path">{{ entry.file.path }}</code>
        <template v-if="group.reason !== 'foreign' && choices[entry.id]">
          <tool-select
            v-model="choices[entry.id].kind"
            class="pick"
            :items="kindItems(kindOptions(entry))"
            :placeholder="$t('contribute.intake.pick_kind')"
          />
          <tool-select
            v-model="choices[entry.id].uid"
            class="pick"
            :items="experimentItems"
            :placeholder="$t('contribute.intake.pick_experiment')"
          />
          <button
            class="btn btn-secondary btn-sm"
            :disabled="!canAttach(entry)"
            type="button"
            @click="attach(entry)"
          >
            {{ $t('contribute.intake.attach') }}
          </button>
        </template>
        <button class="btn btn-ghost btn-sm" type="button" @click="store.ignorePending(entry.id)">
          <v-icon :icon="mdiClose" size="13" />{{ $t('contribute.intake.ignore') }}
        </button>
      </div>
    </div>

    <div v-if="store.pendingFiles.length" class="foot">
      <button class="btn btn-ghost btn-sm" type="button" @click="ignoreAll">
        {{ $t('contribute.intake.ignore_all') }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.intake-report {
  margin-bottom: 16px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--border-strong);
  background: var(--bg);
  font-size: 12.5px;
}
.report-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.report-head h3 {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.lines {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  line-height: 1.5;
}
.lines li {
  padding-left: 14px;
  position: relative;
}
.lines li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.55em;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--border-strong);
}
.lines .ok::before {
  background: var(--epfl-green-text);
}
.lines .warn::before {
  background: var(--epfl-orange);
}
.lines .muted {
  color: var(--fg-muted);
}

.group {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border-subtle);
}
.group-head {
  display: flex;
  align-items: center;
  gap: 6px 12px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.group-hint {
  color: var(--fg-muted);
}
.set-all {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  color: var(--fg-muted);
}
/* The file name keeps a readable width and the controls wrap under it
   when the row is too narrow for all of them. */
.row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 10px;
  padding: 4px 0;
}
.file {
  flex: 1 1 240px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}
.pick {
  flex: none;
  min-width: 170px;
}
.row .btn {
  flex: none;
}
.foot {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
</style>
