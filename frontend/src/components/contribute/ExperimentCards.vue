<script setup lang="ts">
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import ToolSelect from '@/components/commons/tools/ToolSelect.vue'
import { useContributionStore, type CardIssue } from '@/stores/contribution'
import { useNotificationStore } from '@/stores/notification'
import { fieldLabel } from '@/utils/contribution'
import { groupBy, type FieldGroupId } from '@/utils/fieldGroups'
import { readCsvTable } from '@/utils/csv'
import { sparkline } from '@/utils/sparkline'
import { downloadDictionary, downloadTemplate } from '@/utils/templates'
import { checkTimeSeriesFile, timeSeriesKindsFor, type TimeSeriesKind } from '@/utils/timeseries'
import {
  mdiAlertOutline,
  mdiBellOffOutline,
  mdiBookOpenPageVariantOutline,
  mdiChevronRight,
  mdiClose,
  mdiContentCopy,
  mdiDownloadOutline,
  mdiPlus,
  mdiRestore,
  mdiTrayArrowUp,
  mdiUploadOutline
} from '@mdi/js'
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
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

// --- Field groups --------------------------------------------------------
// The editor used to render one input per column in a single grid, which is 70
// to 150 inputs for a real database. Same categories as the filter rail, so a
// contributor fills in identification, then geometry, then material.
const columnGroups = computed(() =>
  store.database ? groupBy(store.database, store.columns, (column) => column) : []
)

const openFieldGroups = ref<Set<FieldGroupId>>(
  new Set<FieldGroupId>(['experimental_program_details'])
)

function toggleFieldGroup(id: FieldGroupId): void {
  const next = new Set(openFieldGroups.value)
  if (!next.delete(id)) next.add(id)
  openFieldGroups.value = next
}

/** Cell problems this row has inside one group, so the head can carry a count. */
function issuesIn(uid: number, columns: { name: string }[]): number {
  return columns.filter((column) => store.cellIssueFor(uid, column.name)).length
}

/** A group holding a problem is always open: a contributor cannot fix what a
 *  collapsed heading is hiding. */
function isFieldGroupOpen(uid: number, id: FieldGroupId, columns: { name: string }[]): boolean {
  return openFieldGroups.value.has(id) || issuesIn(uid, columns) > 0
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
 */
function cardState(uid: number): 'fail' | 'warn' | 'checking' | 'unchecked' | 'pass' {
  const level = store.levelFor(uid)
  if (level !== 'pass') return level
  if (store.checking) return 'checking'
  return store.unverified ? 'unchecked' : 'pass'
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

const expanded = ref<Set<number>>(new Set())

/** A hand-added experiment opens straight away: there is nothing to see folded. */
function addExperiment(): void {
  const uid = store.addRow()
  expanded.value = new Set([...expanded.value, uid])
}

function toggle(uid: number): void {
  const next = new Set(expanded.value)
  if (next.has(uid)) next.delete(uid)
  else next.add(uid)
  expanded.value = next
}

// --- CSV import ----------------------------------------------------------
const importInput = ref<HTMLInputElement>()

/** The drop zone takes the place of the toolbar button while nothing is entered. */
const isEmptyBatch = computed(() => store.rows.length === 0)

// dragenter/dragleave also fire for children, so count them instead of
// toggling a flag — otherwise moving over the icon clears the highlight.
const dragDepth = ref(0)
const dragging = computed(() => dragDepth.value > 0)

async function onDrop(event: DragEvent): Promise<void> {
  dragDepth.value = 0
  const files = Array.from(event.dataTransfer?.files ?? [])
  if (files.length === 0) return
  if (files.length > 1) notification.notify(t('contribute.editor.drop_one_file'))
  await loadCsv(files[0])
}

async function importFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (file) await loadCsv(file)
}

async function loadCsv(file: File): Promise<void> {
  try {
    const columnNames = store.columns.map((column) => column.name)
    const table = readCsvTable(await file.text(), columnNames)
    if (table.matched.length === 0) {
      throw new Error(t('contribute.editor.import_no_match'))
    }
    store.importRows(table.rows)
    let message = t('contribute.editor.import_ok', {
      rows: table.rows.length,
      matched: table.matched.length
    })
    if (table.missing.length) {
      message += ' ' + t('contribute.editor.import_missing', { count: table.missing.length })
    }
    notification.notify(message)
  } catch (caught) {
    notification.notify(caught instanceof Error ? caught.message : String(caught))
  }
}

// --- Time-series attach --------------------------------------------------
const slotInputs = ref<Record<string, HTMLInputElement | null>>({})
const bulkInput = ref<HTMLInputElement>()
const bulkKindKey = ref('')
const bulkKind = computed(() => kinds.value.find((kind) => kind.key === bulkKindKey.value))

function attachText(uid: number, kind: TimeSeriesKind, name: string, text: string): boolean {
  const check = checkTimeSeriesFile(kind, text)
  if (!check.ok) {
    notification.notify(
      check.error === 'empty'
        ? t('contribute.timeseries.error_empty')
        : t('contribute.timeseries.error_columns', { columns: check.missing.join(', ') })
    )
    return false
  }
  store.timeSeries[`${uid}:${kind.key}`] = { name, content: text, rows: check.rows }
  return true
}

async function onSlotAttach(uid: number, kind: TimeSeriesKind, event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (file) attachText(uid, kind, file.name, await file.text())
}

/** Bulk attach: each file's stem is matched (case-sensitively) to an experiment id. */
async function onBulkAttach(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  const kind = bulkKind.value
  if (!kind || files.length === 0) return

  const uidById = new Map(
    store.rows
      .map((row) => [(row.cells.id ?? '').trim(), row.uid] as const)
      .filter(([id]) => id !== '')
  )
  let attached = 0
  const unmatched: string[] = []
  for (const file of files) {
    const uid = uidById.get(file.name.replace(/\.csv$/i, ''))
    if (uid === undefined) {
      unmatched.push(file.name)
      continue
    }
    if (attachText(uid, kind, file.name, await file.text())) attached++
  }
  let message = t('contribute.editor.bulk_result', { attached })
  if (unmatched.length) {
    message += ' ' + t('contribute.editor.bulk_unmatched', { files: unmatched.join(', ') })
  }
  notification.notify(message)
}

function removeSeries(uid: number, kind: TimeSeriesKind): void {
  delete store.timeSeries[`${uid}:${kind.key}`]
}

function chart(uid: number, kind: TimeSeriesKind) {
  const attached = store.timeSeries[`${uid}:${kind.key}`]
  return attached ? sparkline(attached.content) : null
}
</script>

<template>
  <div class="block editor">
    <!-- Section bar: what this block is on the left, its tools on the right. -->
    <div class="block-bar">
      <h2 class="block-h">
        {{ $t('contribute.editor.title') }}
        <span v-if="!isEmptyBatch" class="count">{{ store.rows.length }}</span>
      </h2>
      <div class="toolbar">
        <button
          v-if="!isEmptyBatch"
          class="btn btn-secondary btn-sm"
          type="button"
          @click="importInput?.click()"
        >
          <v-icon :icon="mdiTrayArrowUp" size="14" />{{ $t('contribute.editor.import_csv') }}
        </button>
        <input ref="importInput" accept=".csv,text/csv" hidden type="file" @change="importFile" />
        <button
          class="btn btn-secondary btn-sm"
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

    <button
      v-if="isEmptyBatch"
      class="dropzone"
      :class="{ over: dragging }"
      type="button"
      @click="importInput?.click()"
      @dragenter.prevent="dragDepth++"
      @dragover.prevent
      @dragleave.prevent="dragDepth--"
      @drop.prevent="onDrop"
    >
      <v-icon :icon="mdiTrayArrowUp" size="30" />
      <span class="drop-title">{{ $t('contribute.editor.drop_title') }}</span>
      <span class="drop-hint">{{ $t('contribute.editor.drop_hint') }}</span>
    </button>

    <!-- Bulk attach: pick a response type, drop many <id>.csv files at once. -->
    <div v-if="kinds.length" class="bulk">
      <span class="bulk-label">{{ $t('contribute.editor.bulk_attach') }}</span>
      <tool-select
        v-model="bulkKindKey"
        class="bulk-select"
        :items="
          kinds.map((kind) => ({
            title: $t(`contribute.timeseries.kind.${kind.key}`),
            value: kind.key
          }))
        "
        :placeholder="$t('contribute.editor.bulk_kind')"
      />
      <button
        class="btn btn-secondary btn-sm"
        :disabled="!bulkKind || !store.hasAnyId"
        type="button"
        @click="bulkInput?.click()"
      >
        <v-icon :icon="mdiUploadOutline" size="14" />{{ $t('contribute.editor.bulk_pick') }}
      </button>
      <input
        ref="bulkInput"
        accept=".csv,text/csv"
        hidden
        multiple
        type="file"
        @change="onBulkAttach"
      />
      <span class="bulk-hint">{{ $t('contribute.editor.bulk_hint') }}</span>
    </div>

    <article
      v-for="(row, index) in store.rows"
      :id="`x-${row.uid}`"
      :key="row.uid"
      class="card"
      :class="[store.levelFor(row.uid), { flashed: flashed === `x-${row.uid}` }]"
    >
      <button class="card-head" type="button" @click="toggle(row.uid)">
        <v-icon
          class="chevron"
          :class="{ open: expanded.has(row.uid) }"
          :icon="mdiChevronRight"
          size="18"
        />
        <span v-if="cardState(row.uid) === 'checking'" class="spinner" />
        <span v-else class="dot" :class="cardState(row.uid)" />
        <span class="card-id">
          {{ row.cells.id?.trim() || $t('contribute.editor.untitled', { n: index + 1 }) }}
        </span>
        <span class="headline">
          <span v-for="column in headlineColumns" :key="column.name" class="headline-item">
            <span class="k">{{ fieldLabel(store.database!, column.name) }}</span>
            <span class="v">{{ row.cells[column.name]?.trim() || '—' }}</span>
          </span>
        </span>
        <span class="badge" :class="cardState(row.uid)">
          <template v-if="store.activeIssuesFor(row.uid).length">
            {{
              $t('contribute.editor.issue_count', { count: store.activeIssuesFor(row.uid).length })
            }}
          </template>
          <template v-else-if="cardState(row.uid) === 'checking'">
            {{ $t('contribute.editor.checking') }}
          </template>
          <template v-else-if="cardState(row.uid) === 'unchecked'">
            {{ $t('contribute.editor.unchecked') }}
          </template>
          <template v-else>{{ $t('contribute.editor.clean') }}</template>
        </span>
        <span v-if="store.dismissedIssuesFor(row.uid).length" class="badge muted">
          <v-icon :icon="mdiBellOffOutline" size="13" />
          {{ store.dismissedIssuesFor(row.uid).length }}
        </span>
      </button>

      <div v-if="expanded.has(row.uid)" class="card-body">
        <div class="card-actions">
          <button class="btn btn-ghost btn-sm" type="button" @click="store.duplicateRow(row.uid)">
            <v-icon :icon="mdiContentCopy" size="13" />{{ $t('contribute.editor.duplicate') }}
          </button>
          <button class="btn btn-ghost btn-sm" type="button" @click="store.removeRow(row.uid)">
            <v-icon :icon="mdiClose" size="13" />{{ $t('contribute.editor.remove') }}
          </button>
        </div>

        <section v-if="store.issuesFor(row.uid).length" class="card-section">
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
                  >{{ fieldLabel(store.database!, issue.column) }}:
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
                      {{ fieldLabel(store.database!, issue.column) }}:
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
            :class="{ open: isFieldGroupOpen(row.uid, group.id, group.items) }"
          >
            <button
              class="field-group-head"
              type="button"
              :aria-expanded="isFieldGroupOpen(row.uid, group.id, group.items)"
              @click="toggleFieldGroup(group.id)"
            >
              <v-icon
                class="chevron"
                :class="{ open: isFieldGroupOpen(row.uid, group.id, group.items) }"
                :icon="mdiChevronRight"
                size="14"
              />
              <span class="field-group-label">{{ $t(`field_group.${group.id}`) }}</span>
              <span v-if="issuesIn(row.uid, group.items) > 0" class="field-group-issues">
                {{ issuesIn(row.uid, group.items) }}
              </span>
              <span class="field-group-count">{{ group.items.length }}</span>
            </button>
            <div v-if="isFieldGroupOpen(row.uid, group.id, group.items)" class="fields">
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
                  {{ fieldLabel(store.database!, column.name) }}
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
                />
                <small
                  v-if="store.cellIssueFor(row.uid, column.name)"
                  :class="store.cellIssueFor(row.uid, column.name)!.level"
                >
                  {{ store.cellIssueFor(row.uid, column.name)!.message }}
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
            :class="{ flashed: flashed === `s-${row.uid}-${kind.key}` }"
            tabindex="-1"
          >
            <span class="series-name">{{ $t(`contribute.timeseries.kind.${kind.key}`) }}</span>
            <template v-if="store.timeSeries[`${row.uid}:${kind.key}`]">
              <svg
                v-if="chart(row.uid, kind)"
                class="spark"
                :viewBox="`0 0 ${chart(row.uid, kind)!.width} ${chart(row.uid, kind)!.height}`"
              >
                <polyline :points="chart(row.uid, kind)!.points" />
              </svg>
              <span class="series-meta">
                {{
                  $t('contribute.timeseries.rows', {
                    count: store.timeSeries[`${row.uid}:${kind.key}`].rows
                  })
                }}
              </span>
              <button
                class="btn btn-ghost btn-sm"
                type="button"
                @click="removeSeries(row.uid, kind)"
              >
                <v-icon :icon="mdiClose" size="13" />{{ $t('contribute.editor.remove') }}
              </button>
            </template>
            <template v-else>
              <button
                class="btn btn-secondary btn-sm"
                type="button"
                @click="slotInputs[`${row.uid}:${kind.key}`]?.click()"
              >
                <v-icon :icon="mdiUploadOutline" size="13" />{{
                  $t('contribute.timeseries.attach')
                }}
              </button>
              <input
                :ref="(el) => (slotInputs[`${row.uid}:${kind.key}`] = el as HTMLInputElement)"
                accept=".csv,text/csv"
                hidden
                type="file"
                @change="onSlotAttach(row.uid, kind, $event)"
              />
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

/* Bulk attach — a subdued strip so it reads as a batch tool, not a third row
   of primary actions. Label and hint keep their own rows on narrow screens. */
.bulk {
  display: flex;
  align-items: center;
  gap: 10px 14px;
  flex-wrap: wrap;
  padding: 10px 14px;
  margin-bottom: 16px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-subtle);
  border-radius: var(--radius);
}
.bulk-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--fg);
}
.bulk-select {
  min-width: 220px;
  flex: 0 1 260px;
}
.bulk-hint {
  flex: 1 1 200px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--fg-muted);
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

.dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: clamp(28px, 6vh, 44px) 20px;
  margin-bottom: 16px;
  border: 2px dashed var(--border-strong);
  background: var(--bg);
  color: var(--fg-muted);
  font: inherit;
  cursor: pointer;
  border-radius: var(--radius);
}
.dropzone:hover,
.dropzone:focus-visible {
  border-color: var(--epfl-red);
  background: var(--bg-subtle);
}
.dropzone.over {
  border-color: var(--epfl-red);
  background: var(--bg-subtle);
  color: var(--epfl-red);
}
/* The children would otherwise fire dragleave on the parent as the pointer
   crosses them, and the counter would drift. */
.dropzone * {
  pointer-events: none;
}
.drop-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--fg);
}
.dropzone.over .drop-title {
  color: var(--epfl-red);
}
.drop-hint {
  font-size: 12px;
}

.card {
  border: 1px solid var(--border);
  border-left: 3px solid var(--border-strong);
  margin-bottom: 10px;
  background: var(--bg);
  scroll-margin-top: 12px;
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
  display: grid;
  grid-template-columns: 18px 9px minmax(0, 220px) minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 13px 16px;
  border: none;
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
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
  font-weight: 700;
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
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--fg-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.headline-item .v {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.badge {
  font-size: 12px;
  font-weight: 600;
  /* Reserved width: the label swaps between "No issues", "Checking…" and an
     issue count, and the headline next to it would reflow on every change. */
  min-width: 8em;
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
.badge.unchecked {
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
/* Laptop and below: the headline columns no longer fit beside the identifier
   and the verdict, so they drop rather than squeeze to two characters. */
@media (max-width: 1023px) {
  .card-head {
    grid-template-columns: 18px 9px minmax(0, 1fr) auto auto;
    gap: 12px;
  }
  .headline {
    display: none;
  }
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
  padding: 16px;
  border-top: 1px solid var(--border-subtle);
}
.card-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-bottom: 4px;
}
.card-section + .card-section {
  margin-top: 22px;
}
.card-section h3 {
  padding-bottom: 6px;
  margin: 0 0 12px;
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
  margin-bottom: 4px;
  font-size: 13px;
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
  padding: 3px 6px;
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
.field-group-head {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 7px 8px;
  background: none;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  color: var(--fg);
}
.field-group-head:hover {
  background: var(--bg-subtle);
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
.field-group-issues {
  flex: 0 0 auto;
  min-width: 16px;
  padding: 0 5px;
  border-radius: 8px;
  background: var(--epfl-red);
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
  text-align: center;
}
.field-group.open .fields {
  padding: 6px 8px 14px;
}

.fields {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 14px 20px;
}
/* Labels wrap to two lines for the longer variables. Reserving both lines keeps
   every input in a row on the same baseline instead of stepping up and down. */
.field label {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 2px 5px;
  min-height: 32px;
  margin-bottom: 4px;
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
  padding: 8px 10px;
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

/* Name, preview, count, action — fixed tracks so the rows read as a table. */
.series {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 132px minmax(70px, auto) auto;
  align-items: center;
  gap: 14px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.series:last-child {
  border-bottom: none;
}
.series .spark {
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
  stroke: var(--epfl-red);
  stroke-width: 1.4;
  stroke-linejoin: round;
  stroke-linecap: round;
}
</style>
