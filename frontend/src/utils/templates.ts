/**
 * Downloads a contributor needs to prepare a submission: a template CSV
 * (header + one example row from the dictionary's example values), the data
 * dictionary itself, an example file per response type, and a starter kit —
 * the whole folder laid out the way the repository (and the drop zone)
 * expects it. All built from the runtime dictionary and the response-type
 * table, so they stay in lockstep with what the editor validates and the
 * backend expects.
 */

import type { DictColumn } from '@/stores/dictionary'
import { CONTRIBUTION_DATABASES, escapeCsv } from '@/utils/contribution'
import type { DatabaseId } from '@/utils/navigation'
import { fileStemFor, type TimeSeriesKind } from '@/utils/timeseries'
import download from 'downloadjs'

/** Placeholder specimen id in the starter kit; a valid id, so the kit round-trips. */
export const EXAMPLE_ID = 'EXAMPLE-ID'

/** `braces/steel_braces.csv` → `steel_braces.csv`. */
function primaryCsvName(database: DatabaseId): string {
  const path = CONTRIBUTION_DATABASES[database].csvPath
  return path.slice(path.lastIndexOf('/') + 1)
}

export function buildTemplateCsv(columns: DictColumn[]): string {
  const header = columns.map((column) => escapeCsv(column.name)).join(',')
  const example = columns.map((column) => escapeCsv(column.example)).join(',')
  return `${header}\n${example}\n`
}

export function buildDictionaryCsv(columns: DictColumn[]): string {
  const header = 'column_name,description,symbol,unit,type,example_value,nullable'
  const rows = columns.map((column) =>
    [
      column.name,
      column.description,
      column.symbol,
      column.unit,
      column.type,
      column.example,
      column.nullable ? 'True' : 'False'
    ]
      .map(escapeCsv)
      .join(',')
  )
  return `${header}\n${rows.join('\n')}\n`
}

function downloadCsv(content: string, filename: string): void {
  download(new Blob([content], { type: 'text/csv;charset=utf-8' }), filename, 'text/csv')
}

export function downloadTemplate(database: DatabaseId, columns: DictColumn[]): void {
  downloadCsv(buildTemplateCsv(columns), primaryCsvName(database))
}

export function downloadDictionary(database: DatabaseId, columns: DictColumn[]): void {
  downloadCsv(
    buildDictionaryCsv(columns),
    primaryCsvName(database).replace(/\.csv$/, '_data_dictionary.csv')
  )
}

/**
 * A short curve file with the exact headers of a response type and a few
 * plausible rows: something to open next to one's own export and compare.
 * Values climb to a tenth of the database's typical peak; an index column
 * (no scale) counts from zero.
 */
export function exampleSeriesCsv(kind: TimeSeriesKind, rows = 6): string {
  const header = kind.columns.map((column) => escapeCsv(column.name)).join(',')
  const lines = Array.from({ length: rows }, (_, index) =>
    kind.columns
      .map((column) =>
        column.typicalMax === undefined
          ? String(index)
          : String(Number(((column.typicalMax / 10) * (index / (rows - 1))).toPrecision(4)))
      )
      .join(',')
  )
  return `${header}\n${lines.join('\n')}\n`
}

/** One line of the "expected layout" tree: a path and what goes there. */
export interface LayoutEntry {
  /** Relative to the database folder, e.g. `force_displacement/<id>.csv`. */
  path: string
  kind?: TimeSeriesKind
}

/**
 * The database folder as the repository (and the drop zone) expects it: the
 * primary CSV, then one `<id>.csv` pattern per response type. Paths are
 * relative to the database folder, which is what a contributor sees on disk.
 */
export function layoutEntries(database: DatabaseId, kinds: TimeSeriesKind[]): LayoutEntry[] {
  const csvPath = CONTRIBUTION_DATABASES[database].csvPath
  const root = csvPath.slice(0, csvPath.lastIndexOf('/') + 1)
  const relative = (path: string) => (path.startsWith(root) ? path.slice(root.length) : path)
  return [
    { path: relative(csvPath) },
    ...kinds.map((kind) => ({
      path: `${relative(kind.directory)}/${fileStemFor(kind, '<id>')}.csv`,
      kind
    }))
  ]
}

/** The database folder itself, e.g. `braces/` or `material/tensile_coupons/`. */
export function layoutRoot(database: DatabaseId): string {
  const csvPath = CONTRIBUTION_DATABASES[database].csvPath
  return csvPath.slice(0, csvPath.lastIndexOf('/') + 1)
}

/** Archive name of the example file of a kind: `<directory>/EXAMPLE-ID.csv`. */
export function examplePath(kind: TimeSeriesKind): string {
  return `${kind.directory}/${fileStemFor(kind, EXAMPLE_ID)}.csv`
}

export function downloadExampleSeries(kind: TimeSeriesKind): void {
  downloadCsv(exampleSeriesCsv(kind), `${fileStemFor(kind, EXAMPLE_ID)}.csv`)
}

function readmeText(database: DatabaseId, kinds: TimeSeriesKind[]): string {
  const config = CONTRIBUTION_DATABASES[database]
  const lines = [
    'RESSLab Hub — submission starter kit',
    '',
    `1. Fill in ${config.csvPath}: one row per experiment, one column per`,
    '   dictionary field (headers are already there; keep them as they are).',
    '   Write NR for a value that was not reported, NA where it does not apply.',
    ''
  ]
  if (kinds.length) {
    lines.push(
      '2. Put each measured response in its folder, one CSV per experiment,',
      `   named after the experiment's id (${EXAMPLE_ID}.csv is a sample: rename or`,
      '   replace it, delete it if you have no such file). Exact headers:',
      ''
    )
    for (const kind of kinds) {
      const columns = kind.columns.map((column) => column.name).join(', ')
      lines.push(`   ${kind.directory}/   (${kind.required ? 'required' : 'optional'})`)
      lines.push(`     ${columns}`)
    }
    lines.push('')
  }
  lines.push(
    `${kinds.length ? '3' : '2'}. Drop the whole folder (or a zip of it) on the`,
    '   contribution page: files are matched to experiments by name and checked',
    '   before anything is submitted.',
    '',
    'Numbers only, decimal point, no thousands separators, UTF-8, comma separated.',
    ''
  )
  return lines.join('\n')
}

/** The folder skeleton as a zip: template CSV, one example file per kind, a README. */
export async function buildStarterKit(
  database: DatabaseId,
  columns: DictColumn[],
  kinds: TimeSeriesKind[]
): Promise<Blob> {
  // Lazy: jszip is ~100 kB and only needed when the kit is asked for.
  const { default: JSZip } = await import('jszip')
  const zip = new JSZip()
  zip.file(CONTRIBUTION_DATABASES[database].csvPath, buildTemplateCsv(columns))
  for (const kind of kinds) zip.file(examplePath(kind), exampleSeriesCsv(kind))
  zip.file('README.txt', readmeText(database, kinds))
  return zip.generateAsync({ type: 'blob' })
}

export async function downloadStarterKit(
  database: DatabaseId,
  columns: DictColumn[],
  kinds: TimeSeriesKind[]
): Promise<void> {
  const blob = await buildStarterKit(database, columns, kinds)
  download(
    blob,
    `${primaryCsvName(database).replace(/\.csv$/, '')}-starter-kit.zip`,
    'application/zip'
  )
}
