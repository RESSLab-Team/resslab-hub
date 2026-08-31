/**
 * Helpers for the curation (review) views: map backend curation payloads onto
 * the shapes the contribute-flow utilities already understand, so the quality
 * report and time-series machinery are reused unchanged.
 */

import type { CurationDetail, CurationFile } from '@/backend'
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
