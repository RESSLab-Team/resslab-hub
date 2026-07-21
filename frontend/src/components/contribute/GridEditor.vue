<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import { useContributionStore } from '@/stores/contribution'
import { fieldLabel } from '@/utils/contribution'
import { readCsvTable } from '@/utils/csv'
import { dictionaryFor } from '@/utils/dictionary'
import { downloadDictionary, downloadTemplate } from '@/utils/templates'
import { mapResponse } from '@/utils/qualityReport'
import type { DictColumn } from '@/utils/dictionary'
import type { CellIssue } from '@/utils/validation'
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()

const columns = computed(() => (store.database ? dictionaryFor(store.database) : []))

// Column-description tooltip, teleported to <body> so the grid's scroll
// container cannot clip it. Shown while hovering the header's info icon.
const tip = ref<{ column: DictColumn; x: number; y: number } | null>(null)

function showTip(column: DictColumn, event: MouseEvent | FocusEvent): void {
  const target = event.currentTarget as HTMLElement | null
  if (!target) return
  const rect = target.getBoundingClientRect()
  tip.value = { column, x: rect.left, y: rect.bottom + 6 }
}

function hideTip(): void {
  tip.value = null
}

// Client-side issues re-keyed from row-index (store.clientIssues) to row uid.
const clientByUid = computed(() => {
  const map = new Map<number, Record<string, CellIssue>>()
  store.rows.forEach((row, index) => {
    const issues = store.clientIssues.get(index)
    if (issues) map.set(row.uid, issues)
  })
  return map
})

// Server-side issues from the last quality check, mapped back to cells/files.
const serverReport = computed(() =>
  store.database && store.response ? mapResponse(store.database, store.rows, store.response) : null
)

const serverCellIssues = computed(() => {
  const map = new Map<string, CellIssue>()
  for (const experiment of serverReport.value?.experiments ?? []) {
    for (const cell of experiment.cellIssues) {
      map.set(`${cell.ref.uid}:${cell.ref.column}`, {
        level: cell.severity === 'error' ? 'error' : 'warn',
        message: cell.issue.message
      })
    }
  }
  return map
})

const serverFilesByUid = computed(() => {
  const map = new Map<number, 'error' | 'warn'>()
  for (const experiment of serverReport.value?.experiments ?? []) {
    for (const file of experiment.fileIssues) {
      const level = file.severity === 'error' ? 'error' : 'warn'
      if (level === 'error' || !map.has(experiment.uid)) map.set(experiment.uid, level)
    }
  }
  return map
})

// A cell edited since the last quality check: its stale server issue is hidden.
const dirty = ref<Set<string>>(new Set())

function cellIssue(uid: number, column: string): CellIssue | null {
  const client = clientByUid.value.get(uid)?.[column]
  if (client) return client
  const key = `${uid}:${column}`
  if (!dirty.value.has(key)) {
    const server = serverCellIssues.value.get(key)
    if (server) return server
  }
  return null
}

function rowLevel(uid: number): 'pass' | 'warn' | 'fail' {
  let level: 'pass' | 'warn' | 'fail' = 'pass'
  for (const column of columns.value) {
    const issue = cellIssue(uid, column.name)
    if (issue?.level === 'error') return 'fail'
    if (issue?.level === 'warn') level = 'warn'
  }
  const file = serverFilesByUid.value.get(uid)
  if (file === 'error') return 'fail'
  if (file === 'warn' && level === 'pass') level = 'warn'
  return level
}

const showOnlyIssues = ref(false)
const visibleRows = computed(() =>
  showOnlyIssues.value ? store.rows.filter((row) => rowLevel(row.uid) !== 'pass') : store.rows
)

// Columns that hold at least one flagged cell (across all rows).
const columnsWithIssues = computed(() => {
  const flagged = new Set<string>()
  for (const row of store.rows) {
    for (const column of columns.value) {
      if (flagged.has(column.name)) continue
      if (cellIssue(row.uid, column.name)) flagged.add(column.name)
    }
  }
  return flagged
})

const issuesFirst = ref(false)

// When on, bring flagged columns to the front (id stays pinned first) so the
// problems are visible without scrolling a wide sheet.
const columnsView = computed(() => {
  if (!issuesFirst.value) return columns.value
  const flagged: typeof columns.value = []
  const clean: typeof columns.value = []
  for (const column of columns.value) {
    if (column.name === 'id') continue
    ;(columnsWithIssues.value.has(column.name) ? flagged : clean).push(column)
  }
  const id = columns.value.find((column) => column.name === 'id')
  return [...(id ? [id] : []), ...flagged, ...clean]
})

const totals = computed(() => {
  let errors = 0
  let warnings = 0
  for (const row of store.rows) {
    const level = rowLevel(row.uid)
    if (level === 'fail') errors++
    else if (level === 'warn') warnings++
  }
  return { errors, warnings }
})

function onEdit(uid: number, column: string, event: Event): void {
  const value = (event.target as HTMLInputElement).value
  const row = store.rowByUid(uid)
  if (row) row.cells[column] = value
  dirty.value.add(`${uid}:${column}`)
}

// --- CSV import ---------------------------------------------------------
const fileInput = ref<HTMLInputElement>()
const dragging = ref(false)
const importReport = ref<{
  file: string
  rowCount: number
  matched: number
  unknown: string[]
  missing: string[]
} | null>(null)
const importError = ref('')

async function importFile(file: File | undefined): Promise<void> {
  if (!file || !store.database || !store.config) return
  importError.value = ''
  importReport.value = null
  try {
    const table = readCsvTable(await file.text(), store.config.columns)
    if (table.matched.length === 0) {
      throw new Error(t('contribute.metadata.import_no_match'))
    }
    store.importRows(table.rows)
    dirty.value = new Set()
    importReport.value = {
      file: file.name,
      rowCount: table.rows.length,
      matched: table.matched.length,
      unknown: table.unknown,
      missing: table.missing
    }
  } catch (caught) {
    importError.value = caught instanceof Error ? caught.message : String(caught)
  }
}

function onDrop(event: DragEvent): void {
  dragging.value = false
  importFile(event.dataTransfer?.files[0])
}

function onSelect(event: Event): void {
  const input = event.target as HTMLInputElement
  importFile(input.files?.[0])
  input.value = ''
}

// --- Focus jump from the quality step -----------------------------------
const inputs = ref<Record<string, HTMLInputElement | null>>({})

watch(
  () => store.focusRequest,
  async (request) => {
    if (!request) return
    showOnlyIssues.value = false
    await nextTick()
    const element = inputs.value[`${request.uid}:${request.column}`]
    if (element) {
      element.scrollIntoView({ block: 'center', inline: 'center' })
      element.focus()
    }
    store.clearFocus()
  }
)
</script>

<template>
  <div v-if="store.database" class="cp-sheet-shell">
    <div class="cp-sheet-toolbar">
      <button class="cp-btn ghost" type="button" @click="store.addRow()">
        <cp-icon :size="15" name="layers" />
        {{ $t('contribute.grid.add_row') }}
      </button>
      <button
        class="cp-btn ghost"
        type="button"
        :class="{ 'is-active': showOnlyIssues }"
        @click="showOnlyIssues = !showOnlyIssues"
      >
        <cp-icon :size="15" name="alert" />
        {{ $t('contribute.grid.only_issues') }}
      </button>
      <button
        class="cp-btn ghost"
        type="button"
        :class="{ 'is-active': issuesFirst }"
        :disabled="columnsWithIssues.size === 0"
        @click="issuesFirst = !issuesFirst"
      >
        <cp-icon :size="15" name="arrowRight" />
        {{ $t('contribute.grid.issues_first') }}
      </button>

      <span class="cp-sheet-counts">
        <span v-if="totals.errors" class="c fail">{{
          $t('contribute.grid.error_count', { count: totals.errors })
        }}</span>
        <span v-if="totals.warnings" class="c warn">{{
          $t('contribute.grid.warning_count', { count: totals.warnings })
        }}</span>
        <span v-if="!totals.errors && !totals.warnings" class="c ok">
          <cp-icon :size="13" name="check" />{{ $t('contribute.grid.no_issues') }}
        </span>
      </span>

      <span class="cp-sheet-spacer" />

      <button class="cp-btn ghost" type="button" @click="downloadTemplate(store.database)">
        <cp-icon :size="15" name="save" />
        {{ $t('contribute.grid.download_template') }}
      </button>
      <button class="cp-btn ghost" type="button" @click="downloadDictionary(store.database)">
        <cp-icon :size="15" name="info" />
        {{ $t('contribute.grid.download_dictionary') }}
      </button>
    </div>

    <!-- Import a filled CSV: replaces every experiment with the file's rows. -->
    <div class="cp-sheet-import" :class="{ dragover: dragging }">
      <button
        class="cp-sheet-importzone"
        type="button"
        @click="fileInput?.click()"
        @dragleave.prevent="dragging = false"
        @dragover.prevent="dragging = true"
        @drop.prevent="onDrop"
      >
        <cp-icon :size="16" :width="1.6" name="upload" />
        <i18n-t keypath="contribute.grid.import_prompt" tag="span">
          <template #browse>
            <b>{{ $t('contribute.metadata.import_browse') }}</b>
          </template>
        </i18n-t>
      </button>
    </div>
    <input ref="fileInput" accept=".csv,text/csv" hidden type="file" @change="onSelect" />

    <div v-if="importError" class="cp-hint err">
      <cp-icon :size="13" name="alert" />{{ importError }}
    </div>
    <template v-else-if="importReport">
      <div class="cp-hint ok">
        <cp-icon :size="13" name="check" />
        {{
          $t('contribute.grid.import_ok', {
            file: importReport.file,
            rows: importReport.rowCount,
            matched: importReport.matched
          })
        }}
      </div>
      <div v-if="importReport.missing.length" class="cp-hint err">
        {{
          $t('contribute.grid.import_missing', {
            count: importReport.missing.length,
            columns: importReport.missing.slice(0, 6).join(', ')
          })
        }}
      </div>
      <div v-if="importReport.unknown.length" class="cp-hint">
        {{
          $t('contribute.grid.import_unknown', {
            count: importReport.unknown.length,
            columns: importReport.unknown.slice(0, 6).join(', ')
          })
        }}
      </div>
    </template>

    <div class="cp-sheet-wrap">
      <table class="cp-sheet">
        <thead>
          <tr>
            <th class="rail">#</th>
            <th
              v-for="column in columnsView"
              :key="column.name"
              :class="{ 'col-id': column.name === 'id' }"
            >
              <span class="hd">
                <span class="lbl">{{ fieldLabel(store.database, column.name) }}</span>
                <span v-if="!column.nullable" class="req">*</span>
                <!-- symbol comes from our own dictionary asset (trusted) -->
                <!-- eslint-disable-next-line vue/no-v-html -->
                <span v-if="column.symbol" class="sym" v-html="column.symbol" />
                <span
                  class="info"
                  tabindex="0"
                  @mouseenter="showTip(column, $event)"
                  @mouseleave="hideTip"
                  @focus="showTip(column, $event)"
                  @blur="hideTip"
                >
                  <cp-icon :size="12" name="info" />
                </span>
              </span>
              <span v-if="column.unit && column.unit !== '-'" class="unit">{{ column.unit }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in visibleRows" :key="row.uid" :class="`lvl-${rowLevel(row.uid)}`">
            <td class="rail">
              <span class="num">{{ store.rows.indexOf(row) + 1 }}</span>
              <span class="dot" :class="`lvl-${rowLevel(row.uid)}`" />
              <span class="acts">
                <button
                  type="button"
                  :title="$t('contribute.grid.duplicate_row')"
                  @click="store.duplicateRow(row.uid)"
                >
                  <cp-icon :size="12" name="layers" />
                </button>
                <button
                  type="button"
                  :title="$t('contribute.grid.remove_row')"
                  @click="store.removeRow(row.uid)"
                >
                  <cp-icon :size="12" name="close" />
                </button>
              </span>
            </td>
            <td
              v-for="column in columnsView"
              :key="column.name"
              :class="[
                { 'col-id': column.name === 'id' },
                cellIssue(row.uid, column.name)
                  ? `cell-${cellIssue(row.uid, column.name)!.level}`
                  : ''
              ]"
              :title="cellIssue(row.uid, column.name)?.message"
            >
              <input
                :ref="(el) => (inputs[`${row.uid}:${column.name}`] = el as HTMLInputElement)"
                class="cp-cell-input"
                type="text"
                :value="row.cells[column.name] ?? ''"
                @input="onEdit(row.uid, column.name, $event)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="showOnlyIssues && visibleRows.length === 0" class="cp-hint ok" style="margin-top: 12px">
      <cp-icon :size="13" name="check" />{{ $t('contribute.grid.all_clean') }}
    </p>

    <Teleport to="body">
      <div v-if="tip" class="cp-sheet-tip" :style="{ left: `${tip.x}px`, top: `${tip.y}px` }">
        <div v-if="tip.column.description" class="d">{{ tip.column.description }}</div>
        <div v-else class="d muted">{{ $t('contribute.grid.tip_no_description') }}</div>
        <div class="m">
          <span v-if="tip.column.unit && tip.column.unit !== '-'">
            {{ $t('contribute.grid.tip_unit') }}: {{ tip.column.unit }}
          </span>
          <span>{{ tip.column.type }}</span>
          <span :class="tip.column.nullable ? '' : 'req'">
            {{
              tip.column.nullable
                ? $t('contribute.grid.tip_optional')
                : $t('contribute.grid.tip_required')
            }}
          </span>
        </div>
      </div>
    </Teleport>
  </div>
</template>
