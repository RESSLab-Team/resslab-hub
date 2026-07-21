/**
 * Client-side mirror of the backend validator's per-cell rules
 * (`_validate_field` in `backend/resslab_hub/data/validator.py`), driven by the
 * data dictionary. It gives the grid instant per-cell feedback so contributors
 * rarely need a server round-trip; the server stays the authority.
 *
 * Parity contract: for the classes the server treats as ERRORS, this never
 * flags something the server would accept. Where the server is lenient in ways
 * that corrupt data (accepts `1.5` for an integer, truncating it) we downgrade
 * to a WARNING rather than diverge. Two deliberate parity breaks, both stricter
 * and therefore safe, are documented inline: we reject `NaN`/`Infinity` numbers,
 * and we warn on a blank required field.
 */

import { CONTRIBUTION_DATABASES } from '@/utils/contribution'
import { dictionaryFor, type DictColumn } from '@/utils/dictionary'
import type { DatabaseId } from '@/utils/navigation'

export interface CellIssue {
  level: 'error' | 'warn'
  message: string
}

// A finite decimal literal. Deliberately rejects NaN/Infinity, which Python's
// Decimal() would accept — letting them through would persist garbage numbers.
const DECIMAL = /^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/

function isValidDate(value: string): boolean {
  // Server accepts DD.MM.YY or DD.MM.YYYY (strptime %d.%m.%y then %d.%m.%Y),
  // and strptime tolerates non-padded day/month.
  const match = /^(\d{1,2})\.(\d{1,2})\.(\d{2}|\d{4})$/.exec(value)
  if (!match) return false
  const day = Number(match[1])
  const month = Number(match[2])
  let year = Number(match[3])
  if (match[3].length === 2) {
    // Match Python %y: 00–68 → 2000–2068, 69–99 → 1969–1999.
    year = year <= 68 ? 2000 + year : 1900 + year
  }
  if (month < 1 || month > 12 || day < 1) return false
  const daysInMonth = new Date(year, month, 0).getDate()
  return day <= daysInMonth
}

/** Validate a single cell against its column. Returns null when acceptable. */
export function validateCell(column: DictColumn, raw: string): CellIssue | null {
  const value = raw.trim()

  // A blank cell is serialized as NR ("not reported"), which the server skips.
  // It is never an error, but a blank on a required column is worth flagging.
  if (value === '') {
    return column.nullable
      ? null
      : { level: 'warn', message: 'Recommended field is blank — it will be submitted as NR.' }
  }

  const upper = value.toUpperCase()
  if (upper === 'NR') return null
  if (upper === 'NA') {
    return column.nullable
      ? null
      : { level: 'error', message: 'Field cannot be null: column is not nullable' }
  }

  switch (column.type) {
    case 'Boolean':
      return /^(yes|no)$/i.test(value)
        ? null
        : { level: 'error', message: "Must be 'yes' or 'no'" }

    case 'SmallInteger':
    case 'Integer':
    case 'BigInteger':
      if (!DECIMAL.test(value)) {
        return { level: 'error', message: 'Must be an integer' }
      }
      // Server does int(Decimal(value)), which silently truncates a fraction.
      return Number.isInteger(Number(value))
        ? null
        : { level: 'warn', message: 'Will be truncated to a whole number.' }

    case 'DecimalFloat':
      return DECIMAL.test(value)
        ? null
        : { level: 'error', message: 'Must be a number: Float as decimal' }

    case 'Numeric':
      return DECIMAL.test(value)
        ? null
        : { level: 'error', message: 'Must be a number: Numeric float' }

    case 'Date':
      return isValidDate(value)
        ? null
        : {
            level: 'error',
            message: 'Invalid date format: Expected format: DD.MM.YY or DD.MM.YYYY'
          }

    default:
      // String columns: anything is a valid string.
      return null
  }
}

export interface HeaderReport {
  /** Dictionary columns absent from the file. */
  missing: string[]
  /** File headers absent from the dictionary. */
  unexpected: string[]
}

export function validateHeaders(database: DatabaseId, headers: string[]): HeaderReport {
  const known = new Set(CONTRIBUTION_DATABASES[database].columns)
  const present = new Set(headers)
  return {
    missing: CONTRIBUTION_DATABASES[database].columns.filter((column) => !present.has(column)),
    unexpected: headers.filter((header) => !known.has(header))
  }
}

/** Per-cell issues for a whole sheet, keyed by row index then column name. */
export type SheetIssues = Map<number, Record<string, CellIssue>>

/**
 * Validate every cell of every row, plus sheet-level rules the server cannot
 * see but that would break the upload: a specimen must have an id, and ids must
 * be unique (a time-series file's foreign key is its filename `<id>.csv`, so
 * duplicate ids are ambiguous).
 */
export function validateSheet(
  database: DatabaseId,
  rows: Array<Record<string, string>>
): SheetIssues {
  const columns = dictionaryFor(database)
  const issues: SheetIssues = new Map()

  const setIssue = (rowIndex: number, column: string, issue: CellIssue) => {
    const row = issues.get(rowIndex) ?? {}
    row[column] = issue
    issues.set(rowIndex, row)
  }

  rows.forEach((cells, rowIndex) => {
    for (const column of columns) {
      const issue = validateCell(column, cells[column.name] ?? '')
      if (issue) setIssue(rowIndex, column.name, issue)
    }
  })

  // Sheet rule: id is required and must be unique.
  const idRows = new Map<string, number[]>()
  rows.forEach((cells, rowIndex) => {
    const id = (cells.id ?? '').trim()
    if (id === '') {
      setIssue(rowIndex, 'id', { level: 'error', message: 'A specimen id is required.' })
      return
    }
    idRows.set(id, [...(idRows.get(id) ?? []), rowIndex])
  })
  for (const [id, indices] of idRows) {
    if (indices.length > 1) {
      for (const rowIndex of indices) {
        setIssue(rowIndex, 'id', {
          level: 'error',
          message: `Duplicate specimen id "${id}" — ids must be unique.`
        })
      }
    }
  }

  return issues
}
