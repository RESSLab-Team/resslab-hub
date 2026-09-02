/**
 * Helpers for the curation (review) views: map backend curation payloads onto
 * the shapes the contribute-flow utilities already understand, so the quality
 * report and time-series machinery are reused unchanged.
 */

import {
  MaterialField,
  ResidualStressField,
  type CurationDetail,
  type CurationFile
} from '@/backend'
import type { ExperimentRow } from '@/stores/contribution'
import { CONTRIBUTION_DATABASES } from '@/utils/contribution'
import type { DatabaseId } from '@/utils/navigation'
import { timeSeriesKindsFor, type TimeSeriesKind } from '@/utils/timeseries'

/** Invert `CONTRIBUTION_DATABASES`: backend uploader Type value → DatabaseId. */
export function databaseIdForType(type: string): DatabaseId | null {
  for (const [id, entry] of Object.entries(CONTRIBUTION_DATABASES)) {
    if (entry.type === type) return id as DatabaseId
  }
  return null
}

/**
 * Reconstructed batch rows in the shape `mapResponse` (utils/qualityReport)
 * consumes. The backend guarantees the validation endpoint's row indices match
 * this order, so `uid` can simply be the array index.
 */
export function toExperimentRows(detail: CurationDetail): ExperimentRow[] {
  return detail.experiments.map((experiment, index) => ({
    uid: index,
    cells: experiment.cells
  }))
}

/** The time-series kind a submitted file belongs to, from its directory. */
export function kindForFile(database: DatabaseId, file: CurationFile): TimeSeriesKind | undefined {
  return timeSeriesKindsFor(database).find((kind) => kind.directory === file.timeseries_dir)
}

/** "3 d ago"-style age for the queue, from an ISO timestamp. */
export function formatAge(iso: string, locale: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: 'always' })
  const seconds = (then - Date.now()) / 1000
  const steps: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31536000],
    ['month', 2592000],
    ['week', 604800],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60]
  ]
  for (const [unit, span] of steps) {
    if (Math.abs(seconds) >= span) return formatter.format(Math.round(seconds / span), unit)
  }
  return formatter.format(Math.round(seconds), 'second')
}

/** A submitted cell parsed for chart/statistics use: number, string, or null. */
export function cellValue(raw: string | undefined): string | number | null {
  const value = (raw ?? '').trim()
  if (value === '' || value === 'NR') return null
  const numeric = Number(value)
  return Number.isNaN(numeric) ? value : numeric
}

/** True when the cell carries no reported value (blank or the NR sentinel). */
export function isMissing(raw: string | undefined): boolean {
  const value = (raw ?? '').trim()
  return value === '' || value === 'NR'
}

type Derivation = (cells: Record<string, string>) => string | undefined

/**
 * Columns the database derives from others (`column_property` in the ORM
 * models). A submitted CSV never carries them, so compute them here the same
 * way: the cohort chips and the ghost chart read them like any other cell, and
 * the value has the same format as the stored rows, so the cohort query finds
 * them. A derivation with a missing input stays missing, like the SQL
 * expression with a NULL.
 */
const DERIVED_CELLS: Partial<Record<DatabaseId, Record<string, Derivation>>> = {
  cyclic: {
    // material.type = grade || '-' || spec
    [MaterialField.Type]: (cells) => {
      const grade = cells[MaterialField.Grade]
      const spec = cells[MaterialField.Spec]
      if (isMissing(grade) || isMissing(spec)) return undefined
      return `${grade.trim()}-${spec.trim()}`
    }
  },
  residuals: {
    // residual_stress.h_over_b = h / b
    [ResidualStressField.HOverB]: (cells) => {
      const h = cellValue(cells[ResidualStressField.H])
      const b = cellValue(cells[ResidualStressField.B])
      if (typeof h !== 'number' || typeof b !== 'number' || b === 0) return undefined
      return String(h / b)
    }
  }
}

/** The cells plus the derived columns of that database (a value the CSV already carries is kept). */
export function withDerivedCells(
  database: DatabaseId | null,
  cells: Record<string, string>
): Record<string, string> {
  const derivations = database ? DERIVED_CELLS[database] : undefined
  if (!derivations) return cells
  const derived = { ...cells }
  for (const [column, derive] of Object.entries(derivations)) {
    if (!isMissing(derived[column])) continue
    const value = derive(cells)
    if (value !== undefined) derived[column] = value
  }
  return derived
}

/** A copy of the detail whose experiment cells carry the derived columns. */
export function withDerivedExperiments(detail: CurationDetail): CurationDetail {
  const database = databaseIdForType(detail.type)
  if (!database || !DERIVED_CELLS[database]) return detail
  return {
    ...detail,
    experiments: detail.experiments.map((experiment) => ({
      ...experiment,
      cells: withDerivedCells(database, experiment.cells)
    }))
  }
}
