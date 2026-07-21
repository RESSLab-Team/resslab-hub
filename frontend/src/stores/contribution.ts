import { defaultApi } from '@/plugins/axios'
import { buildCsv, CONTRIBUTION_DATABASES } from '@/utils/contribution'
import type { DatabaseId } from '@/utils/navigation'
import { buildTarGz } from '@/utils/tar'
import { timeSeriesKindsFor } from '@/utils/timeseries'
import { validateSheet, type SheetIssues } from '@/utils/validation'
import type { ValidationResponse } from '@/utils/validationResponse'
import { isValidationResponse } from '@/utils/validationResponse'
import { isAxiosError } from 'axios'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type { ValidationResponse } from '@/utils/validationResponse'

export type QualityCheckStatus =
  | 'idle'
  | 'running'
  /** Validation ran and the record is clean. */
  | 'pass'
  /** Validation ran, no errors, but the validator raised warnings. */
  | 'warn'
  /** Validation ran and rejected the record. */
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
  /** Original filename, for display. */
  name: string
  content: string
  rows: number
}

/** One experiment (a data row) with a stable client-only id. */
export interface ExperimentRow {
  /** Monotonic, client-only. Keys time-series and survives id edits/reordering. */
  uid: number
  cells: Record<string, string>
}

/** Where a quality-check issue wants to send the user in the grid. */
export interface CellFocus {
  uid: number
  column: string
}

export const useContributionStore = defineStore('contribution', () => {
  const currentStep = ref(0)
  const database = ref<DatabaseId | null>(null)
  const program = ref('')
  const year = ref('')
  const doi = ref('')

  let uidCounter = 0
  const newRow = (cells: Record<string, string> = {}): ExperimentRow => ({
    uid: uidCounter++,
    cells
  })

  /** Experiments, one per grid row. Starts with a single blank row. */
  const rows = ref<ExperimentRow[]>([newRow()])
  /** Attached time-series, keyed by `${row.uid}:${TimeSeriesKind.key}`. */
  const timeSeries = ref<Record<string, AttachedTimeSeries>>({})

  const status = ref<QualityCheckStatus>('idle')
  const response = ref<ValidationResponse | null>(null)
  const errorMessage = ref('')
  /** Set by the quality step to jump to a cell; the grid consumes and clears it. */
  const focusRequest = ref<CellFocus | null>(null)

  const config = computed(() => (database.value ? CONTRIBUTION_DATABASES[database.value] : null))

  const experimentCount = computed(() => rows.value.length)

  const specimenIds = computed(() =>
    rows.value.map((row) => (row.cells.id ?? '').trim()).filter((id) => id !== '')
  )
  const hasAnyId = computed(() => specimenIds.value.length > 0)

  const filledCount = computed(() =>
    rows.value.reduce(
      (total, row) => total + Object.values(row.cells).filter((v) => (v ?? '').trim() !== '').length,
      0
    )
  )

  /** Per-cell client-side issues across the whole sheet (empty when no database). */
  const clientIssues = computed<SheetIssues>(() =>
    database.value ? validateSheet(database.value, rows.value.map((row) => row.cells)) : new Map()
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
    // Columns differ per database, so carrying values across would leave
    // orphaned keys that never reach the CSV.
    database.value = id
    rows.value = [newRow()]
    timeSeries.value = {}
    resetQualityCheck()
  }

  function addRow(): void {
    rows.value.push(newRow())
    resetQualityCheck()
  }

  function duplicateRow(uid: number): void {
    const source = rowByUid(uid)
    if (!source) return
    // Clear the id: ids must be unique, so a copy needs its own.
    rows.value.push(newRow({ ...source.cells, id: '' }))
    resetQualityCheck()
  }

  function removeRow(uid: number): void {
    // Always keep at least one row so the grid is never empty.
    if (rows.value.length <= 1) {
      rows.value = [newRow()]
    } else {
      rows.value = rows.value.filter((row) => row.uid !== uid)
    }
    for (const key of Object.keys(timeSeries.value)) {
      if (key.startsWith(`${uid}:`)) delete timeSeries.value[key]
    }
    resetQualityCheck()
  }

  /** Replace all experiments from imported CSV rows. */
  function importRows(records: Array<Record<string, string>>): void {
    rows.value = records.length ? records.map((cells) => newRow(cells)) : [newRow()]
    timeSeries.value = {}
    resetQualityCheck()
  }

  function requestFocus(uid: number, column: string): void {
    focusRequest.value = { uid, column }
  }

  function clearFocus(): void {
    focusRequest.value = null
  }

  function resetQualityCheck(): void {
    status.value = 'idle'
    response.value = null
    errorMessage.value = ''
  }

  async function runQualityCheck(): Promise<void> {
    const target = config.value
    if (!target || !database.value) return

    if (!target.qualityCheckSupported) {
      status.value = 'unsupported'
      return
    }

    status.value = 'running'
    response.value = null
    errorMessage.value = ''

    try {
      // The primary CSV (all experiments) plus each attached time-series, placed
      // in the directory its subsidiary type is globbed from and named after its
      // experiment's id — the validator resolves the foreign key from the
      // filename against the primary CSV's `id`, so both travel in one archive.
      const kinds = timeSeriesKindsFor(database.value)
      const entries = [
        { path: target.csvPath, content: buildCsv(database.value, rows.value.map((r) => r.cells)) }
      ]
      for (const row of rows.value) {
        const id = (row.cells.id ?? '').trim()
        if (id === '') continue // no filename to key on
        for (const kind of kinds) {
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
      // The validator returns 200 for data errors too, so a rejection here means
      // a transport problem: 400 (bad archive), 413 (too large), 429 (rate
      // limited) or a 5xx.
      status.value = 'error'
      errorMessage.value = transportError(caught)
    }
  }

  function reset(): void {
    currentStep.value = 0
    database.value = null
    program.value = ''
    year.value = ''
    doi.value = ''
    rows.value = [newRow()]
    timeSeries.value = {}
    focusRequest.value = null
    resetQualityCheck()
  }

  return {
    currentStep,
    database,
    program,
    year,
    doi,
    rows,
    timeSeries,
    status,
    response,
    errorMessage,
    focusRequest,
    config,
    experimentCount,
    specimenIds,
    hasAnyId,
    filledCount,
    clientIssues,
    clientErrorCount,
    rowByUid,
    selectDatabase,
    addRow,
    duplicateRow,
    removeRow,
    importRows,
    requestFocus,
    clearFocus,
    resetQualityCheck,
    runQualityCheck,
    reset
  }
})
