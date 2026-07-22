/**
 * Downloads a contributor needs to prepare a CSV: a template (header + one
 * example row from the dictionary's example values) and the data dictionary
 * itself. Both are built from the runtime dictionary, so they stay in lockstep
 * with what the editor validates and the backend expects.
 */

import type { DictColumn } from '@/stores/dictionary'
import { CONTRIBUTION_DATABASES, escapeCsv } from '@/utils/contribution'
import type { DatabaseId } from '@/utils/navigation'
import download from 'downloadjs'

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
