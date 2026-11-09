<script setup lang="ts">
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import IntakeReport from '@/components/contribute/IntakeReport.vue'
import DataLegend, { type DataLegendItem } from '@/components/curation/DataLegend.vue'
import { useContributionStore, type CardIssue, type IntakeSummary } from '@/stores/contribution'
import { useNotificationStore } from '@/stores/notification'
import { groupBy, type FieldGroupId } from '@/utils/fieldGroups'
import {
  classifyIntake,
  collectFromDataTransfer,
  collectFromFileList,
  expandArchives,
  type IntakeFile,
  type IntakePlan
} from '@/utils/intake'
import { sparkline } from '@/utils/sparkline'
import {
  downloadDictionary,
  downloadExampleSeries,
  downloadStarterKit,
  downloadTemplate
} from '@/utils/templates'
import { fileStemFor, timeSeriesKindsFor, type TimeSeriesKind } from '@/utils/timeseries'
import {
  mdiAlertCircleOutline,
  mdiAlertOutline,
  mdiBellOffOutline,
  mdiBookOpenPageVariantOutline,
  mdiCheckCircleOutline,
  mdiChevronRight,
  mdiClose,
  mdiContentCopy,
  mdiDownloadOutline,
  mdiFolderOutline,
  mdiPackageVariantClosed,
  mdiPlus,
  mdiRestore,
  mdiTrayArrowUp,
  mdiUnfoldLessHorizontal,
  mdiUnfoldMoreHorizontal
} from '@mdi/js'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t, te } = useI18n({ useScope: 'global' })
const store = useContributionStore()
const notification = useNotificationStore()

const emit = defineEmits<{ (event: 'open-guide', tab: 'guide' | 'dictionary'): void }>()

const kinds = computed(() => timeSeriesKindsFor(store.database))

// Headline fields shown on the collapsed card: identifying metadata first,
// padded with the first dictionary columns after id.
const HEADLINE_PREFERRED = [
  'date',
  'investigator',
  'cross_section_shape',
  'grade',
  'connection_type',
  'test_type',
  'section'
]
const headlineColumns = computed(() => {
  const names = new Set(store.columns.map((column) => column.name))
  const picked = HEADLINE_PREFERRED.filter((name) => names.has(name)).slice(0, 3)
  for (const column of store.columns) {
    if (picked.length >= 3) break
    if (column.name !== 'id' && !picked.includes(column.name)) picked.push(column.name)
  }
  return store.columns.filter((column) => picked.includes(column.name))
})

// --- Sticky heads ----------------------------------------------------------
// An experiment head, and the head of the group being filled in, stay pinned
// while their own content scrolls past, so the title a contributor is reading
// fields under — and the button that folds it away — are always in reach. A
// group head pins directly under its card head, so its offset has to follow
// that head's real height, which grows when the response-type chips wrap on a
// narrow screen. Every head holds the same shape, so one measurement sizes them
// all; only a width change can alter it, hence one observer on the list rather
// than one per card.
const editorEl = ref<HTMLElement>()
const cardHeadHeight = ref('44px')
let headObserver: ResizeObserver | undefined

function measureCardHead(): void {
  const head = editorEl.value?.querySelector<HTMLElement>('.card-head')
  if (head) cardHeadHeight.value = `${head.offsetHeight}px`
}

// The first card carries the measurement, so re-measure whenever the batch (or
// the database behind the chips) changes under it.
watch([() => store.rows.length, kinds], async () => {
  await nextTick()
  measureCardHead()
})

onMounted(() => {
  measureCardHead()
  if ('ResizeObserver' in window && editorEl.value) {
    headObserver = new ResizeObserver(measureCardHead)
    headObserver.observe(editorEl.value)
  }
})
onUnmounted(() => headObserver?.disconnect())

/**
 * Folding from a pinned head: the content the reader was in vanishes from above
 * them, which would drop them further down the batch. Hold the head where it
 * was on screen instead — it also absorbs the reflow when a group opens on the
 * cards above this one, the groups being shared across cards.
 */
async function keepHeadInView(head: HTMLElement | null): Promise<void> {
  if (!head) return
  const before = head.getBoundingClientRect().top
  await nextTick()
  const after = head.getBoundingClientRect().top
  if (Math.abs(after - before) > 1) window.scrollBy(0, after - before)
}

// --- Field groups --------------------------------------------------------
// The editor used to render one input per column in a single grid, which is 70
// to 150 inputs for a real database. Same categories as the filter rail, so a
// contributor fills in identification, then geometry, then material.
const columnGroups = computed(() =>
  store.database ? groupBy(store.database, store.columns, (column) => column) : []
)

// Every group starts folded: an open card then shows its problems and its group
// headings on one screen, and the contributor opens what they need.
const openFieldGroups = ref<Set<FieldGroupId>>(new Set<FieldGroupId>())

function toggleFieldGroup(id: FieldGroupId, event?: MouseEvent): void {
  const next = new Set(openFieldGroups.value)
  if (!next.delete(id)) next.add(id)
  openFieldGroups.value = next
  if (event) void keepHeadInView(event.currentTarget as HTMLElement)
}

const allFieldGroupsOpen = computed(
  () =>
    columnGroups.value.length > 0 &&
    columnGroups.value.every((group) => openFieldGroups.value.has(group.id))
)

function toggleAllFieldGroups(event?: MouseEvent): void {
  openFieldGroups.value = allFieldGroupsOpen.value
    ? new Set<FieldGroupId>()
    : new Set(columnGroups.value.map((group) => group.id))
  if (event) void keepHeadInView(event.currentTarget as HTMLElement)
}

/** Cell problems this row has inside one group, by level, so the head carries
 *  the same counts as the card. A draft's "still to fill in" hints do not
 *  count. Clicking a problem opens the group it points at, so a folded heading
 *  never hides a cell the contributor has to fix. */
function issuesIn(uid: number, columns: { name: string }[], level: 'error' | 'warn'): number {
  return columns.filter((column) => store.cellIssueFor(uid, column.name)?.level === level).length
}

/** The count in a group head is a shortcut to its first problem of that level:
 *  one warning behind a folded heading is then one click away, without opening
 *  the group and reading it, or scrolling back to the list on top. */
function goToGroupIssue(uid: number, columns: { name: string }[], level: 'error' | 'warn'): void {
  const names = new Set(columns.map((column) => column.name))
  const issue = store
    .activeIssuesFor(uid)
    .find((entry) => entry.level === level && entry.column && names.has(entry.column))
  if (issue) void goToIssue(uid, issue)
}

/** Which group a column landed in, for the jump-to-field path below. */
const groupOfColumn = computed(() => {
  const lookup = new Map<string, FieldGroupId>()
  columnGroups.value.forEach((group) => {
    group.items.forEach((column) => lookup.set(column.name, group.id))
  })
  return lookup
})

/**
 * A card is only green once the server has actually judged it. Until then it
 * reads as pending, so a batch does not flash "No issues" the moment it loads.
 * A draft (just added by hand) reads as work in progress instead, and while it
 * holds the check back the other cards have no verdict either.
 */
function cardState(uid: number): 'fail' | 'warn' | 'draft' | 'checking' | 'unchecked' | 'pass' {
  const level = store.levelFor(uid)
  if (level !== 'pass') return level
  // Something still to do (a blank field, a file to attach) reads the same
  // way as a draft: not there yet, not a verdict.
  if (store.isDraft(uid) || store.todoFor(uid).length) return 'draft'
  if (store.checking) return 'checking'
  return store.unverified || store.checkPaused ? 'unchecked' : 'pass'
}

/** The badge of a card with hints: blank fields are counted, files are named. */
function todoLabel(uid: number): string {
  const todos = store.todoFor(uid)
  const fields = todos.filter((issue) => issue.column).length
  if (fields > 0) return t('contribute.editor.todo_count', { count: fields })
  return t('contribute.editor.todo_files')
}

/**
 * The element a problem points at: its field input, or its test-data row. A
 * problem about test data as a whole (none attached) points at the first slot.
 */
function targetId(uid: number, issue: CardIssue): string {
  if (issue.column) return `f-${uid}-${issue.column}`
  return `s-${uid}-${issue.kindKey ?? kinds.value[0]?.key}`
}

// Briefly outlines the element a problem was just clicked from, so the jump is
// visible when the target is already on screen.
const flashed = ref('')

function flash(id: string): void {
  flashed.value = id
  window.setTimeout(() => {
    if (flashed.value === id) flashed.value = ''
  }, 1600)
}

async function goToIssue(uid: number, issue: CardIssue): Promise<void> {
  const id = targetId(uid, issue)
  // Unfold the group first, or the input this points at is not in the DOM yet.
  const group = issue.column ? groupOfColumn.value.get(issue.column) : undefined
  if (group && !openFieldGroups.value.has(group)) toggleFieldGroup(group)
  await nextTick()
  const element = document.getElementById(id)
  if (!element) return
  element.scrollIntoView({ block: 'center', behavior: 'smooth' })
  element.focus({ preventScroll: true })
  flash(id)
}

/** Open an experiment and bring it on screen, from the summary under the status bar. */
async function reveal(uid: number): Promise<void> {
  if (!expanded.value.has(uid)) toggle(uid)
  await nextTick()
  const element = document.getElementById(`x-${uid}`)
  if (!element) return
  element.scrollIntoView({ block: 'start', behavior: 'smooth' })
  flash(`x-${uid}`)
}

/** Open an experiment and jump to one of its problems. */
async function revealIssue(uid: number, issue: CardIssue): Promise<void> {
  if (!expanded.value.has(uid)) toggle(uid)
  await nextTick()
  await goToIssue(uid, issue)
}

defineExpose({ reveal, revealIssue })

// --- Expand / collapse ---------------------------------------------------
/** Cards whose dismissed-warning list is unfolded. */
const showDismissed = ref<Set<number>>(new Set())
function toggleDismissed(uid: number): void {
  const next = new Set(showDismissed.value)
  if (!next.delete(uid)) next.add(uid)
  showDismissed.value = next
}

function issueCount(uid: number, level: 'error' | 'warn'): number {
  return store.activeIssuesFor(uid).filter((issue) => issue.level === level).length
}

const expanded = ref<Set<number>>(new Set())

/** A hand-added experiment opens straight away: there is nothing to see folded. */
function addExperiment(): void {
  const uid = store.addRow()
  expanded.value = new Set([...expanded.value, uid])
}

function toggle(uid: number, event?: MouseEvent): void {
  const next = new Set(expanded.value)
  if (next.has(uid)) {
    next.delete(uid)
    // Folding a draft away reads as "done with it".
    store.settle(uid)
  } else next.add(uid)
  expanded.value = next
  if (event) void keepHeadInView(event.currentTarget as HTMLElement)
}

// --- Intake ----------------------------------------------------------------
// One zone takes the whole submission: the primary CSV, the curve files, a
// folder holding both, or a zip of it. `utils/intake.ts` places every file
// and the store applies the plan; what could not be placed is listed in the
// report below the zone for the contributor to resolve.

/** The zone is the whole stage while nothing is entered, a strip afterwards. */
const isEmptyBatch = computed(() => store.rows.length === 0)

const filesInput = ref<HTMLInputElement>()
const folderInput = ref<HTMLInputElement>()
/** Files being read, for the progress note; 0 when idle. */
const reading = ref(0)

// One drag counter per drop target (see below): dragenter/dragleave also fire
// for children, so count them instead of toggling a flag. A slot is keyed like
// `store.timeSeries`, the intake zone is `intake`.
const dragOver = ref<Record<string, number>>({})
function dragEnter(key: string): void {
  dragOver.value[key] = (dragOver.value[key] ?? 0) + 1
}
function dragLeave(key: string): void {
  dragOver.value[key] = Math.max(0, (dragOver.value[key] ?? 0) - 1)
}
function isOver(key: string): boolean {
  return (dragOver.value[key] ?? 0) > 0
}

/** The folder names of the response types, for the zone's hint. */
const kindFolders = computed(() =>
  kinds.value.map((kind) => kind.directory.slice(kind.directory.lastIndexOf('/') + 1)).join(', ')
)

/** One line for the snackbar; the report under the zone carries the detail. */
function intakeLine(summary: IntakeSummary, plan: IntakePlan): string {
  const parts: string[] = []
  if (summary.primaryName) {
    parts.push(t('contribute.intake.loaded', { added: summary.added, updated: summary.updated }))
  }
  const attached = Object.values(summary.attached).reduce((total, count) => total + count, 0)
  if (attached) parts.push(t('contribute.intake.attached', { count: attached }))
  const assumed = Object.values(summary.assumed).reduce((total, count) => total + count, 0)
  if (assumed) parts.push(t('contribute.intake.assumed', { count: assumed }))
  if (plan.pending.length)
    parts.push(t('contribute.intake.to_resolve', { count: plan.pending.length }))
  if (parts.length === 0) parts.push(t('contribute.intake.nothing'))
  return parts.join(' ')
}

async function intake(files: IntakeFile[]): Promise<void> {
  if (files.length === 0 || !store.database || !store.config) return
  reading.value = files.length
  try {
    const expanded = await expandArchives(files)
    reading.value = expanded.length
    const csvPath = store.config.csvPath
    const plan = await classifyIntake(expanded, {
      columns: store.columns.map((column) => column.name),
      primaryName: csvPath.slice(csvPath.lastIndexOf('/') + 1),
      kinds: kinds.value,
      ids: store.specimenIds,
      aliases: (kind) => [t(`contribute.timeseries.kind.${kind.key}`)]
    })
    const summary = store.applyIntake(plan)
    notification.notify(intakeLine(summary, plan))
  } catch (caught) {
    notification.notify(caught instanceof Error ? caught.message : String(caught))
  } finally {
    reading.value = 0
  }
}

async function onIntakeDrop(event: DragEvent): Promise<void> {
  dragOver.value.intake = 0
  if (!event.dataTransfer) return
  // The directory entries must be read before anything awaits (see intake.ts).
  const files = await collectFromDataTransfer(event.dataTransfer)
  await intake(files)
}

async function onIntakePick(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const files = collectFromFileList(input.files ?? [])
  input.value = ''
  await intake(files)
}

// --- Time-series attach, one slot at a time ------------------------------
const slotInputs = ref<Record<string, HTMLInputElement | null>>({})

async function attachFile(uid: number, kind: TimeSeriesKind, file: File): Promise<void> {
  store.attachSeries(uid, kind, file.name, await file.text())
}

async function onSlotAttach(uid: number, kind: TimeSeriesKind, event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (file) await attachFile(uid, kind, file)
}

/** A file dropped on a slot lands there whatever its name; a second file is ignored. */
async function onSlotDrop(uid: number, kind: TimeSeriesKind, event: DragEvent): Promise<void> {
  dragOver.value[`${uid}:${kind.key}`] = 0
  const files = Array.from(event.dataTransfer?.files ?? [])
  if (files.length === 0) return
  if (files.length > 1) notification.notify(t('contribute.editor.drop_one_file'))
  await attachFile(uid, kind, files[0])
}

// The same colour convention as the curation review (#268): what the contributor
// submits is drawn in --data-submitted, so the two screens read alike.
const hasCurves = computed(() => Object.keys(store.timeSeries).length > 0)
const legendItems = computed<DataLegendItem[]>(() => [
  { kind: 'submitted', label: t('contribute.legend.submitted') }
])

function chart(uid: number, kind: TimeSeriesKind) {
  const attached = store.timeSeries[`${uid}:${kind.key}`]
  return attached ? sparkline(attached.report.x, attached.report.y) : null
}

/** The live problems of one slot, shown under the file. */
function seriesIssues(uid: number, kind: TimeSeriesKind): CardIssue[] {
  return store.activeIssuesFor(uid).filter((issue) => issue.kindKey === kind.key)
}

/** The file name a slot expects for this experiment, `<id>` while it has none. */
function expectedName(uid: number, kind: TimeSeriesKind): string {
  const id = (store.rowByUid(uid)?.cells.id ?? '').trim()
  return `${fileStemFor(kind, id || '<id>')}.csv`
}

/** The sign / content conventions of a kind, when the README states any. */
function noteFor(kind: TimeSeriesKind): string {
  const key = `contribute.timeseries.note.${kind.key}`
  return te(key) ? t(key) : ''
}
</script>

<template>
  <div ref="editorEl" class="block editor" :style="{ '--card-head-h': cardHeadHeight }">
    <!-- Section bar: what this block is on the left, its tools on the right. -->
    <div class="block-bar">
      <h2 class="block-h">
        {{ $t('contribute.editor.title') }}
        <span v-if="!isEmptyBatch" class="count">{{ store.rows.length }}</span>
      </h2>
      <div class="toolbar">
        <button
          class="btn btn-secondary btn-sm"
          type="button"
          :title="$t('contribute.editor.starter_kit_hint')"
          @click="downloadStarterKit(store.database!, store.columns, kinds)"
        >
          <v-icon :icon="mdiPackageVariantClosed" size="14" />{{
            $t('contribute.editor.starter_kit')
          }}
        </button>
        <button
          class="btn btn-ghost btn-sm"
          type="button"
          @click="downloadTemplate(store.database!, store.columns)"
        >
          <v-icon :icon="mdiDownloadOutline" size="14" />{{ $t('contribute.editor.template') }}
        </button>
        <button
          class="btn btn-ghost btn-sm"
          type="button"
          @click="downloadDictionary(store.database!, store.columns)"
        >
          <v-icon :icon="mdiDownloadOutline" size="14" />{{ $t('contribute.editor.dictionary') }}
        </button>
        <button class="btn btn-ghost btn-sm" type="button" @click="emit('open-guide', 'guide')">
          <v-icon :icon="mdiBookOpenPageVariantOutline" size="14" />{{
            $t('contribute.editor.guide')
          }}
        </button>
      </div>
    </div>
    <data-legend v-if="hasCurves" class="legend" :items="legendItems" />

    <div v-if="isEmptyBatch" class="intro">
      <p>{{ $t('contribute.editor.intro') }}</p>
      <p v-if="kinds.length">{{ $t('contribute.editor.intro_files') }}</p>
      <p>
        {{ $t('contribute.editor.intro_guide') }}
        <button class="link" type="button" @click="emit('open-guide', 'guide')">
          {{ $t('contribute.editor.guide') }}
        </button>
      </p>
    </div>

    <!-- Intake: the whole submission at once — a folder, a zip, or files. -->
    <div
      class="intake"
      :class="{ over: isOver('intake'), compact: !isEmptyBatch, reading: reading > 0 }"
      @dragenter.prevent="dragEnter('intake')"
      @dragover.prevent
      @dragleave.prevent="dragLeave('intake')"
      @drop.prevent="onIntakeDrop"
    >
      <v-icon class="intake-icon" :icon="mdiTrayArrowUp" :size="isEmptyBatch ? 30 : 20" />
      <div class="intake-text">
        <span class="drop-title">{{ $t('contribute.intake.title') }}</span>
        <span class="drop-hint">
          {{
            kinds.length
              ? $t('contribute.intake.hint_files', { folders: kindFolders })
              : $t('contribute.intake.hint_csv')
          }}
        </span>
      </div>
      <div class="intake-actions">
        <button class="btn btn-secondary btn-sm" type="button" @click="folderInput?.click()">
          <v-icon :icon="mdiFolderOutline" size="14" />{{ $t('contribute.intake.choose_folder') }}
        </button>
        <button class="btn btn-secondary btn-sm" type="button" @click="filesInput?.click()">
          <v-icon :icon="mdiTrayArrowUp" size="14" />{{ $t('contribute.intake.choose_files') }}
        </button>
      </div>
      <input
        ref="filesInput"
        accept=".csv,.zip,text/csv,application/zip"
        hidden
        multiple
        type="file"
        @change="onIntakePick"
      />
      <input ref="folderInput" hidden multiple type="file" webkitdirectory @change="onIntakePick" />
      <span v-if="reading" class="intake-reading">
        {{ $t('contribute.intake.reading', { count: reading }) }}
      </span>
    </div>

    <intake-report v-if="store.lastIntake || store.pendingFiles.length" />

    <article
      v-for="(row, index) in store.rows"
      :id="`x-${row.uid}`"
      :key="row.uid"
      class="card"
      :class="[
        store.levelFor(row.uid),
        { flashed: flashed === `x-${row.uid}`, open: expanded.has(row.uid) }
      ]"
    >
      <button class="card-head" type="button" @click="toggle(row.uid, $event)">
        <v-icon
          class="chevron"
          :class="{ open: expanded.has(row.uid) }"
          :icon="mdiChevronRight"
          size="18"
        />
        <span class="state">
          <span v-if="cardState(row.uid) === 'checking'" class="spinner" />
          <span v-else class="dot" :class="cardState(row.uid)" />
        </span>
        <span class="card-id">
          {{ row.cells.id?.trim() || $t('contribute.editor.untitled', { n: index + 1 }) }}
        </span>
        <span class="headline">
          <span v-for="column in headlineColumns" :key="column.name" class="headline-item">
            <span class="k"
              ><code class="col-name">{{ column.name }}</code></span
            >
            <span class="v">{{ row.cells[column.name]?.trim() || '—' }}</span>
          </span>
        </span>
        <span v-if="kinds.length" class="kinds">
          <span
            v-for="kind in kinds"
            :key="kind.key"
            class="kind-chip"
            :class="store.kindStatus(row.uid, kind)"
            :title="`${$t(`contribute.timeseries.kind.${kind.key}`)}: ${$t(
              `contribute.timeseries.state.${store.kindStatus(row.uid, kind)}`
            )}`"
          >
            <span class="kind-dot" />{{ $t(`contribute.timeseries.short.${kind.key}`) }}
          </span>
        </span>
        <span class="badge" :class="cardState(row.uid)">
          <template v-if="store.activeIssuesFor(row.uid).length">
            <span class="issue-counts">
              <span v-if="issueCount(row.uid, 'error')" class="n error">
                {{ issueCount(row.uid, 'error') }}<v-icon :icon="mdiAlertCircleOutline" size="13" />
              </span>
              <span v-if="issueCount(row.uid, 'warn')" class="n warn">
                {{ issueCount(row.uid, 'warn') }}<v-icon :icon="mdiAlertOutline" size="13" />
              </span>
            </span>
            <span class="issue-text">
              {{
                $t('contribute.editor.issue_count', {
                  count: store.activeIssuesFor(row.uid).length
                })
              }}
            </span>
          </template>
          <template v-else-if="cardState(row.uid) === 'draft' && store.todoFor(row.uid).length">
            {{ todoLabel(row.uid) }}
          </template>
          <template v-else-if="cardState(row.uid) === 'checking'">
            {{ $t('contribute.editor.checking') }}
          </template>
          <template v-else-if="cardState(row.uid) === 'unchecked'">
            {{ $t('contribute.editor.unchecked') }}
          </template>
          <template v-else>
            <span class="issue-counts" :title="$t('contribute.editor.clean')">
              <span class="n"><v-icon :icon="mdiCheckCircleOutline" size="13" /></span>
            </span>
            <span class="issue-text">{{ $t('contribute.editor.clean') }}</span>
          </template>
        </span>
        <span v-if="store.dismissedIssuesFor(row.uid).length" class="badge muted">
          <v-icon :icon="mdiBellOffOutline" size="13" />
          {{ store.dismissedIssuesFor(row.uid).length }}
        </span>
      </button>

      <div v-if="expanded.has(row.uid)" class="card-body">
        <div class="card-actions">
          <button class="card-action" type="button" @click="toggleAllFieldGroups($event)">
            <v-icon
              :icon="allFieldGroupsOpen ? mdiUnfoldLessHorizontal : mdiUnfoldMoreHorizontal"
              size="14"
            />
            {{
              allFieldGroupsOpen
                ? $t('contribute.editor.collapse_groups')
                : $t('contribute.editor.expand_groups')
            }}
          </button>
          <button class="card-action" type="button" @click="store.duplicateRow(row.uid)">
            <v-icon :icon="mdiContentCopy" size="14" />{{ $t('contribute.editor.duplicate') }}
          </button>
          <button class="card-action danger" type="button" @click="store.removeRow(row.uid)">
            <v-icon :icon="mdiClose" size="14" />{{ $t('contribute.editor.remove') }}
          </button>
        </div>

        <section
          v-if="store.activeIssuesFor(row.uid).length || store.dismissedIssuesFor(row.uid).length"
          class="card-section"
        >
          <h3>{{ $t('contribute.editor.problems') }}</h3>

          <div
            v-for="issue in store.activeIssuesFor(row.uid)"
            :key="issue.key"
            class="issue"
            :class="issue.level"
          >
            <button class="issue-go" type="button" @click="goToIssue(row.uid, issue)">
              <v-icon :icon="mdiAlertOutline" size="14" />
              <span>
                <template v-if="issue.column"
                  ><code class="col-name">{{ issue.column }}</code
                  >:
                </template>
                <template v-else-if="issue.kindKey">
                  {{ $t(`contribute.timeseries.kind.${issue.kindKey}`) }}:
                </template>
                {{ issue.message }}
              </span>
            </button>
            <button
              v-if="issue.level === 'warn'"
              class="issue-action"
              type="button"
              :title="$t('contribute.editor.dismiss_hint')"
              @click="store.dismissIssue(issue.key)"
            >
              <v-icon :icon="mdiClose" size="14" />
              <span class="sr-only">{{ $t('contribute.editor.dismiss') }}</span>
            </button>
          </div>

          <!-- Dismissed warnings stay available, folded away by default. -->
          <div v-if="store.dismissedIssuesFor(row.uid).length" class="dismissed">
            <button class="dismissed-toggle" type="button" @click="toggleDismissed(row.uid)">
              <v-icon
                class="chevron"
                :class="{ open: showDismissed.has(row.uid) }"
                :icon="mdiChevronRight"
                size="14"
              />
              {{
                $t('contribute.editor.dismissed_count', {
                  count: store.dismissedIssuesFor(row.uid).length
                })
              }}
            </button>
            <button class="link" type="button" @click="store.restoreDismissed(row.uid)">
              {{ $t('contribute.editor.restore_all') }}
            </button>

            <div v-if="showDismissed.has(row.uid)" class="dismissed-list">
              <div
                v-for="issue in store.dismissedIssuesFor(row.uid)"
                :key="issue.key"
                class="issue muted"
              >
                <button class="issue-go" type="button" @click="goToIssue(row.uid, issue)">
                  <v-icon :icon="mdiBellOffOutline" size="14" />
                  <span>
                    <template v-if="issue.column">
                      <code class="col-name">{{ issue.column }}</code
                      >:
                    </template>
                    <template v-else-if="issue.kindKey">
                      {{ $t(`contribute.timeseries.kind.${issue.kindKey}`) }}:
                    </template>
                    {{ issue.message }}
                  </span>
                </button>
                <button
                  class="issue-action"
                  type="button"
                  :title="$t('contribute.editor.restore')"
                  @click="store.restoreIssue(issue.key)"
                >
                  <v-icon :icon="mdiRestore" size="14" />
                  <span class="sr-only">{{ $t('contribute.editor.restore') }}</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        <section class="card-section">
          <h3>{{ $t('contribute.editor.fields') }}</h3>
          <div
            v-for="group in columnGroups"
            :key="group.id"
            class="field-group"
            :class="{ open: openFieldGroups.has(group.id) }"
          >
            <div class="field-group-head">
              <button
                class="field-group-toggle"
                type="button"
                :aria-expanded="openFieldGroups.has(group.id)"
                @click="toggleFieldGroup(group.id, $event)"
              >
                <v-icon
                  class="chevron"
                  :class="{ open: openFieldGroups.has(group.id) }"
                  :icon="mdiChevronRight"
                  size="14"
                />
                <span class="field-group-label">{{ $t(`field_group.${group.id}`) }}</span>
              </button>
              <span class="issue-counts">
                <button
                  v-if="issuesIn(row.uid, group.items, 'error')"
                  class="n error"
                  type="button"
                  :title="$t('contribute.editor.go_to_issue')"
                  @click="goToGroupIssue(row.uid, group.items, 'error')"
                >
                  {{ issuesIn(row.uid, group.items, 'error')
                  }}<v-icon :icon="mdiAlertCircleOutline" size="12" />
                </button>
                <button
                  v-if="issuesIn(row.uid, group.items, 'warn')"
                  class="n warn"
                  type="button"
                  :title="$t('contribute.editor.go_to_issue')"
                  @click="goToGroupIssue(row.uid, group.items, 'warn')"
                >
                  {{ issuesIn(row.uid, group.items, 'warn')
                  }}<v-icon :icon="mdiAlertOutline" size="12" />
                </button>
              </span>
              <span class="field-group-count">{{ group.items.length }}</span>
            </div>
            <div v-if="openFieldGroups.has(group.id)" class="fields">
              <div
                v-for="column in group.items"
                :key="column.name"
                class="field"
                :class="[
                  store.cellIssueFor(row.uid, column.name)?.level,
                  { flashed: flashed === `f-${row.uid}-${column.name}` }
                ]"
              >
                <label :for="`f-${row.uid}-${column.name}`">
                  <code class="col-name">{{ column.name }}</code>
                  <span v-if="!column.nullable" class="required">*</span>
                  <span v-if="column.unit && column.unit !== '-'" class="unit">{{
                    column.unit
                  }}</span>
                  <info-tooltip v-if="column.description">{{ column.description }}</info-tooltip>
                </label>
                <input
                  :id="`f-${row.uid}-${column.name}`"
                  v-model="row.cells[column.name]"
                  type="text"
                  @input="store.touch(row.uid)"
                />
                <small
                  v-if="store.cellIssueFor(row.uid, column.name)"
                  :class="store.cellIssueFor(row.uid, column.name)!.level"
                >
                  {{
                    store.cellIssueFor(row.uid, column.name)!.level === 'todo'
                      ? $t('contribute.editor.todo')
                      : store.cellIssueFor(row.uid, column.name)!.message
                  }}
                </small>
              </div>
            </div>
          </div>
        </section>

        <section v-if="kinds.length" class="card-section">
          <h3>{{ $t('contribute.editor.test_data') }}</h3>
          <div
            v-for="kind in kinds"
            :id="`s-${row.uid}-${kind.key}`"
            :key="kind.key"
            class="series"
            :class="[
              store.kindStatus(row.uid, kind),
              {
                flashed: flashed === `s-${row.uid}-${kind.key}`,
                over: isOver(`${row.uid}:${kind.key}`),
                empty: !store.timeSeries[`${row.uid}:${kind.key}`]
              }
            ]"
            tabindex="-1"
            @dragenter.prevent="dragEnter(`${row.uid}:${kind.key}`)"
            @dragover.prevent
            @dragleave.prevent="dragLeave(`${row.uid}:${kind.key}`)"
            @drop.prevent="onSlotDrop(row.uid, kind, $event)"
          >
            <span class="series-name">
              <span class="series-dot" />
              {{ $t(`contribute.timeseries.kind.${kind.key}`) }}
              <span class="series-tag" :class="{ required: kind.required }">
                {{
                  $t(
                    kind.required
                      ? 'contribute.timeseries.required'
                      : 'contribute.timeseries.optional'
                  )
                }}
              </span>
              <info-tooltip interactive>
                <div class="series-help">
                  <p>
                    <strong>{{ $t('contribute.timeseries.help_columns') }}</strong>
                    <template v-for="(column, i) in kind.columns" :key="column.name">
                      <template v-if="i > 0">, </template>
                      <code>{{ column.name }}</code>
                      <template v-if="column.unit !== '-'"> ({{ column.unit }})</template>
                    </template>
                  </p>
                  <p>
                    {{
                      $t('contribute.timeseries.help_file', { name: expectedName(row.uid, kind) })
                    }}
                  </p>
                  <p v-if="noteFor(kind)">{{ noteFor(kind) }}</p>
                  <p>
                    {{
                      $t(
                        kind.required
                          ? 'contribute.timeseries.help_required'
                          : 'contribute.timeseries.help_optional'
                      )
                    }}
                    <button class="link" type="button" @click="emit('open-guide', 'guide')">
                      {{ $t('contribute.editor.guide') }}
                    </button>
                  </p>
                  <p>
                    <button class="link" type="button" @click="downloadExampleSeries(kind)">
                      {{ $t('contribute.timeseries.help_example') }}
                    </button>
                  </p>
                </div>
              </info-tooltip>
            </span>
            <template v-if="store.timeSeries[`${row.uid}:${kind.key}`]">
              <svg
                v-if="chart(row.uid, kind)"
                class="spark"
                :viewBox="`0 0 ${chart(row.uid, kind)!.width} ${chart(row.uid, kind)!.height}`"
              >
                <polyline :points="chart(row.uid, kind)!.points" />
              </svg>
              <span v-else class="spark spark-empty" />
              <span class="series-meta">
                <span class="series-file">{{
                  store.timeSeries[`${row.uid}:${kind.key}`].name
                }}</span>
                {{
                  $t('contribute.timeseries.rows', {
                    count: store.timeSeries[`${row.uid}:${kind.key}`].rows
                  })
                }}
              </span>
              <button
                class="btn btn-ghost btn-sm"
                type="button"
                @click="store.removeSeries(row.uid, kind)"
              >
                <v-icon :icon="mdiClose" size="13" />{{ $t('contribute.editor.remove') }}
              </button>
              <div v-if="seriesIssues(row.uid, kind).length" class="series-issues">
                <small
                  v-for="issue in seriesIssues(row.uid, kind)"
                  :key="issue.key"
                  :class="issue.level"
                >
                  {{ issue.message }}
                  <button
                    v-if="issue.level === 'warn'"
                    class="link"
                    type="button"
                    :title="$t('contribute.editor.dismiss_hint')"
                    @click="store.dismissIssue(issue.key)"
                  >
                    {{ $t('contribute.editor.dismiss') }}
                  </button>
                </small>
              </div>
            </template>
            <template v-else>
              <button
                class="series-drop"
                type="button"
                @click="slotInputs[`${row.uid}:${kind.key}`]?.click()"
              >
                <v-icon :icon="mdiTrayArrowUp" size="15" />
                {{ $t('contribute.timeseries.drop_here', { name: expectedName(row.uid, kind) }) }}
              </button>
              <input
                :ref="(el) => (slotInputs[`${row.uid}:${kind.key}`] = el as HTMLInputElement)"
                accept=".csv,text/csv"
                hidden
                type="file"
                @change="onSlotAttach(row.uid, kind, $event)"
              />
              <small
                v-if="['missing_required', 'todo'].includes(store.kindStatus(row.uid, kind))"
                class="series-issues"
                :class="store.kindStatus(row.uid, kind) === 'todo' ? 'todo' : 'error'"
              >
                {{ $t(`contribute.timeseries.state.${store.kindStatus(row.uid, kind)}`) }}
              </small>
            </template>
          </div>
        </section>
      </div>
    </article>

    <button class="btn btn-secondary add-manual" type="button" @click="addExperiment()">
      <v-icon :icon="mdiPlus" size="15" />{{ $t('contribute.editor.add_experiment') }}
    </button>
  </div>
</template>

<style scoped>
/* Section chrome — mirrors ContributeView's blocks so both stacks share one
   left edge and one header rhythm. */
.legend {
  margin: -6px 0 16px;
}
.block-bar {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px 20px;
  flex-wrap: wrap;
  padding-bottom: 10px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
}
.block-h {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: var(--title-panel-size);
  font-weight: var(--title-panel-weight);
  text-transform: uppercase;
  letter-spacing: var(--title-panel-tracking);
  color: var(--fg);
}
.block-h .count {
  padding: 0 6px;
  border-radius: 999px;
  background: var(--bg-subtle);
  color: var(--fg-muted);
  font-size: 11px;
  font-weight: 600;
  line-height: 17px;
  letter-spacing: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.intro .link {
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  font-weight: 600;
  text-decoration: underline;
  cursor: pointer;
}

.intro {
  margin-bottom: 16px;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--fg-muted);
  max-width: 76ch;
}
.intro p {
  margin: 0 0 6px;
}
.intro p:last-child {
  margin-bottom: 0;
}

.add-manual {
  width: 100%;
  margin-top: 12px;
  padding: 12px;
  justify-content: center;
  border-style: dashed;
}

/* Intake — the stage while the batch is empty, a strip once it has rows.
   Buttons live inside the zone, so the drag counter (not pointer-events)
   keeps the highlight steady; children stop taking events only mid-drag. */
.intake {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: clamp(28px, 6vh, 44px) 20px;
  margin-bottom: 16px;
  border: 2px dashed var(--border-strong);
  background: var(--bg);
  color: var(--fg-muted);
  text-align: center;
  border-radius: var(--radius);
}
.intake.compact {
  flex-direction: row;
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: 8px 14px;
  padding: 10px 14px;
  border-width: 1px;
  background: var(--bg-subtle);
  text-align: left;
}
.intake.over {
  border-color: var(--epfl-red);
  background: var(--bg-subtle);
  color: var(--epfl-red);
}
.intake.over * {
  pointer-events: none;
}
.intake.reading {
  opacity: 0.7;
}
.intake-icon {
  flex: none;
}
.intake-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 72ch;
}
.intake.compact .intake-text {
  flex: 1 1 260px;
  gap: 2px;
}
.drop-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--fg);
}
.intake.compact .drop-title {
  font-size: 12.5px;
}
.intake.over .drop-title {
  color: var(--epfl-red);
}
.drop-hint {
  font-size: 12px;
  line-height: 1.45;
}
.intake-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}
.intake-reading {
  flex-basis: 100%;
  font-size: 12px;
  font-style: italic;
}

/* How far down the viewport a pinned head has to start: above the mobile
   breakpoint the sidebar is the chrome and nothing overlays the page, below it
   the app header owns the first 56px (`.mhdr` in assets/styles/app.css). */
.editor {
  --stick-top: 0px;
}
@media (max-width: 1023px) {
  .editor {
    --stick-top: 56px;
  }
}

.card {
  border: 1px solid var(--border);
  border-left: 3px solid var(--border-strong);
  margin-bottom: 6px;
  background: var(--bg);
  scroll-margin-top: calc(var(--stick-top) + 12px);
}
.card:last-of-type {
  margin-bottom: 0;
}
.card.fail {
  border-left-color: var(--epfl-red);
}
.card.warn {
  border-left-color: var(--epfl-orange);
}

/* Fixed tracks, not a wrapping flex row: the identifier column and the three
   headline columns then line up from one card to the next, and the verdict
   badge always ends at the same right edge. */
.card-head {
  position: sticky;
  top: var(--stick-top);
  z-index: 2;
  display: grid;
  grid-template-columns: 18px minmax(0, 220px) minmax(0, 1fr) auto auto auto;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 9px 14px;
  border: none;
  /* Opaque, and carrying the body's top rule while pinned: the fields have to
     pass under a line rather than under a floating title. */
  background: var(--bg);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.card.open .card-head {
  border-bottom: 1px solid var(--border-subtle);
}
.card-head:hover {
  background: var(--bg-subtle);
}
.chevron {
  transition: transform 0.15s ease;
}
.chevron.open {
  transform: rotate(90deg);
}
/* The status dot only shows on the roomy layout: the left border and the
   counts already say the same thing, and "Checking…" is in the badge. */
.state {
  display: none;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--epfl-green-text);
  flex: none;
}
.dot.warn {
  background: var(--epfl-orange);
}
.dot.fail {
  background: var(--epfl-red);
}
.dot.unchecked {
  background: var(--border-strong);
}
/* A draft: hollow, so it reads as "not there yet" rather than as a verdict. */
.dot.draft {
  box-sizing: border-box;
  border: 1.5px solid var(--border-strong);
  background: transparent;
}
/* Sits in the status dot's place while the server verdict is pending — same
   box as .dot (border included) so swapping the two shifts nothing. */
.spinner {
  box-sizing: border-box;
  width: 9px;
  height: 9px;
  flex: none;
  border: 1.5px solid var(--border-strong);
  border-top-color: var(--fg-muted);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation-duration: 2.4s;
  }
}
.card-id {
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.headline {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
  min-width: 0;
}
.headline-item {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.headline-item .k {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--fg-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* The small uppercase key holds a raw column name: keep its case and size. */
.headline-item .k .col-name {
  font-size: 10.5px;
  font-weight: 500;
}
.headline-item .v {
  font-size: 12.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.badge {
  font-size: 12px;
  font-weight: 600;
  text-align: right;
  color: var(--epfl-green-text);
}
.badge.warn {
  color: var(--epfl-orange);
}
.badge.fail {
  color: var(--epfl-red);
}
.badge.checking,
.badge.unchecked,
.badge.draft {
  color: var(--fg-muted);
  font-weight: 400;
}
.badge.muted {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  min-width: 0;
  color: var(--fg-muted);
  font-weight: 400;
}
/* "1 (!) 4 (⚠)": a count per level, the icon says which, and a lone green tick
   when there is none. The words are for the roomy layout only. */
.issue-counts {
  display: inline-flex;
  gap: 8px;
}
.issue-counts .n {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-variant-numeric: tabular-nums;
}
.issue-counts .n.error {
  color: var(--epfl-red);
}
.issue-counts .n.warn {
  color: var(--epfl-orange);
}
.issue-text {
  display: none;
}
/* Laptop and below: the headline columns no longer fit beside the identifier
   and the verdict, so they drop rather than squeeze to two characters. */
@media (max-width: 1023px) {
  .card-head {
    grid-template-columns: 18px minmax(0, 1fr) auto auto auto;
  }
  .headline {
    display: none;
  }
}
@media (max-width: 559px) {
  .kind-chip .kind-label {
    display: none;
  }
}

/* One chip per response type: a dot in the slot's state and a short label.
   The dot alone carries the state so the row stays quiet; red and orange
   mean the same as on the card, hollow means "nothing there yet". */
.kinds {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.kind-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--fg-muted);
  white-space: nowrap;
}
.kind-dot,
.series-dot {
  box-sizing: border-box;
  width: 7px;
  height: 7px;
  flex: none;
  border-radius: 50%;
  border: 1.5px solid var(--border-strong);
  background: transparent;
}
.kind-chip.ok,
.series.ok .series-dot {
  color: var(--fg);
}
.kind-chip.ok .kind-dot,
.series.ok .series-dot {
  border-color: var(--epfl-green-text);
  background: var(--epfl-green-text);
}
.kind-chip.warn,
.kind-chip.error,
.kind-chip.missing_required {
  color: var(--fg);
}
.kind-chip.warn .kind-dot,
.series.warn .series-dot {
  border-color: var(--epfl-orange);
  background: var(--epfl-orange);
}
.kind-chip.error .kind-dot,
.series.error .series-dot {
  border-color: var(--epfl-red);
  background: var(--epfl-red);
}
.kind-chip.missing_required .kind-dot,
.series.missing_required .series-dot {
  border-color: var(--epfl-red);
  background: transparent;
}
/* Still to attach (a draft, or a batch whose files have not started
   arriving): hollow like "missing", dotted so it reads as a to-do. */
.kind-chip.todo .kind-dot,
.series.todo .series-dot {
  border-style: dotted;
  border-color: var(--fg-muted);
  background: transparent;
}
@media (max-width: 559px) {
  .card-head {
    padding: 12px;
  }
  .badge {
    min-width: 0;
  }
}

.card-body {
  padding: 12px 14px;
}
/* One strip of card chrome, right under the head: the view control on the left,
   the row actions on the right. Full bleed, so it reads as part of the card and
   not as two buttons floating over an empty line. */
.card-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  margin: -12px -14px 10px;
  padding: 3px 8px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-subtle);
}
.card-actions .card-action:first-child {
  margin-right: auto;
}
.card-action {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  border: none;
  border-radius: var(--radius);
  background: transparent;
  color: var(--fg-muted);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
  transition: color var(--t-fast);
}
.card-action:hover {
  color: var(--fg);
}
.card-action.danger:hover {
  color: var(--epfl-red);
}
.card-section + .card-section {
  margin-top: 16px;
}
.card-section h3 {
  padding-bottom: 6px;
  margin: 0 0 8px;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
}

.issue {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 2px;
  font-size: 12.5px;
}
.issue.error {
  color: var(--epfl-red);
}
.issue.warn {
  color: var(--epfl-orange);
}
.issue.muted {
  color: var(--fg-muted);
}
/* The message itself is the jump-to-field control. */
.issue-go {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
  padding: 2px 4px;
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  border-radius: var(--radius);
}
.issue-go:hover,
.issue-go:focus-visible {
  background: var(--bg-subtle);
  text-decoration: underline;
}
.issue-action {
  display: flex;
  flex: none;
  padding: 4px;
  border: none;
  background: transparent;
  color: var(--fg-muted);
  cursor: pointer;
  border-radius: var(--radius);
}
.issue-action:hover,
.issue-action:focus-visible {
  background: var(--bg-subtle);
  color: var(--fg);
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.dismissed {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.dismissed-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 0;
  border: none;
  background: transparent;
  color: var(--fg-muted);
  font: inherit;
  font-size: 12.5px;
  cursor: pointer;
}
.dismissed-toggle:hover {
  color: var(--fg);
}
.link {
  border: none;
  background: transparent;
  color: var(--fg-muted);
  font: inherit;
  font-size: 12.5px;
  text-decoration: underline;
  cursor: pointer;
}
.link:hover {
  color: var(--fg);
}
.dismissed-list {
  flex-basis: 100%;
  padding-left: 12px;
  border-left: 2px solid var(--border-subtle);
}

.field-group + .field-group {
  margin-top: 4px;
}
/* Pinned right under the card head it belongs to, and only for as long as its
   own fields are on screen — the next group's head takes over from there. */
.field-group-head {
  position: sticky;
  top: calc(var(--stick-top) + var(--card-head-h, 44px));
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 8px;
  background: var(--bg);
  border-radius: 4px;
  color: var(--fg);
}
.field-group-head:hover {
  background: var(--bg-subtle);
}
/* The heading folds, the counts beside it jump to a problem, so they are two
   buttons and not one. The toggle takes the whole free width all the same. */
.field-group-toggle {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}
.field-group-head .chevron {
  flex: 0 0 auto;
  color: var(--fg-muted);
  transition: transform var(--t-fast);
}
.field-group-head .chevron.open {
  transform: rotate(90deg);
}
.field-group-label {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.field-group-count {
  flex: 0 0 auto;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--fg-muted);
}
.field-group-head .issue-counts {
  flex: 0 0 auto;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
}
.field-group-head .issue-counts .n {
  padding: 0 2px;
  border: 0;
  border-radius: 3px;
  background: none;
  font: inherit;
  cursor: pointer;
}
.field-group-head .issue-counts .n:hover {
  background: var(--bg);
  text-decoration: underline;
}
.field-group.open .fields {
  padding: 4px 8px 10px;
}

.fields {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 8px 16px;
}
.field label {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 2px 5px;
  margin-bottom: 3px;
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.3;
}
.field .required {
  color: var(--epfl-red);
}
.field .unit {
  padding: 0 6px;
  background: var(--bg-subtle);
  font-size: 11px;
  font-weight: 400;
  color: var(--fg-muted);
}
.field input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  font-size: 13px;
  border-radius: var(--radius);
}
.field input:focus {
  outline: 2px solid var(--epfl-red);
  outline-offset: -1px;
}
.field.error input {
  border-color: var(--epfl-red);
}
.field.warn input {
  border-color: var(--epfl-orange);
}
.field small {
  display: block;
  margin-top: 3px;
  font-size: 11.5px;
}
.field small.error {
  color: var(--epfl-red);
}
.field small.warn {
  color: var(--epfl-orange);
}
/* A draft's blank required field: a hint, in the label's grey, no border. */
.field small.todo {
  color: var(--fg-muted);
}
.field.flashed input,
.series.flashed,
.card.flashed {
  animation: flash 1.6s ease-out;
}
@keyframes flash {
  0%,
  60% {
    box-shadow: 0 0 0 3px var(--epfl-red-soft, rgba(227, 6, 19, 0.22));
  }
  100% {
    box-shadow: 0 0 0 3px transparent;
  }
}
@media (prefers-reduced-motion: reduce) {
  .field.flashed input,
  .series.flashed,
  .card.flashed {
    animation: none;
    box-shadow: 0 0 0 3px var(--epfl-red-soft, rgba(227, 6, 19, 0.22));
  }
}

/* Name, preview, count, action — fixed tracks so the rows read as a table.
   Every row is a drop target: dropping on an empty slot fills it, on a filled
   one replaces the file. */
.series {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 132px minmax(70px, auto) auto;
  align-items: center;
  gap: 10px 14px;
  padding: 10px 6px;
  margin: 0 -6px;
  border-bottom: 1px solid var(--border-subtle);
  border-radius: var(--radius);
}
.series:last-child {
  border-bottom: none;
}
.series.over {
  outline: 2px dashed var(--epfl-red);
  outline-offset: -2px;
  background: var(--bg-subtle);
}
/* While a file hovers, the children must not steal dragenter/dragleave. */
.series.over * {
  pointer-events: none;
}
.series .spark {
  grid-column: 2;
}
.series-meta {
  grid-column: 3;
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.series-file {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--fg);
}
.series .btn-ghost {
  grid-column: 4;
}
/* Nothing attached yet: a dashed target takes the preview and count tracks. */
.series-drop {
  grid-column: 2 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 14px;
  border: 1.5px dashed var(--border-strong);
  background: transparent;
  color: var(--fg-muted);
  font: inherit;
  font-size: 12.5px;
  cursor: pointer;
  border-radius: var(--radius);
}
.series-drop:hover,
.series-drop:focus-visible {
  border-color: var(--epfl-red);
  color: var(--fg);
  background: var(--bg-subtle);
}
.series.missing_required .series-drop {
  border-color: var(--epfl-red);
}
.series-issues {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11.5px;
  line-height: 1.4;
}
.series-issues.error,
.series-issues .error {
  color: var(--epfl-red);
}
.series-issues .warn {
  color: var(--epfl-orange);
}
.series-issues.todo {
  color: var(--fg-muted);
}
.series-issues .link {
  margin-left: 4px;
  font-size: 11.5px;
}
.series-name {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 13px;
  font-weight: 600;
}
.series-tag {
  padding: 0 5px;
  border-radius: 999px;
  background: var(--bg-subtle);
  color: var(--fg-muted);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.series-tag.required {
  color: var(--epfl-red);
}
.series-help {
  font-size: 12.5px;
  line-height: 1.5;
}
.series-help p {
  margin: 0 0 6px;
}
.series-help p:last-child {
  margin-bottom: 0;
}
.series-help code {
  padding: 0 3px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 12px;
}
.series-help .link {
  color: inherit;
  font-size: inherit;
}
.series-meta {
  font-size: 12px;
  color: var(--fg-muted);
}
.spark-empty {
  display: block;
}
.spark {
  grid-column: 2;
}
.series-meta {
  grid-column: 3;
}
.series .btn-ghost {
  grid-column: 4;
}
/* Nothing attached yet: the attach button takes the preview and count tracks. */
.series .btn-secondary {
  grid-column: 2 / -1;
  justify-self: start;
}
.series-name {
  font-size: 13px;
  font-weight: 600;
}
/* Below 700px: name and action on the first row, the preview under them. Kept
   after the base track rules above, which would win otherwise. */
@media (max-width: 700px) {
  .series {
    grid-template-columns: minmax(0, 1fr) auto;
  }
  .series .spark {
    grid-column: 1 / -1;
    grid-row: 2;
  }
  .series-meta,
  .series .btn-ghost,
  .series .btn-secondary {
    grid-column: 2;
  }
  .series-drop {
    grid-column: 1 / -1;
  }
}
.series-meta {
  font-size: 12px;
  color: var(--fg-muted);
}
.spark {
  width: 132px;
  height: 40px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-subtle);
}
.spark polyline {
  fill: none;
  stroke: var(--data-submitted);
  stroke-width: 1.4;
  stroke-linejoin: round;
  stroke-linecap: round;
}

/* Roomy layout, for screens wider than a laptop: the status dot is back, the
   verdict is spelled out, and labels reserve two lines so the inputs of a row
   share a baseline. Everything above is the dense default, which a 13" laptop
   needs. */
@media (min-width: 1600px) {
  .card {
    margin-bottom: 10px;
  }
  .card-head {
    grid-template-columns: 18px 9px minmax(0, 220px) minmax(0, 1fr) auto auto auto;
    gap: 14px;
    padding: 13px 16px;
  }
  .state {
    display: flex;
  }
  .card-id {
    font-size: inherit;
    font-weight: 700;
  }
  .headline-item .k {
    font-size: 10.5px;
  }
  .headline-item .v {
    font-size: 13px;
  }
  /* Reserved width: the label swaps between "No issues", "Checking…" and an
     issue count, and the headline next to it would reflow on every change. */
  .badge {
    min-width: 8em;
  }
  .card-head .issue-counts {
    display: none;
  }
  .issue-text {
    display: inline;
  }
  .card-body {
    padding: 16px;
  }
  .card-actions {
    margin: -16px -16px 14px;
    padding: 5px 10px;
  }
  .card-action {
    font-size: 12.5px;
  }
  .card-section + .card-section {
    margin-top: 22px;
  }
  .card-section h3 {
    margin-bottom: 12px;
  }
  .issue {
    margin-bottom: 4px;
    font-size: 13px;
  }
  .issue-go {
    padding: 3px 6px;
  }
  .field label {
    min-height: 32px;
    margin-bottom: 4px;
  }
  .field input {
    padding: 8px 10px;
  }
  .field-group.open .fields {
    padding: 6px 8px 14px;
  }
  .fields {
    gap: 14px 20px;
  }
}
</style>
