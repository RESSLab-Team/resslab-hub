import { defaultApi } from '@/plugins/axios'
import { useDictionaryStore } from '@/stores/dictionary'
import { buildCsv, CONTRIBUTION_DATABASES } from '@/utils/contribution'
import { normalizeCsvText } from '@/utils/csv'
import { describeFailure, type FailureReport } from '@/utils/failureReport'
import type { IntakePending, IntakePlan } from '@/utils/intake'
import type { DatabaseId } from '@/utils/navigation'
import { mapResponse, type ExperimentReport, type ReportedIssue } from '@/utils/qualityReport'
import { postContribution } from '@/utils/submission'
import { buildTarGz } from '@/utils/tar'
import {
  checkTimeSeriesFile,
  fileStemFor,
  timeSeriesKindsFor,
  type TimeSeriesKind,
  type TimeSeriesReport
} from '@/utils/timeseries'
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
  /** Normalized text (LF, final newline, no BOM): what the archive carries. */
  content: string
  rows: number
  /** What the client found in the file; its errors are the server's too. */
  report: TimeSeriesReport
}

/** One test-data slot of a card, for the minimalist chip in the card head. */
export type KindStatus = 'ok' | 'missing' | 'missing_required' | 'error' | 'warn' | 'todo'

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
  /** The experiment has no file where one is expected. */
  missing?: true
  /**
   * `todo` is a blank field on a draft experiment (one just added by hand):
   * shown as a neutral hint, never counted as a problem. It becomes a real
   * error or warning once the draft settles.
   */
  level: 'error' | 'warn' | 'todo'
  message: string
}

/** What a field shows under its input: the issue's level and message. */
export interface FieldIssue {
  level: CardIssue['level']
  message: string
}

function issueKey(uid: number, target: string, signature: string, message: string): string {
  return `${uid}|${target}|${signature}|${message}`
}

/** Warning on an experiment that would be submitted with its record only. */
export const NO_TEST_DATA_MESSAGE =
  'No test data attached — the experiment will be submitted with its metadata only.'
/** Error on a slot every experiment of the database is expected to fill. */
export const MISSING_REQUIRED_MESSAGE = 'Required test data is missing.'

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

/** What the last bulk drop did, for the report shown under the drop zone. */
export interface IntakeSummary {
  /** Name of the primary CSV that was read, if any. */
  primaryName: string | null
  /** Experiments added by that CSV, and experiments it updated (same id). */
  added: number
  updated: number
  /** Other files that also looked like a primary CSV and were left alone. */
  primaryCandidates: string[]
  /** Curve files attached, per response type key. */
  attached: Record<string, number>
  /** Files that are not CSV. */
  skipped: string[]
  noise: number
}

/** Idle time after the last edit before the server check fires. */
const AUTO_VALIDATE_DELAY_MS = 2000

/**
 * How long a hand-added experiment stays a draft with nobody editing it. A
 * draft is also settled sooner when the contributor moves on to something
 * else or fills in every required field (see `settle`).
 */
export const DRAFT_SETTLE_MS = 30_000

export const useContributionStore = defineStore('contribution', () => {
  const dictionary = useDictionaryStore()

  const database = ref<DatabaseId | null>(null)
  let uidCounter = 0
  const newRow = (cells: Record<string, string> = {}): ExperimentRow => ({
    uid: uidCounter++,
    cells
  })

  /** Starts empty: a contributor imports a CSV or adds experiments by hand. */
  const rows = ref<ExperimentRow[]>([])
  /** Attached time-series, keyed by `${row.uid}:${TimeSeriesKind.key}`. */
  const timeSeries = ref<Record<string, AttachedTimeSeries>>({})
  /** Curve files from a bulk drop that still need a home. */
  const pendingFiles = ref<IntakePending[]>([])
  const lastIntake = ref<IntakeSummary | null>(null)

  const status = ref<QualityCheckStatus>('idle')
  const response = ref<ValidationResponse | null>(null)
  const errorMessage = ref('')
  /** The technical side of a failed check, for the details fold and bug reports. */
  const checkFailure = ref<FailureReport | null>(null)

  const submitStatus = ref<'idle' | 'submitting' | 'submitted' | 'error'>('idle')
  const submitError = ref('')
  const submitFailure = ref<FailureReport | null>(null)
  const pullRequestUrl = ref('')
  const pullRequestNumber = ref(0)

  const config = computed(() => (database.value ? CONTRIBUTION_DATABASES[database.value] : null))
  const columns = computed(() => dictionary.columnsFor(database.value))

  const experimentCount = computed(() => rows.value.length)
  const specimenIds = computed(() =>
    rows.value.map((row) => (row.cells.id ?? '').trim()).filter((id) => id !== '')
  )
  const hasAnyId = computed(() => specimenIds.value.length > 0)

  // --- Drafts -----------------------------------------------------------
  // An experiment added by hand starts as a draft: its blank fields are hints,
  // not errors, and the server check waits. It settles into a normally checked
  // experiment when the contributor moves on (adds another, edits another,
  // folds the card, asks for a check), completes it, or pauses for a while.

  /** Uids of the experiments still being drafted. */
  const drafts = ref<Set<number>>(new Set())
  /**
   * Whether any test data has been attached to this batch. Until then an
   * expected file that is absent is a hint, not an error: a CSV import
   * lands a whole batch at once and the files come next, and turning every
   * card red before the contributor has had the chance is no help. Once the
   * files start arriving, the ones still missing are real problems.
   */
  const testDataStarted = ref(false)
  const checkPaused = computed(() => drafts.value.size > 0)

  function isDraft(uid: number): boolean {
    return drafts.value.has(uid)
  }

  let debounce: ReturnType<typeof setTimeout> | undefined
  let settleTimer: ReturnType<typeof setTimeout> | undefined

  /** Run the server check after a quiet delay, unless something rules it out. */
  function scheduleCheck(): void {
    clearTimeout(debounce)
    if (!config.value?.qualityCheckSupported || !hasAnyId.value || checkPaused.value) return
    debounce = setTimeout(() => {
      if (status.value !== 'running') runQualityCheck()
    }, AUTO_VALIDATE_DELAY_MS)
  }

  /** End one draft, or every draft when uid is omitted; the check resumes. */
  function settle(uid?: number): void {
    if (drafts.value.size === 0) return
    if (uid === undefined) drafts.value.clear()
    else if (!drafts.value.delete(uid)) return
    if (drafts.value.size === 0) {
      clearTimeout(settleTimer)
      scheduleCheck()
    }
  }

  /** The contributor is editing `uid`: working on another experiment ends the drafts. */
  function touch(uid: number): void {
    if (!drafts.value.has(uid)) settle()
  }

  /** Every required field (the id included) has a value. */
  function isComplete(row: ExperimentRow): boolean {
    const filled = (column: string) => (row.cells[column] ?? '').trim() !== ''
    return filled('id') && columns.value.every((column) => column.nullable || filled(column.name))
  }

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
      const draft = drafts.value.has(row.uid)

      for (const [column, issue] of Object.entries(client)) {
        issues.push({
          key: issueKey(row.uid, column, value(column), issue.message),
          column,
          // On a draft, what is still blank is a hint; what was typed wrong
          // is feedback and keeps its level.
          level: draft && value(column) === '' ? 'todo' : issue.level,
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
      const local = testDataIssues(row, draft)
      for (const file of report?.fileIssues ?? []) {
        const attached = file.kindKey ? timeSeries.value[`${row.uid}:${file.kindKey}`] : undefined
        // The client reads the file the way the server does, so a file it
        // already rejects is not reported twice.
        if (local.some((issue) => issue.kindKey === file.kindKey && issue.level === 'error')) {
          continue
        }
        issues.push({
          key: issueKey(row.uid, file.kindKey ?? 'file', attached?.name ?? '', file.issue.message),
          kindKey: file.kindKey,
          level: file.severity === 'error' ? 'error' : 'warn',
          message: file.issue.message
        })
      }
      issues.push(...local)
      map.set(row.uid, issues)
    })
    return map
  })

  /**
   * The test-data problems of one experiment, per response type:
   *  - a slot the database expects filled and that is empty is an error (a
   *    neutral hint while the experiment is a draft); with no slot expected,
   *    an experiment with no file at all gets the blanket warning instead;
   *  - what the file check found: its errors are the server's (a missing
   *    column, a value that is not a number), its warnings are for the
   *    contributor to judge (values on the wrong scale);
   *  - a file whose own name is not the specimen's may have landed on the
   *    wrong card (the archive renames it, so the name never reaches the
   *    validator).
   * Keys embed the filename, so a dismissed warning comes back with a new file.
   */
  function testDataIssues(row: ExperimentRow, draft: boolean): CardIssue[] {
    const id = (row.cells.id ?? '').trim()
    const kinds = timeSeriesKindsFor(database.value)
    if (id === '' || kinds.length === 0) return []

    const issues: CardIssue[] = []
    let attachedCount = 0
    for (const kind of kinds) {
      const attached = timeSeries.value[`${row.uid}:${kind.key}`]
      if (!attached) {
        if (kind.required) {
          issues.push({
            key: issueKey(row.uid, kind.key, '', MISSING_REQUIRED_MESSAGE),
            kindKey: kind.key,
            missing: true,
            level: draft || !testDataStarted.value ? 'todo' : 'error',
            message: MISSING_REQUIRED_MESSAGE
          })
        }
        continue
      }
      attachedCount++
      const push = (level: CardIssue['level'], message: string) =>
        issues.push({
          key: issueKey(row.uid, kind.key, attached.name, message),
          kindKey: kind.key,
          level,
          message
        })
      for (const message of attached.report.errors) push('error', message)
      for (const message of attached.report.warnings) push('warn', message)
      const stem = attached.name.replace(/\.csv$/i, '')
      const expected = fileStemFor(kind, id)
      if (stem !== expected) {
        push(
          'warn',
          `The attached file is named "${attached.name}", not "${expected}.csv" after the specimen id — check that it belongs to this experiment.`
        )
      }
    }
    if (attachedCount === 0 && !kinds.some((kind) => kind.required)) {
      issues.push({
        key: issueKey(row.uid, 'file', '', NO_TEST_DATA_MESSAGE),
        kindKey: null,
        missing: true,
        level: draft ? 'todo' : 'warn',
        message: NO_TEST_DATA_MESSAGE
      })
    }
    return issues
  }

  /**
   * Attach a measured-response file to an experiment. Nothing is refused:
   * the file is read (and tidied for the data repository), what is wrong
   * with it becomes issues on the card, and the contributor fixes or
   * replaces it from there.
   */
  function attachSeries(uid: number, kind: TimeSeriesKind, name: string, raw: string): void {
    const content = normalizeCsvText(raw)
    const report = checkTimeSeriesFile(kind, content)
    timeSeries.value[`${uid}:${kind.key}`] = { name, content, rows: report.rows, report }
    testDataStarted.value = true
    touch(uid)
  }

  function removeSeries(uid: number, kind: TimeSeriesKind): void {
    delete timeSeries.value[`${uid}:${kind.key}`]
    touch(uid)
  }

  /** The state of one test-data slot, for the chip in the card head. */
  function kindStatus(uid: number, kind: TimeSeriesKind): KindStatus {
    const attached = timeSeries.value[`${uid}:${kind.key}`]
    const issues = issuesFor(uid).filter(
      (issue) => issue.kindKey === kind.key && !isDismissed(issue)
    )
    if (issues.some((issue) => issue.level === 'error')) {
      return attached ? 'error' : 'missing_required'
    }
    if (issues.some((issue) => issue.level === 'todo')) return 'todo'
    if (issues.some((issue) => issue.level === 'warn')) return 'warn'
    return attached ? 'ok' : 'missing'
  }

  /** Errors are never dismissible — they have to be fixed. */
  function isDismissed(issue: CardIssue): boolean {
    return issue.level === 'warn' && dismissed.value.has(issue.key)
  }

  function issuesFor(uid: number): CardIssue[] {
    return issuesByUid.value.get(uid) ?? []
  }

  /** The problems that count: not dismissed, and not a draft's blank fields. */
  function activeIssuesFor(uid: number): CardIssue[] {
    return issuesFor(uid).filter((issue) => issue.level !== 'todo' && !isDismissed(issue))
  }

  /** A draft's blank required fields, for its neutral "still to fill in" badge. */
  function todoFor(uid: number): CardIssue[] {
    return issuesFor(uid).filter((issue) => issue.level === 'todo')
  }

  function dismissedIssuesFor(uid: number): CardIssue[] {
    return issuesFor(uid).filter((issue) => isDismissed(issue))
  }

  function levelFor(uid: number): 'pass' | 'warn' | 'fail' {
    const issues = activeIssuesFor(uid)
    if (issues.some((issue) => issue.level === 'error')) return 'fail'
    return issues.length ? 'warn' : 'pass'
  }

  /** The live problem (or draft hint) for a cell, so the field can show it inline. */
  function cellIssueFor(uid: number, column: string): FieldIssue | undefined {
    const issue = issuesFor(uid).find((entry) => entry.column === column && !isDismissed(entry))
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

  /** Experiments with an id but not one test-data file, drafts and dismissals aside. */
  const withoutTestDataCount = computed(() =>
    rows.value.reduce((total, row) => {
      const kinds = timeSeriesKindsFor(database.value)
      const none = !kinds.some((kind) => timeSeries.value[`${row.uid}:${kind.key}`])
      const flagged = activeIssuesFor(row.uid).some((issue) => issue.missing)
      return total + (none && flagged ? 1 : 0)
    }, 0)
  )

  /** Experiments whose expected file is still a hint (no test data attached to the batch yet). */
  const awaitingTestDataCount = computed(() => {
    let count = 0
    for (const uid of issuesByUid.value.keys()) {
      if (todoFor(uid).some((issue) => issue.missing && issue.kindKey)) count++
    }
    return count
  })

  /** Test-data errors the server cannot see (an expected file that is absent). */
  const fileErrorCount = computed(() => {
    let count = 0
    for (const uid of issuesByUid.value.keys()) {
      count += activeIssuesFor(uid).filter(
        (issue) => issue.kindKey !== undefined && issue.level === 'error'
      ).length
    }
    return count
  })

  /**
   * True while the server's verdict is unknown because a check is coming: one
   * is in flight, or an edit has invalidated the last one and the debounce has
   * yet to fire. A card with no *client* issues is not clean yet, only unjudged.
   */
  const checking = computed(
    () =>
      status.value === 'running' ||
      (status.value === 'idle' &&
        !!config.value?.qualityCheckSupported &&
        hasAnyId.value &&
        !checkPaused.value)
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
    rows.value = []
    timeSeries.value = {}
    clearIntake()
    dismissed.value.clear()
    drafts.value.clear()
    testDataStarted.value = false
    resetQualityCheck()
    resetSubmission()
  }

  /** Append a blank experiment as a draft; returns its uid so the editor can open it. */
  function addRow(): number {
    // Starting another experiment is moving on from the previous draft.
    settle()
    const row = newRow()
    rows.value.push(row)
    drafts.value.add(row.uid)
    return row.uid
  }

  function duplicateRow(uid: number): void {
    const source = rowByUid(uid)
    if (!source) return
    settle()
    // Ids must be unique, so a copy starts without one — as a draft, like a
    // hand-added experiment.
    const row = newRow({ ...source.cells, id: '' })
    rows.value.push(row)
    drafts.value.add(row.uid)
  }

  function removeRow(uid: number): void {
    rows.value = rows.value.filter((row) => row.uid !== uid)
    for (const key of Object.keys(timeSeries.value)) {
      if (key.startsWith(`${uid}:`)) delete timeSeries.value[key]
    }
    settle(uid)
  }

  /** Replace all experiments from imported CSV rows (never drafts: a file is complete). */
  function importRows(records: Array<Record<string, string>>): void {
    rows.value = records.map((cells) => newRow(cells))
    timeSeries.value = {}
    clearIntake()
    dismissed.value.clear()
    drafts.value.clear()
    testDataStarted.value = false
  }

  /**
   * Add imported rows to the batch instead of replacing it: a row whose id is
   * already there updates that experiment (its attached files stay, keyed by
   * uid), the others are appended. Rows without an id are always appended.
   * Never drafts: a file is complete.
   */
  function mergeRows(records: Array<Record<string, string>>): { added: number; updated: number } {
    settle()
    let added = 0
    let updated = 0
    for (const cells of records) {
      const id = (cells.id ?? '').trim()
      const existing = id ? rows.value.find((row) => (row.cells.id ?? '').trim() === id) : undefined
      if (existing) {
        existing.cells = { ...existing.cells, ...cells }
        updated++
      } else {
        rows.value.push(newRow(cells))
        added++
      }
    }
    return { added, updated }
  }

  // --- Bulk intake ------------------------------------------------------
  // A dropped folder, zip or set of files arrives as an `IntakePlan` (see
  // `utils/intake.ts`): the primary CSV merges into the batch, the curve
  // files that were placed attach, and the rest waits in `pendingFiles` for
  // the contributor to assign or ignore.

  function uidForId(id: string): number | undefined {
    return rows.value.find((row) => (row.cells.id ?? '').trim() === id)?.uid
  }

  function applyIntake(plan: IntakePlan): IntakeSummary {
    const summary: IntakeSummary = {
      primaryName: plan.primary?.file.name ?? null,
      added: 0,
      updated: 0,
      primaryCandidates: plan.primaryCandidates.map((file) => file.path),
      attached: {},
      skipped: plan.skipped.map((file) => file.path),
      noise: plan.noise
    }
    if (plan.primary) {
      const counts = mergeRows(plan.primary.table.rows)
      summary.added = counts.added
      summary.updated = counts.updated
    }
    for (const match of plan.matched) {
      const uid = uidForId(match.id)
      if (uid === undefined) continue
      attachSeries(uid, match.kind, match.file.name, match.text)
      summary.attached[match.kind.key] = (summary.attached[match.kind.key] ?? 0) + 1
    }
    // A file dropped again replaces its earlier pending entry (same path).
    const paths = new Set(plan.pending.map((entry) => entry.file.path))
    pendingFiles.value = [
      ...pendingFiles.value.filter((entry) => !paths.has(entry.file.path)),
      ...plan.pending
    ]
    lastIntake.value = summary
    return summary
  }

  /** Give a pending file a home: it attaches like any other and leaves the list. */
  function assignPending(pendingId: number, uid: number, kind: TimeSeriesKind): void {
    const entry = pendingFiles.value.find((item) => item.id === pendingId)
    if (!entry) return
    attachSeries(uid, kind, entry.file.name, entry.text)
    pendingFiles.value = pendingFiles.value.filter((item) => item.id !== pendingId)
  }

  function ignorePending(pendingId: number): void {
    pendingFiles.value = pendingFiles.value.filter((item) => item.id !== pendingId)
  }

  function clearIntake(): void {
    pendingFiles.value = []
    lastIntake.value = null
  }

  function resetQualityCheck(): void {
    // A database without a server validator never gets a check: say so up
    // front instead of leaving the bar on "waiting for a pause in editing".
    status.value = config.value && !config.value.qualityCheckSupported ? 'unsupported' : 'idle'
    response.value = null
    errorMessage.value = ''
    checkFailure.value = null
  }

  /** What was being checked or submitted, for a failure report. */
  function failureContext(): Omit<Parameters<typeof describeFailure>[1], 'operation' | 'message'> {
    return {
      database: database.value ?? undefined,
      type: config.value?.type,
      experiments: rows.value.length,
      files: Object.keys(timeSeries.value).length
    }
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
          entries.push({
            path: `${kind.directory}/${fileStemFor(kind, id)}.csv`,
            content: attached.content
          })
        }
      }
    }
    return buildTarGz(entries, 'contribution.tar.gz')
  }

  async function runQualityCheck(): Promise<void> {
    const target = config.value
    if (!target || !database.value || columns.value.length === 0) return
    // Asking for a check ends the drafts, and this call is the check.
    settle()
    clearTimeout(debounce)

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
      checkFailure.value = describeFailure(caught, {
        operation: 'validate',
        message: errorMessage.value,
        ...failureContext()
      })
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
      fileErrorCount.value === 0 &&
      awaitingTestDataCount.value === 0 &&
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

  async function submit(): Promise<void> {
    const target = config.value
    if (!target || !database.value || !canSubmit.value) return

    settle()
    submitStatus.value = 'submitting'
    submitError.value = ''
    try {
      const archive = await buildArchive()
      const result = await postContribution(target.type, archive, dismissedWarningMessages.value)
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
      submitFailure.value = describeFailure(caught, {
        operation: 'submit',
        message: submitError.value,
        ...failureContext()
      })
    }
  }

  function resetSubmission(): void {
    submitStatus.value = 'idle'
    submitError.value = ''
    submitFailure.value = null
    pullRequestUrl.value = ''
    pullRequestNumber.value = 0
  }

  // Auto-validate: any edit invalidates the last report and re-checks after a
  // quiet delay. Trailing-only, so continuous typing fires nothing; a failed
  // request is not auto-retried (the manual "Check now" button covers that).
  // While an experiment is being drafted the check waits instead, and a long
  // pause settles the draft.
  watch(
    [rows, timeSeries],
    () => {
      if (status.value !== 'running') resetQualityCheck()
      // Editing after a submission starts a new batch.
      if (submitStatus.value !== 'submitting') resetSubmission()
      // A draft with every required field filled is done: check it now.
      for (const uid of [...drafts.value]) {
        const row = rowByUid(uid)
        if (row && isComplete(row)) drafts.value.delete(uid)
      }
      clearTimeout(settleTimer)
      if (drafts.value.size > 0) settleTimer = setTimeout(() => settle(), DRAFT_SETTLE_MS)
      scheduleCheck()
    },
    { deep: true }
  )

  function reset(): void {
    database.value = null
    rows.value = []
    timeSeries.value = {}
    clearIntake()
    dismissed.value.clear()
    drafts.value.clear()
    testDataStarted.value = false
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
    checkFailure,
    submitStatus,
    submitError,
    submitFailure,
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
    checkPaused,
    isDraft,
    settle,
    touch,
    clientIssues,
    clientErrorCount,
    globalIssues,
    checking,
    unverified,
    activeWarningCount,
    activeErrorCount,
    problemSummary,
    withoutTestDataCount,
    awaitingTestDataCount,
    fileErrorCount,
    dismissedCount,
    issuesFor,
    activeIssuesFor,
    todoFor,
    dismissedIssuesFor,
    levelFor,
    cellIssueFor,
    attachSeries,
    removeSeries,
    kindStatus,
    dismissIssue,
    restoreIssue,
    restoreDismissed,
    rowByUid,
    selectDatabase,
    addRow,
    duplicateRow,
    removeRow,
    importRows,
    mergeRows,
    pendingFiles,
    lastIntake,
    applyIntake,
    assignPending,
    ignorePending,
    clearIntake,
    resetQualityCheck,
    runQualityCheck,
    reset
  }
})
