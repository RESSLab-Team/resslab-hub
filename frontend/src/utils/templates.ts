/**
 * Client-side generation of the two downloads a contributor needs to prepare a
 * CSV: a blank-ish template (header + one example row) and the data dictionary
 * itself (every column with its description, symbol, unit, type and example).
 *
 * Both are built from the baked dictionary asset, so they stay in lockstep with
 * what the wizard validates and what the backend expects.
 */

import { CONTRIBUTION_DATABASES, escapeCsv } from '@/utils/contribution'
import { dictionaryFor } from '@/utils/dictionary'
import type { DatabaseId } from '@/utils/navigation'
import download from 'downloadjs'

/** `braces/steel_braces.csv` → `steel_braces.csv`. */
function primaryCsvName(database: DatabaseId): string {
  const path = CONTRIBUTION_DATABASES[database].csvPath
  return path.slice(path.lastIndexOf('/') + 1)
}

function dictionaryCsvName(database: DatabaseId): string {
  return primaryCsvName(database).replace(/\.csv$/, '_data_dictionary.csv')
}

/** Header row + one example row built from the dictionary's example values. */
export function buildTemplateCsv(database: DatabaseId): string {
  const columns = dictionaryFor(database)
  const header = columns.map((column) => escapeCsv(column.name)).join(',')
  const example = columns.map((column) => escapeCsv(column.example)).join(',')
  return `${header}\n${example}\n`
}

/** The data dictionary re-serialized to CSV (the same 7 columns as the source). */
export function buildDictionaryCsv(database: DatabaseId): string {
  const header = 'column_name,description,symbol,unit,type,example_value,nullable'
  const rows = dictionaryFor(database).map((column) =>
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

export function downloadTemplate(database: DatabaseId): void {
  downloadCsv(buildTemplateCsv(database), primaryCsvName(database))
}

export function downloadDictionary(database: DatabaseId): void {
  downloadCsv(buildDictionaryCsv(database), dictionaryCsvName(database))
}
