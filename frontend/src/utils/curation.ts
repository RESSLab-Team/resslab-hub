/**
 * Helpers for the curation (review) views: map backend curation payloads onto
 * the shapes the contribute-flow utilities already understand, so the quality
 * report and time-series machinery are reused unchanged.
 */

import type { CurationDetail, CurationFile } from '@/backend'
import type { ExperimentRow } from '@/stores/contribution'
import { CONTRIBUTION_DATABASES } from '@/utils/contribution'
import type { DatabaseId } from '@/utils/navigation'
import { fileStemFor, timeSeriesKindsFor, type TimeSeriesKind } from '@/utils/timeseries'

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

/**
 * A submitted row as the editor holds it. `NR` collapses to an empty cell,
 * the same way `readCsvTable` treats an imported file: it round-trips back to
 * `NR` on submit, and an empty field reads better than a literal "NR".
 */
export function toEditorCells(cells: Record<string, string>): Record<string, string> {
  const values: Record<string, string> = {}
  for (const [name, raw] of Object.entries(cells)) {
    const value = (raw ?? '').trim()
    values[name] = value.toUpperCase() === 'NR' ? '' : value
  }
  return values
}

/** One submitted time-series file, matched to the experiment it belongs to. */
export interface EditableFile {
  path: string
  /** File name, what the editor shows next to the slot. */
  name: string
  kind: TimeSeriesKind
  /** Index into `detail.experiments`. */
  index: number
}

/**
 * Split a submission's files into the ones the editor can hold and the rest.
 *
 * A file is placeable when its directory is a known time-series kind and its
 * name points at one of the submitted experiments. The others (the provenance
 * record, anything unexpected) stay on the branch untouched, and the editor
 * says so rather than pretending they are gone.
 */
export function editableFiles(
  database: DatabaseId,
  detail: CurationDetail
): { placed: EditableFile[]; skipped: string[] } {
  const placed: EditableFile[] = []
  const skipped: string[] = []
  for (const file of detail.files) {
    if (file.kind !== 'timeseries') continue
    const kind = kindForFile(database, file)
    const stem =
      file.path
        .split('/')
        .pop()
        ?.replace(/\.csv$/i, '') ?? ''
    // Match on the id first; fall back to the stem the kind would have
    // written, since EBF names its files `id74.csv` for the record `74`.
    const index = kind
      ? detail.experiments.findIndex(
          (experiment) =>
            experiment.id === file.experiment_id || fileStemFor(kind, experiment.id) === stem
        )
      : -1
    if (!kind || index < 0) {
      skipped.push(file.path)
      continue
    }
    placed.push({ path: file.path, name: file.path.split('/').pop() ?? file.path, kind, index })
  }
  return { placed, skipped }
}

/**
 * `items.map(run)` with at most `limit` calls in flight, results in order.
 *
 * Loading a submission asks the backend for one file per request; a batch with
 * many curves would otherwise fire them all at once and trip the rate limit.
 */
export async function mapLimit<T, R>(
  items: T[],
  limit: number,
  run: (item: T) => Promise<R>
): Promise<R[]> {
  const results: R[] = new Array(items.length)
  let next = 0
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const index = next++
      results[index] = await run(items[index])
    }
  })
  await Promise.all(workers)
  return results
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
