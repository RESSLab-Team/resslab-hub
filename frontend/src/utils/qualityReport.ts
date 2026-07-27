/**
 * Map a `/validate` response back onto the experiments and cells that produced
 * it, so the quality step can show a per-experiment summary and link each issue
 * to its grid cell.
 *
 * Row semantics (pinned by a backend test): a primary-CSV issue with `row === 0`
 * is file/header-level; `row === N` (1-based) is the Nth data row, i.e.
 * `rows[N - 1]` — the grid built the CSV in this order, so the mapping is exact.
 */

import type { ExperimentRow } from '@/stores/contribution'
import { CONTRIBUTION_DATABASES } from '@/utils/contribution'
import type { DatabaseId } from '@/utils/navigation'
import { timeSeriesKindsFor } from '@/utils/timeseries'
import type { FileValidationResult, ValidationIssue, ValidationResponse } from '@/utils/validationResponse'

export type Severity = 'error' | 'warning'
export type ExperimentLevel = 'pass' | 'warn' | 'fail'

export interface CellRef {
  uid: number
  column: string
}

export interface ReportedIssue {
  issue: ValidationIssue
  severity: Severity
}

export interface CellReportedIssue extends ReportedIssue {
  ref: CellRef
}

export interface FileReportedIssue extends ReportedIssue {
  /** The time-series kind key, or null when the file could not be matched. */
  kindKey: string | null
}

export interface ExperimentReport {
  uid: number
  id: string
  level: ExperimentLevel
  cellIssues: CellReportedIssue[]
  fileIssues: FileReportedIssue[]
}

export interface QualityReport {
  experiments: ExperimentReport[]
  /** Issues that could not be tied to an experiment (header/file-level, orphans). */
  global: ReportedIssue[]
}

function dirname(path: string): string {
  const index = path.lastIndexOf('/')
  return index === -1 ? '' : path.slice(0, index)
}

function stem(path: string): string {
  const base = path.slice(path.lastIndexOf('/') + 1)
  return base.replace(/\.csv$/i, '')
}

function levelOf(cellIssues: ReportedIssue[], fileIssues: ReportedIssue[]): ExperimentLevel {
  const all = [...cellIssues, ...fileIssues]
  if (all.some((entry) => entry.severity === 'error')) return 'fail'
  if (all.length > 0) return 'warn'
  return 'pass'
}

export function mapResponse(
  database: DatabaseId,
  rows: ExperimentRow[],
  response: ValidationResponse
): QualityReport {
  const csvPath = CONTRIBUTION_DATABASES[database].csvPath
  const kindByDir = new Map(timeSeriesKindsFor(database).map((kind) => [kind.directory, kind.key]))

  const reports = new Map<number, ExperimentReport>()
  for (const row of rows) {
    reports.set(row.uid, {
      uid: row.uid,
      id: (row.cells.id ?? '').trim(),
      level: 'pass',
      cellIssues: [],
      fileIssues: []
    })
  }

  // First non-empty id wins as the owner of a matching time-series file.
  const uidById = new Map<string, number>()
  for (const row of rows) {
    const id = (row.cells.id ?? '').trim()
    if (id !== '' && !uidById.has(id)) uidById.set(id, row.uid)
  }

  const global: ReportedIssue[] = []

  const eachIssue = (file: FileValidationResult, visit: (i: ValidationIssue, s: Severity) => void) => {
    for (const issue of file.errors ?? []) visit(issue, 'error')
    for (const issue of file.warnings ?? []) visit(issue, 'warning')
  }

  for (const file of response.results) {
    if (file.path === csvPath) {
      eachIssue(file, (issue, severity) => {
        const row = issue.row >= 1 ? rows[issue.row - 1] : undefined
        if (!row) {
          global.push({ issue, severity })
          return
        }
        reports.get(row.uid)!.cellIssues.push({
          ref: { uid: row.uid, column: issue.column },
          issue,
          severity
        })
      })
    } else {
      const kindKey = kindByDir.get(dirname(file.path)) ?? null
      const uid = uidById.get(stem(file.path))
      eachIssue(file, (issue, severity) => {
        if (uid === undefined) {
          global.push({ issue, severity })
          return
        }
        reports.get(uid)!.fileIssues.push({ kindKey, issue, severity })
      })
    }
  }

  for (const report of reports.values()) {
    report.level = levelOf(report.cellIssues, report.fileIssues)
  }

  return { experiments: [...reports.values()], global }
}
