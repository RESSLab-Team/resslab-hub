<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import { useContributionStore } from '@/stores/contribution'
import { fieldLabel } from '@/utils/contribution'
import { columnFor, dictionaryFor, type DictColumn } from '@/utils/dictionary'
import { mapResponse, type ExperimentReport } from '@/utils/qualityReport'
import { sparkline } from '@/utils/sparkline'
import { checkTimeSeriesFile, timeSeriesKindsFor, type TimeSeriesKind } from '@/utils/timeseries'
import type { CellIssue } from '@/utils/validation'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()

const columns = computed(() => (store.database ? dictionaryFor(store.database) : []))
const kinds = computed(() => timeSeriesKindsFor(store.database))

// Headline fields shown on the collapsed card. Prefer identifying metadata that
// exists in this database, then fall back to the first columns after id.
const HEADLINE_PREFERRED = [
  'date',
  'investigator',
  'cross_section_shape',
  'grade',
  'connection_type',
  'test_type',
  'section'
]
const headlineColumns = computed<DictColumn[]>(() => {
  if (!store.database) return []
  const names = new Set(columns.value.map((column) => column.name))
  const picked: string[] = HEADLINE_PREFERRED.filter((name) => names.has(name)).slice(0, 3)
  for (const column of columns.value) {
    if (picked.length >= 3) break
    if (column.name !== 'id' && !picked.includes(column.name)) picked.push(column.name)
  }
  return picked
    .map((name) => columnFor(store.database!, name))
    .filter((column): column is DictColumn => Boolean(column))
})

// Client-side issues re-keyed from row-index to row uid.
const clientByUid = computed(() => {
  const map = new Map<number, Record<string, CellIssue>>()
  store.rows.forEach((row, index) => {
    const issues = store.clientIssues.get(index)
    if (issues) map.set(row.uid, issues)
  })
  return map
})

const serverByUid = computed(() => {
  const map = new Map<number, ExperimentReport>()
  if (store.database && store.response) {
    for (const experiment of mapResponse(store.database, store.rows, store.response).experiments) {
      map.set(experiment.uid, experiment)
    }
  }
  return map
})

function clientIssues(uid: number): Array<{ column: string; issue: CellIssue }> {
  return Object.entries(clientByUid.value.get(uid) ?? {}).map(([column, issue]) => ({
    column,
    issue
  }))
}

function levelForUid(uid: number): 'pass' | 'warn' | 'fail' {
  let level: 'pass' | 'warn' | 'fail' = 'pass'
  for (const { issue } of clientIssues(uid)) {
    if (issue.level === 'error') return 'fail'
    if (issue.level === 'warn') level = 'warn'
  }
  for (const file of serverByUid.value.get(uid)?.fileIssues ?? []) {
    if (file.severity === 'error') return 'fail'
    if (file.severity === 'warning' && level === 'pass') level = 'warn'
  }
  return level
}

function issueCount(uid: number): number {
  return clientIssues(uid).length + (serverByUid.value.get(uid)?.fileIssues.length ?? 0)
}

function cellError(uid: number, column: string): CellIssue | undefined {
  return clientByUid.value.get(uid)?.[column]
}

// --- Expand / collapse ---------------------------------------------------
const expanded = ref<Set<number>>(new Set())
function toggle(uid: number): void {
  const next = new Set(expanded.value)
  next.has(uid) ? next.delete(uid) : next.add(uid)
  expanded.value = next
}
function expandAll(): void {
  expanded.value = new Set(store.rows.map((row) => row.uid))
}
function collapseAll(): void {
  expanded.value = new Set()
}

// --- Test data -----------------------------------------------------------
const fileInputs = ref<Record<string, HTMLInputElement | null>>({})
const attachErrors = ref<Record<string, string>>({})

async function attach(uid: number, kind: TimeSeriesKind, file: File | undefined): Promise<void> {
  if (!file) return
  const key = `${uid}:${kind.key}`
  const text = await file.text()
  const check = checkTimeSeriesFile(kind, text)
  if (!check.ok) {
    attachErrors.value[key] =
      check.error === 'empty'
        ? t('contribute.timeseries.error_empty')
        : t('contribute.timeseries.error_columns', { columns: check.missing.join(', ') })
    return
  }
  delete attachErrors.value[key]
  store.timeSeries[key] = { name: file.name, content: text, rows: check.rows }
  store.resetQualityCheck()
}

function onAttach(uid: number, kind: TimeSeriesKind, event: Event): void {
  const input = event.target as HTMLInputElement
  attach(uid, kind, input.files?.[0])
  input.value = ''
}

function remove(uid: number, kind: TimeSeriesKind): void {
  delete store.timeSeries[`${uid}:${kind.key}`]
  store.resetQualityCheck()
}

function chart(uid: number, kind: TimeSeriesKind) {
  const attached = store.timeSeries[`${uid}:${kind.key}`]
  return attached ? sparkline(attached.content) : null
}
</script>

<template>
  <div v-if="store.database" class="cp-cards">
    <div class="cp-cards-toolbar">
      <button class="cp-btn ghost" type="button" @click="store.addRow()">
        <cp-icon :size="15" name="layers" />{{ $t('contribute.grid.add_row') }}
      </button>
      <span class="cp-sheet-spacer" />
      <button class="cp-btn ghost" type="button" @click="expandAll">
        {{ $t('contribute.cards.expand_all') }}
      </button>
      <button class="cp-btn ghost" type="button" @click="collapseAll">
        {{ $t('contribute.cards.collapse_all') }}
      </button>
    </div>

    <div v-for="(row, index) in store.rows" :key="row.uid" class="cp-card" :class="levelForUid(row.uid)">
      <!-- Always-visible header -->
      <button class="cp-card-h" type="button" @click="toggle(row.uid)">
        <cp-icon class="chev" :class="{ open: expanded.has(row.uid) }" :size="15" name="chevronRight" />
        <span class="dot" :class="levelForUid(row.uid)" />
        <span class="cp-card-id">{{ row.cells.id?.trim() || $t('contribute.cards.untitled', { n: index + 1 }) }}</span>

        <span class="cp-card-headline">
          <span v-for="column in headlineColumns" :key="column.name" class="chip">
            <span class="k">{{ fieldLabel(store.database, column.name) }}</span>
            <span class="v">{{ row.cells[column.name]?.trim() || '—' }}</span>
          </span>
        </span>

        <span class="cp-card-badge" :class="levelForUid(row.uid)">
          <template v-if="issueCount(row.uid)">
            {{ $t('contribute.cards.issue_count', { count: issueCount(row.uid) }) }}
          </template>
          <template v-else>
            <cp-icon :size="12" name="check" />{{ $t('contribute.cards.clean') }}
          </template>
        </span>
      </button>

      <!-- Expanded body -->
      <div v-if="expanded.has(row.uid)" class="cp-card-body">
        <div class="cp-card-acts">
          <button class="cp-btn ghost" type="button" @click="store.duplicateRow(row.uid)">
            <cp-icon :size="13" name="layers" />{{ $t('contribute.grid.duplicate_row') }}
          </button>
          <button class="cp-btn ghost" type="button" @click="store.removeRow(row.uid)">
            <cp-icon :size="13" name="close" />{{ $t('contribute.grid.remove_row') }}
          </button>
        </div>

        <!-- Problems -->
        <div v-if="issueCount(row.uid)" class="cp-card-section">
          <div class="cp-card-sh">{{ $t('contribute.cards.problems') }}</div>
          <div
            v-for="entry in clientIssues(row.uid)"
            :key="`c-${entry.column}`"
            class="cp-exp-issue"
            :class="entry.issue.level === 'error' ? 'error' : 'warning'"
          >
            <cp-icon :size="13" :name="entry.issue.level === 'error' ? 'close' : 'alert'" />
            <span>{{ fieldLabel(store.database, entry.column) }}: {{ entry.issue.message }}</span>
          </div>
          <div
            v-for="(file, i) in serverByUid.get(row.uid)?.fileIssues ?? []"
            :key="`f-${i}`"
            class="cp-exp-issue"
            :class="file.severity"
          >
            <cp-icon :size="13" :name="file.severity === 'error' ? 'close' : 'alert'" />
            <span>
              {{ file.kindKey ? $t(`contribute.timeseries.kind.${file.kindKey}`) : '' }} ·
              {{ file.issue.message }}
            </span>
          </div>
        </div>

        <!-- All fields -->
        <div class="cp-card-section">
          <div class="cp-card-sh">{{ $t('contribute.metadata.fields') }}</div>
          <div class="cp-grid2">
            <div
              v-for="column in columns"
              :key="column.name"
              class="cp-field"
              :class="{ 'is-err': cellError(row.uid, column.name) }"
            >
              <label class="cp-label" :for="`f-${row.uid}-${column.name}`">
                {{ fieldLabel(store.database, column.name) }}
                <span v-if="!column.nullable" class="req">*</span>
                <span v-if="column.unit && column.unit !== '-'" class="cp-unit-chip">{{ column.unit }}</span>
                <span
                  v-if="column.description"
                  class="cp-info-i"
                  :title="column.description"
                >
                  <cp-icon :size="11" name="info" />
                </span>
              </label>
              <input
                :id="`f-${row.uid}-${column.name}`"
                v-model="row.cells[column.name]"
                class="cp-input"
                type="text"
              />
              <div v-if="cellError(row.uid, column.name)" class="cp-hint err" style="margin-top: 4px">
                {{ cellError(row.uid, column.name)!.message }}
              </div>
            </div>
          </div>
        </div>

        <!-- Test data (measured responses) -->
        <div v-if="kinds.length" class="cp-card-section">
          <div class="cp-card-sh">{{ $t('contribute.cards.test_data') }}</div>
          <div v-for="kind in kinds" :key="kind.key" class="cp-ts-slot">
            <div class="cp-ts-kind">{{ $t(`contribute.timeseries.kind.${kind.key}`) }}</div>
            <template v-if="store.timeSeries[`${row.uid}:${kind.key}`]">
              <svg
                v-if="chart(row.uid, kind)"
                class="cp-spark"
                :viewBox="`0 0 ${chart(row.uid, kind)!.width} ${chart(row.uid, kind)!.height}`"
                :width="chart(row.uid, kind)!.width"
                :height="chart(row.uid, kind)!.height"
              >
                <polyline :points="chart(row.uid, kind)!.points" />
              </svg>
              <span class="cp-ts-meta">
                {{ $t('contribute.timeseries.rows', { count: store.timeSeries[`${row.uid}:${kind.key}`].rows }) }}
              </span>
              <button class="fx" type="button" @click="remove(row.uid, kind)">
                <cp-icon :size="13" name="close" />
              </button>
            </template>
            <template v-else>
              <button class="cp-btn ghost" type="button" @click="fileInputs[`${row.uid}:${kind.key}`]?.click()">
                <cp-icon :size="13" name="upload" />{{ $t('contribute.timeseries.attach') }}
              </button>
              <input
                :ref="(el) => (fileInputs[`${row.uid}:${kind.key}`] = el as HTMLInputElement)"
                accept=".csv,text/csv"
                hidden
                type="file"
                @change="onAttach(row.uid, kind, $event)"
              />
            </template>
            <div v-if="attachErrors[`${row.uid}:${kind.key}`]" class="cp-hint err">
              {{ attachErrors[`${row.uid}:${kind.key}`] }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
