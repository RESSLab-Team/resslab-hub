<script setup lang="ts">
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import ToolSelect from '@/components/commons/tools/ToolSelect.vue'
import { useContributionStore } from '@/stores/contribution'
import { useNotificationStore } from '@/stores/notification'
import { fieldLabel } from '@/utils/contribution'
import { readCsvTable } from '@/utils/csv'
import { mapResponse, type ExperimentReport } from '@/utils/qualityReport'
import { sparkline } from '@/utils/sparkline'
import { downloadDictionary, downloadTemplate } from '@/utils/templates'
import { checkTimeSeriesFile, timeSeriesKindsFor, type TimeSeriesKind } from '@/utils/timeseries'
import type { CellIssue } from '@/utils/validation'
import {
  mdiAlertOutline,
  mdiChevronRight,
  mdiClose,
  mdiContentCopy,
  mdiDownloadOutline,
  mdiPlus,
  mdiTrayArrowUp,
  mdiUploadOutline
} from '@mdi/js'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()
const notification = useNotificationStore()

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

// Client-side issues re-keyed from row index to row uid.
const clientByUid = computed(() => {
  const map = new Map<number, Record<string, CellIssue>>()
  store.rows.forEach((row, index) => {
    const issues = store.clientIssues.get(index)
    if (issues) map.set(row.uid, issues)
  })
  return map
})

// Server-side issues from the last validation, mapped back per experiment.
const serverByUid = computed(() => {
  const map = new Map<number, ExperimentReport>()
  if (store.database && store.response) {
    for (const experiment of mapResponse(store.database, store.rows, store.response).experiments) {
      map.set(experiment.uid, experiment)
    }
  }
  return map
})

function cellIssue(uid: number, column: string): CellIssue | undefined {
  return clientByUid.value.get(uid)?.[column]
}

interface CardIssue {
  column?: string
  kindKey?: string | null
  level: 'error' | 'warn'
  message: string
}

function issuesFor(uid: number): CardIssue[] {
  const client = Object.entries(clientByUid.value.get(uid) ?? {}).map(([column, issue]) => ({
    column,
    level: issue.level,
    message: issue.message
  }))
  const server = (serverByUid.value.get(uid)?.fileIssues ?? []).map((file) => ({
    kindKey: file.kindKey,
    level: file.severity === 'error' ? ('error' as const) : ('warn' as const),
    message: file.issue.message
  }))
  // Server-reported range warnings live on cells too; surface those the client
  // engine cannot know about (client issues already cover the rest).
  const known = new Set(client.map((issue) => issue.column))
  const serverCells = (serverByUid.value.get(uid)?.cellIssues ?? [])
    .filter((cell) => !known.has(cell.ref.column))
    .map((cell) => ({
      column: cell.ref.column,
      level: cell.severity === 'error' ? ('error' as const) : ('warn' as const),
      message: cell.issue.message
    }))
  return [...client, ...serverCells, ...server]
}

function levelFor(uid: number): 'pass' | 'warn' | 'fail' {
  const issues = issuesFor(uid)
  if (issues.some((issue) => issue.level === 'error')) return 'fail'
  return issues.length ? 'warn' : 'pass'
}

// --- Expand / collapse ---------------------------------------------------
const expanded = ref<Set<number>>(new Set())
function toggle(uid: number): void {
  const next = new Set(expanded.value)
  if (next.has(uid)) next.delete(uid)
  else next.add(uid)
  expanded.value = next
}

// --- CSV import ----------------------------------------------------------
const importInput = ref<HTMLInputElement>()

async function importFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
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
  <div>
    <div class="toolbar">
      <button class="btn btn-secondary btn-sm" type="button" @click="store.addRow()">
        <v-icon :icon="mdiPlus" size="14" />{{ $t('contribute.editor.add_experiment') }}
      </button>
      <button class="btn btn-secondary btn-sm" type="button" @click="importInput?.click()">
        <v-icon :icon="mdiTrayArrowUp" size="14" />{{ $t('contribute.editor.import_csv') }}
      </button>
      <input ref="importInput" accept=".csv,text/csv" hidden type="file" @change="importFile" />
      <span class="spacer" />
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
    </div>

    <!-- Bulk attach: pick a response type, drop many <id>.csv files at once. -->
    <div v-if="kinds.length" class="toolbar">
      <span class="bulk-label">{{ $t('contribute.editor.bulk_attach') }}</span>
      <tool-select
        v-model="bulkKindKey"
        class="bulk-select"
        :items="kinds.map((kind) => ({ title: $t(`contribute.timeseries.kind.${kind.key}`), value: kind.key }))"
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
      <input ref="bulkInput" accept=".csv,text/csv" hidden multiple type="file" @change="onBulkAttach" />
      <span class="bulk-hint">{{ $t('contribute.editor.bulk_hint') }}</span>
    </div>

    <article v-for="(row, index) in store.rows" :key="row.uid" class="card" :class="levelFor(row.uid)">
      <button class="card-head" type="button" @click="toggle(row.uid)">
        <v-icon class="chevron" :class="{ open: expanded.has(row.uid) }" :icon="mdiChevronRight" size="18" />
        <span class="dot" :class="levelFor(row.uid)" />
        <span class="card-id">
          {{ row.cells.id?.trim() || $t('contribute.editor.untitled', { n: index + 1 }) }}
        </span>
        <span class="headline">
          <span v-for="column in headlineColumns" :key="column.name" class="headline-item">
            <span class="k">{{ fieldLabel(store.database!, column.name) }}</span>
            <span class="v">{{ row.cells[column.name]?.trim() || '—' }}</span>
          </span>
        </span>
        <span class="badge" :class="levelFor(row.uid)">
          {{
            issuesFor(row.uid).length
              ? $t('contribute.editor.issue_count', { count: issuesFor(row.uid).length })
              : $t('contribute.editor.clean')
          }}
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

        <section v-if="issuesFor(row.uid).length" class="card-section">
          <h3>{{ $t('contribute.editor.problems') }}</h3>
          <p v-for="(issue, i) in issuesFor(row.uid)" :key="i" class="issue" :class="issue.level">
            <v-icon :icon="mdiAlertOutline" size="14" />
            <span>
              <template v-if="issue.column">{{ fieldLabel(store.database!, issue.column) }}: </template>
              <template v-else-if="issue.kindKey">
                {{ $t(`contribute.timeseries.kind.${issue.kindKey}`) }}:
              </template>
              {{ issue.message }}
            </span>
          </p>
        </section>

        <section class="card-section">
          <h3>{{ $t('contribute.editor.fields') }}</h3>
          <div class="fields">
            <div
              v-for="column in store.columns"
              :key="column.name"
              class="field"
              :class="cellIssue(row.uid, column.name)?.level"
            >
              <label :for="`f-${row.uid}-${column.name}`">
                {{ fieldLabel(store.database!, column.name) }}
                <span v-if="!column.nullable" class="required">*</span>
                <span v-if="column.unit && column.unit !== '-'" class="unit">{{ column.unit }}</span>
                <info-tooltip v-if="column.description">{{ column.description }}</info-tooltip>
              </label>
              <input :id="`f-${row.uid}-${column.name}`" v-model="row.cells[column.name]" type="text" />
              <small v-if="cellIssue(row.uid, column.name)" :class="cellIssue(row.uid, column.name)!.level">
                {{ cellIssue(row.uid, column.name)!.message }}
              </small>
            </div>
          </div>
        </section>

        <section v-if="kinds.length" class="card-section">
          <h3>{{ $t('contribute.editor.test_data') }}</h3>
          <div v-for="kind in kinds" :key="kind.key" class="series">
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
                <v-icon :icon="mdiUploadOutline" size="13" />{{ $t('contribute.timeseries.attach') }}
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
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.spacer {
  flex: 1;
}
.bulk-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--fg);
}
.bulk-select {
  min-width: 220px;
}
.bulk-hint {
  font-size: 12px;
  color: var(--fg-muted);
}

.card {
  border: 1px solid var(--border);
  border-left: 3px solid var(--border-strong);
  margin-bottom: 12px;
  background: var(--bg);
}
.card.fail {
  border-left-color: var(--epfl-red);
}
.card.warn {
  border-left-color: var(--epfl-orange);
}

.card-head {
  display: flex;
  align-items: center;
  gap: 12px;
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
.card-id {
  font-weight: 700;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.headline {
  display: flex;
  gap: 18px;
  flex: 1;
  flex-wrap: wrap;
  min-width: 0;
}
.headline-item {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.headline-item .k {
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--fg-muted);
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
  flex: none;
  color: var(--epfl-green-text);
}
.badge.warn {
  color: var(--epfl-orange);
}
.badge.fail {
  color: var(--epfl-red);
}

.card-body {
  padding: 0 16px 16px;
  border-top: 1px solid var(--border-subtle);
}
.card-actions {
  display: flex;
  gap: 8px;
  padding: 12px 0;
}
.card-section {
  margin-top: 10px;
}
.card-section h3 {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
  margin: 0 0 10px;
}

.issue {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 6px;
  font-size: 13px;
}
.issue.error {
  color: var(--epfl-red);
}
.issue.warn {
  color: var(--epfl-orange);
}

.fields {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px 18px;
}
.field label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12.5px;
  font-weight: 600;
  margin-bottom: 4px;
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

.series {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.series:last-child {
  border-bottom: none;
}
.series-name {
  min-width: 200px;
  font-size: 13px;
  font-weight: 600;
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
