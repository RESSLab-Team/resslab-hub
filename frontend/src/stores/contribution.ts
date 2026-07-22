import { defaultApi } from '@/plugins/axios'
import { useDictionaryStore } from '@/stores/dictionary'
import { buildCsv, CONTRIBUTION_DATABASES } from '@/utils/contribution'
import type { DatabaseId } from '@/utils/navigation'
import { buildTarGz } from '@/utils/tar'
import { timeSeriesKindsFor } from '@/utils/timeseries'
import { validateSheet, type SheetIssues } from '@/utils/validation'
import type { ValidationResponse } from '@/utils/validationResponse'
import { isValidationResponse } from '@/utils/validationResponse'
import { isAxiosError } from 'axios'
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

export type { ValidationResponse } from '@/utils/validationResponse'

export type QualityCheckStatus =
  | 'idle'
  | 'running'
  | 'pass'
  | 'warn'
  | 'fail'
  /** The backend has no validator for this database. */
  | 'unsupported'
  /** The request itself failed — network, transport, or a server-side crash. */
  | 'error'

function deriveStatus(response: ValidationResponse): QualityCheckStatus {
  if (!response.valid) return 'fail'
  return response.results.some((file) => file.warnings.length > 0) ? 'warn' : 'pass'
}

/** Human-readable message for a failed `/validate` request (not a data error). */
function transportError(caught: unknown): string {
  if (isAxiosError(caught)) {
    const status = caught.response?.status
    if (status === 429) return 'Too many checks in a short time — wait a moment and retry.'
    if (status === 413) return 'The contribution is too large to validate in one request.'
    if (status === 400) return 'The generated archive could not be read by the server.'
    const detail = (caught.response?.data as { detail?: string } | undefined)?.detail
    if (detail) return detail
  }
  return caught instanceof Error ? caught.message : String(caught)
}

/** A measured-response file attached to an experiment, held in memory until upload. */
export interface AttachedTimeSeries {
  name: string
  content: string
  rows: number
}

/** One experiment (a data row) with a stable client-only id. */
export interface ExperimentRow {
  /** Monotonic, client-only. Keys time-series and survives id edits. */
  uid: number
  cells: Record<string, string>
}

/** Idle time after the last edit before the server check fires. */
const AUTO_VALIDATE_DELAY_MS = 2000

export const useContributionStore = defineStore('contribution', () => {
  const dictionary = useDictionaryStore()

  const database = ref<DatabaseId | null>(null)
  const program = ref('')
  const year = ref('')
  const doi = ref('')

  let uidCounter = 0
  const newRow = (cells: Record<string, string> = {}): ExperimentRow => ({
    uid: uidCounter++,
    cells
  })

  const rows = ref<ExperimentRow[]>([newRow()])
  /** Attached time-series, keyed by `${row.uid}:${TimeSeriesKind.key}`. */
  const timeSeries = ref<Record<string, AttachedTimeSeries>>({})

  const status = ref<QualityCheckStatus>('idle')
  const response = ref<ValidationResponse | null>(null)
  const errorMessage = ref('')

  const config = computed(() => (database.value ? CONTRIBUTION_DATABASES[database.value] : null))
  const columns = computed(() => dictionary.columnsFor(database.value))

  const experimentCount = computed(() => rows.value.length)
  const specimenIds = computed(() =>
    rows.value.map((row) => (row.cells.id ?? '').trim()).filter((id) => id !== '')
  )
  const hasAnyId = computed(() => specimenIds.value.length > 0)

  /** Per-cell client-side issues across all experiments. */
  const clientIssues = computed<SheetIssues>(() =>
    validateSheet(columns.value, rows.value.map((row) => row.cells))
  )

  const clientErrorCount = computed(() => {
    let count = 0
    for (const row of clientIssues.value.values()) {
      for (const issue of Object.values(row)) if (issue.level === 'error') count++
    }
    return count
  })

  function rowByUid(uid: number): ExperimentRow | undefined {
    return rows.value.find((row) => row.uid === uid)
  }

  function selectDatabase(id: DatabaseId): void {
    if (database.value === id) return
    // Columns differ per database; carried-over values would never reach the CSV.
    database.value = id
    rows.value = [newRow()]
    timeSeries.value = {}
    resetQualityCheck()
  }

  function addRow(): void {
    rows.value.push(newRow())
  }

  function duplicateRow(uid: number): void {
    const source = rowByUid(uid)
    if (!source) return
    // Ids must be unique, so a copy starts without one.
    rows.value.push(newRow({ ...source.cells, id: '' }))
  }

  function removeRow(uid: number): void {
    // Keep at least one row so the editor is never empty.
    rows.value = rows.value.length > 1 ? rows.value.filter((row) => row.uid !== uid) : [newRow()]
    for (const key of Object.keys(timeSeries.value)) {
      if (key.startsWith(`${uid}:`)) delete timeSeries.value[key]
    }
  }

  /** Replace all experiments from imported CSV rows. */
  function importRows(records: Array<Record<string, string>>): void {
    rows.value = records.length ? records.map((cells) => newRow(cells)) : [newRow()]
    timeSeries.value = {}
  }

  function resetQualityCheck(): void {
    status.value = 'idle'
    response.value = null
    errorMessage.value = ''
  }

  async function runQualityCheck(): Promise<void> {
    const target = config.value
    if (!target || !database.value || columns.value.length === 0) return

    if (!target.qualityCheckSupported) {
      status.value = 'unsupported'
      return
    }
    if (!hasAnyId.value) return

    status.value = 'running'
    response.value = null
    errorMessage.value = ''

    try {
      // The primary CSV (all experiments) plus each attached time-series, named
      // `<id>.csv` in its kind's directory — the validator reads the foreign
      // key from the filename, matched against the primary CSV in the archive.
      const columnNames = columns.value.map((column) => column.name)
      const entries = [
        { path: target.csvPath, content: buildCsv(columnNames, rows.value.map((r) => r.cells)) }
      ]
      for (const row of rows.value) {
        const id = (row.cells.id ?? '').trim()
        if (id === '') continue
        for (const kind of timeSeriesKindsFor(database.value)) {
          const attached = timeSeries.value[`${row.uid}:${kind.key}`]
          if (attached) {
            entries.push({ path: `${kind.directory}/${id}.csv`, content: attached.content })
          }
        }
      }

      const archive = await buildTarGz(entries, 'contribution.tar.gz')
      const { data } = await defaultApi.validateData(target.type, archive)
      if (!isValidationResponse(data)) {
        throw new Error('Unexpected validation response shape.')
      }
      response.value = data
      status.value = deriveStatus(data)
    } catch (caught) {
      status.value = 'error'
      errorMessage.value = transportError(caught)
    }
  }

  // Auto-validate: any edit invalidates the last report and re-checks after a
  // quiet delay. Trailing-only, so continuous typing fires nothing; a failed
  // request is not auto-retried (the manual "Check now" button covers that).
  let debounce: ReturnType<typeof setTimeout> | undefined
  watch(
    [rows, timeSeries],
    () => {
      if (status.value !== 'running') resetQualityCheck()
      clearTimeout(debounce)
      if (!config.value?.qualityCheckSupported || !hasAnyId.value) return
      debounce = setTimeout(() => {
        if (status.value !== 'running') runQualityCheck()
      }, AUTO_VALIDATE_DELAY_MS)
    },
    { deep: true }
  )

  function reset(): void {
    database.value = null
    program.value = ''
    year.value = ''
    doi.value = ''
    rows.value = [newRow()]
    timeSeries.value = {}
    resetQualityCheck()
  }

  return {
    database,
    program,
    year,
    doi,
    rows,
    timeSeries,
    status,
    response,
    errorMessage,
    config,
    columns,
    experimentCount,
    specimenIds,
    hasAnyId,
    clientIssues,
    clientErrorCount,
    rowByUid,
    selectDatabase,
    addRow,
    duplicateRow,
    removeRow,
    importRows,
    resetQualityCheck,
    runQualityCheck,
    reset
  }
})
