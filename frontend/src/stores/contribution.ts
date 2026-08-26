import { defaultApi } from '@/plugins/axios'
import { useDictionaryStore } from '@/stores/dictionary'
import { buildCsv, CONTRIBUTION_DATABASES } from '@/utils/contribution'
import type { DatabaseId } from '@/utils/navigation'
import { mapResponse, type ExperimentReport, type ReportedIssue } from '@/utils/qualityReport'
import { postContribution, type ContributorInfo } from '@/utils/submission'
import { buildTarGz } from '@/utils/tar'
import { timeSeriesKindsFor } from '@/utils/timeseries'
import type { CellIssue } from '@/utils/validation'
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
    // The backend explains its own refusals (an id that cannot be a file name,
    // a specimen already in the repository, GitHub unreachable…) — show that,
    // and only fall back to a generic line when there is nothing to show.
    const detail = (caught.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string' && detail) return detail
    if (status === 400) return 'The generated archive could not be read by the server.'
    if (status !== undefined) return `The server answered with status ${status}.`
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

/** One problem to show on an experiment card, from either validation source. */
export interface CardIssue {
  /**
   * Identity of the problem, stable across re-validations so a dismissal
   * survives the next automatic check. It embeds what the contributor was
   * looking at when they dismissed it — the cell value, or the attached
   * filename — so editing that value brings the warning back.
   */
  key: string
  /** Set for a field problem; `kindKey` is set instead for a test-data file. */
  column?: string
  kindKey?: string | null
  level: 'error' | 'warn'
  message: string
}

function issueKey(uid: number, target: string, signature: string, message: string): string {
  return `${uid}|${target}|${signature}|${message}`
}

/** Warning on an experiment that would be submitted with its record only. */
export const NO_TEST_DATA_MESSAGE =
  'No test data attached — the experiment will be submitted with its metadata only.'

/** One experiment's unresolved problems, for the summary under the status bar. */
export interface ExperimentProblems {
  uid: number
  /** Position in the batch, for experiments without an id yet. */
  index: number
  id: string
  errors: number
  warnings: number
  /** The unresolved problems themselves, so a lone one can be shown in place. */
  issues: CardIssue[]
}

/** Idle time after the last edit before the server check fires. */
const AUTO_VALIDATE_DELAY_MS = 2000

export const useContributionStore = defineStore('contribution', () => {
  const dictionary = useDictionaryStore()

  const database = ref<DatabaseId | null>(null)
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

  const submitStatus = ref<'idle' | 'submitting' | 'submitted' | 'error'>('idle')
  const submitError = ref('')
  const pullRequestUrl = ref('')
  const pullRequestNumber = ref(0)

  const config = computed(() => (database.value ? CONTRIBUTION_DATABASES[database.value] : null))
  const columns = computed(() => dictionary.columnsFor(database.value))

  const experimentCount = computed(() => rows.value.length)
  const specimenIds = computed(() =>
    rows.value.map((row) => (row.cells.id ?? '').trim()).filter((id) => id !== '')
  )
  const hasAnyId = computed(() => specimenIds.value.length > 0)

  /** Per-cell client-side issues across all experiments. */
  const clientIssues = computed<SheetIssues>(() =>
    validateSheet(
      columns.value,
      rows.value.map((row) => row.cells)
    )
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

  // --- Problems, and dismissing them ------------------------------------

  /** Keys of warnings the contributor has acknowledged. */
  const dismissed = ref<Set<string>>(new Set())

  const serverReport = computed(() =>
    database.value && response.value
      ? mapResponse(database.value, rows.value, response.value)
      : null
  )

  /** Problems that could not be tied to an experiment (header-level, orphans). */
  const globalIssues = computed<ReportedIssue[]>(() => serverReport.value?.global ?? [])

  /** Every problem per experiment, client-side and server-side merged. */
  const issuesByUid = computed<Map<number, CardIssue[]>>(() => {
    const reports = new Map<number, ExperimentReport>()
    for (const experiment of serverReport.value?.experiments ?? []) {
      reports.set(experiment.uid, experiment)
    }

    const map = new Map<number, CardIssue[]>()
    rows.value.forEach((row, index) => {
      const issues: CardIssue[] = []
      const client = clientIssues.value.get(index) ?? {}
      const value = (column: string) => (row.cells[column] ?? '').trim()

      for (const [column, issue] of Object.entries(client)) {
        issues.push({
          key: issueKey(row.uid, column, value(column), issue.message),
          column,
          level: issue.level,
          message: issue.message
        })
      }

      const report = reports.get(row.uid)
      for (const cell of report?.cellIssues ?? []) {
        // The client engine mirrors the server's per-cell rules, so only report
        // what it cannot know about — chiefly the range warnings.
        if (client[cell.ref.column]) continue
        issues.push({
          key: issueKey(row.uid, cell.ref.column, value(cell.ref.column), cell.issue.message),
          column: cell.ref.column,
          level: cell.severity === 'error' ? 'error' : 'warn',
          message: cell.issue.message
        })
      }
      for (const file of report?.fileIssues ?? []) {
        const attached = file.kindKey ? timeSeries.value[`${row.uid}:${file.kindKey}`] : undefined
        issues.push({
          key: issueKey(row.uid, file.kindKey ?? 'file', attached?.name ?? '', file.issue.message),
          kindKey: file.kindKey,
          level: file.severity === 'error' ? 'error' : 'warn',
          message: file.issue.message
        })
      }
      issues.push(...testDataIssues(row))
      map.set(row.uid, issues)
    })
    return map
  })

  /**
   * What the server cannot see about test data: the files are optional, so
   * an experiment submitted with none is worth a second look, and a file
   * whose own name is not the specimen id may have landed on the wrong card
   * (the archive renames it to `<id>.csv`, so the name never reaches the
   * validator). Both are warnings the contributor can dismiss.
   */
  function testDataIssues(row: ExperimentRow): CardIssue[] {
    const id = (row.cells.id ?? '').trim()
    const kinds = timeSeriesKindsFor(database.value)
    if (id === '' || kinds.length === 0) return []

    const issues: CardIssue[] = []
    let attachedCount = 0
    for (const kind of kinds) {
      const attached = timeSeries.value[`${row.uid}:${kind.key}`]
      if (!attached) continue
      attachedCount++
      const stem = attached.name.replace(/\.csv$/i, '')
      if (stem !== id) {
        const message = `The attached file is named "${attached.name}", not after the specimen id — check that it belongs to this experiment.`
        issues.push({
          key: issueKey(row.uid, kind.key, attached.name, message),
          kindKey: kind.key,
          level: 'warn',
          message
        })
      }
    }
    if (attachedCount === 0) {
      const message = NO_TEST_DATA_MESSAGE
      issues.push({
        key: issueKey(row.uid, 'file', '', message),
        kindKey: null,
        level: 'warn',
        message
      })
    }
    return issues
  }

  /** Errors are never dismissible — they have to be fixed. */
  function isDismissed(issue: CardIssue): boolean {
    return issue.level === 'warn' && dismissed.value.has(issue.key)
  }

  function issuesFor(uid: number): CardIssue[] {
    return issuesByUid.value.get(uid) ?? []
  }

  function activeIssuesFor(uid: number): CardIssue[] {
    return issuesFor(uid).filter((issue) => !isDismissed(issue))
  }

  function dismissedIssuesFor(uid: number): CardIssue[] {
    return issuesFor(uid).filter((issue) => isDismissed(issue))
  }

  function levelFor(uid: number): 'pass' | 'warn' | 'fail' {
    const issues = activeIssuesFor(uid)
    if (issues.some((issue) => issue.level === 'error')) return 'fail'
    return issues.length ? 'warn' : 'pass'
  }

  /** The live problem for a cell, so the field can show it inline. */
  function cellIssueFor(uid: number, column: string): CellIssue | undefined {
    const issue = activeIssuesFor(uid).find((entry) => entry.column === column)
    return issue ? { level: issue.level, message: issue.message } : undefined
  }

  function dismissIssue(key: string): void {
    dismissed.value.add(key)
  }

  function restoreIssue(key: string): void {
    dismissed.value.delete(key)
  }

  /** Restore one experiment's dismissed warnings, or every one when uid is omitted. */
  function restoreDismissed(uid?: number): void {
    if (uid === undefined) {
      dismissed.value.clear()
      return
    }
    for (const issue of dismissedIssuesFor(uid)) dismissed.value.delete(issue.key)
  }

  const activeWarningCount = computed(() => {
    let count = globalIssues.value.filter((entry) => entry.severity === 'warning').length
    for (const uid of issuesByUid.value.keys()) {
      count += activeIssuesFor(uid).filter((issue) => issue.level === 'warn').length
    }
    return count
  })

  /** Experiments that still have something to look at, in batch order. */
  const problemSummary = computed<ExperimentProblems[]>(() =>
    rows.value
      .map((row, index) => {
        const active = activeIssuesFor(row.uid)
        return {
          uid: row.uid,
          index,
          id: (row.cells.id ?? '').trim(),
          errors: active.filter((issue) => issue.level === 'error').length,
          warnings: active.filter((issue) => issue.level === 'warn').length,
          issues: active
        }
      })
      .filter((entry) => entry.errors > 0 || entry.warnings > 0)
  )

  /** Every unresolved error, client-side and server-side, batch-wide. */
  const activeErrorCount = computed(
    () =>
      globalIssues.value.filter((entry) => entry.severity === 'error').length +
      problemSummary.value.reduce((total, entry) => total + entry.errors, 0)
  )

  /** Experiments with an id but not one test-data file. */
  const withoutTestDataCount = computed(() =>
    rows.value.reduce(
      (total, row) =>
        total +
        (activeIssuesFor(row.uid).some((issue) => issue.message === NO_TEST_DATA_MESSAGE) ? 1 : 0),
      0
    )
  )

  /**
   * True while the server's verdict is unknown because a check is coming: one
   * is in flight, or an edit has invalidated the last one and the debounce has
   * yet to fire. A card with no *client* issues is not clean yet, only unjudged.
   */
  const checking = computed(
    () =>
      status.value === 'running' ||
      (status.value === 'idle' && !!config.value?.qualityCheckSupported && hasAnyId.value)
  )

  /** The last check failed outright, so there is no verdict to report either. */
  const unverified = computed(() => status.value === 'error')

  const dismissedCount = computed(() => {
    let count = 0
    for (const uid of issuesByUid.value.keys()) count += dismissedIssuesFor(uid).length
    return count
  })

  function selectDatabase(id: DatabaseId): void {
    if (database.value === id) return
    // Columns differ per database; carried-over values would never reach the CSV.
    database.value = id
    rows.value = [newRow()]
    timeSeries.value = {}
    dismissed.value.clear()
    resetQualityCheck()
    resetSubmission()
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
    dismissed.value.clear()
  }

  function resetQualityCheck(): void {
    // A database without a server validator never gets a check: say so up
    // front instead of leaving the bar on "waiting for a pause in editing".
    status.value = config.value && !config.value.qualityCheckSupported ? 'unsupported' : 'idle'
    response.value = null
    errorMessage.value = ''
  }

  /**
   * The upload artifact: the primary CSV (all experiments) plus each attached
   * time-series, named `<id>.csv` in its kind's directory — the layout of the
   * data repository, which both /validate and /contributions expect.
   */
  async function buildArchive(): Promise<File> {
    const columnNames = columns.value.map((column) => column.name)
    const entries = [
      {
        path: config.value!.csvPath,
        content: buildCsv(
          columnNames,
          rows.value.map((r) => r.cells)
        )
      }
    ]
    for (const row of rows.value) {
      const id = (row.cells.id ?? '').trim()
      if (id === '') continue
      for (const kind of timeSeriesKindsFor(database.value!)) {
        const attached = timeSeries.value[`${row.uid}:${kind.key}`]
        if (attached) {
          entries.push({ path: `${kind.directory}/${id}.csv`, content: attached.content })
        }
      }
    }
    return buildTarGz(entries, 'contribution.tar.gz')
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
      const archive = await buildArchive()
      // check_duplicates flags ids that already exist in the database as
      // errors. Opt-in on the endpoint: the data-repo CI validates full repo
      // CSVs and must not get this check.
      const { data } = await defaultApi.validateData(target.type, archive, true)
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

  // --- Submission -------------------------------------------------------

  /**
   * Submittable once the batch is clean: no client-side errors, a server
   * verdict of pass or warn (warnings never block — dismissed or not, they are
   * listed in the PR), and nothing in flight. The databases without a server
   * validator stay locked: the backend refuses to open an unvalidated PR.
   */
  const canSubmit = computed(
    () =>
      hasAnyId.value &&
      clientErrorCount.value === 0 &&
      !checking.value &&
      (status.value === 'pass' || status.value === 'warn') &&
      submitStatus.value !== 'submitting'
  )

  /** Human-readable lines for the PR body, one per dismissed warning. */
  const dismissedWarningMessages = computed<string[]>(() => {
    const messages: string[] = []
    for (const row of rows.value) {
      const id = (row.cells.id ?? '').trim() || `#${row.uid}`
      for (const issue of dismissedIssuesFor(row.uid)) {
        messages.push(`${id}: ${issue.message}`)
      }
    }
    return messages
  })

  async function submit(contributor: ContributorInfo): Promise<void> {
    const target = config.value
    if (!target || !database.value || !canSubmit.value) return

    submitStatus.value = 'submitting'
    submitError.value = ''
    try {
      const archive = await buildArchive()
      const result = await postContribution(
        target.type,
        archive,
        contributor,
        dismissedWarningMessages.value
      )
      pullRequestUrl.value = result.pr_url
      pullRequestNumber.value = result.pr_number
      submitStatus.value = 'submitted'
    } catch (caught) {
      // A 422 carries a full validation report: surface it through the same
      // cell mapping as the automatic check.
      if (isAxiosError(caught) && caught.response?.status === 422) {
        const data = caught.response.data
        if (isValidationResponse(data)) {
          response.value = data
          status.value = deriveStatus(data)
        }
      }
      submitStatus.value = 'error'
      submitError.value = transportError(caught)
    }
  }

  function resetSubmission(): void {
    submitStatus.value = 'idle'
    submitError.value = ''
    pullRequestUrl.value = ''
    pullRequestNumber.value = 0
  }

  // Auto-validate: any edit invalidates the last report and re-checks after a
  // quiet delay. Trailing-only, so continuous typing fires nothing; a failed
  // request is not auto-retried (the manual "Check now" button covers that).
  let debounce: ReturnType<typeof setTimeout> | undefined
  watch(
    [rows, timeSeries],
    () => {
      if (status.value !== 'running') resetQualityCheck()
      // Editing after a submission starts a new draft.
      if (submitStatus.value !== 'submitting') resetSubmission()
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
    rows.value = [newRow()]
    timeSeries.value = {}
    dismissed.value.clear()
    resetQualityCheck()
    resetSubmission()
  }

  return {
    database,
    rows,
    timeSeries,
    status,
    response,
    errorMessage,
    submitStatus,
    submitError,
    pullRequestUrl,
    pullRequestNumber,
    canSubmit,
    dismissedWarningMessages,
    submit,
    resetSubmission,
    config,
    columns,
    experimentCount,
    specimenIds,
    hasAnyId,
    clientIssues,
    clientErrorCount,
    globalIssues,
    checking,
    unverified,
    activeWarningCount,
    activeErrorCount,
    problemSummary,
    withoutTestDataCount,
    dismissedCount,
    issuesFor,
    activeIssuesFor,
    dismissedIssuesFor,
    levelFor,
    cellIssueFor,
    dismissIssue,
    restoreIssue,
    restoreDismissed,
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
