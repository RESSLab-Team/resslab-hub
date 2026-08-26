/**
 * Client-side mirror of the backend validator's per-cell rules
 * (`_validate_field` in `backend/resslab_hub/data/validator.py`), driven by the
 * data dictionary. It gives the editor instant per-cell feedback; the server
 * stays the authority.
 *
 * Parity contract: for the classes the server treats as ERRORS, this never
 * flags something the server would accept. Where the server is lenient in ways
 * that corrupt data (accepts `1.5` for an integer, truncating it) we downgrade
 * to a WARNING rather than diverge. Two deliberate, stricter parity breaks:
 * `NaN`/`Infinity` are rejected, and a blank required field warns.
 */

import type { DictColumn } from '@/stores/dictionary'

export interface CellIssue {
  level: 'error' | 'warn'
  message: string
}

// Mirror of the backend's SAFE_ID_PATTERN (`data/common.py`): a specimen id
// names its time-series file (`<id>.csv`) and becomes a path in the data
// repository, so it has to be one safe path segment on every platform.
// (`\p{Cc}` covers the C0/DEL control characters the server's byte ranges do.)
const SAFE_ID = /^[\p{L}\p{N}][^<>:"/\\|?*\p{Cc}]*$/u
export const SAFE_ID_RULE =
  'it must start with a letter or digit and cannot contain / \\ < > : " | ? * or control characters'

// A finite decimal literal. Deliberately rejects NaN/Infinity, which Python's
// Decimal() would accept — letting them through would persist garbage numbers.
const DECIMAL = /^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/

function isValidDate(value: string): boolean {
  // Server accepts DD.MM.YY or DD.MM.YYYY; strptime tolerates non-padded parts.
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
  return day <= new Date(year, month, 0).getDate()
}

/** Validate a single cell against its column. Returns null when acceptable. */
export function validateCell(column: DictColumn, raw: string): CellIssue | null {
  const value = raw.trim()

  // A blank cell is serialized as NR ("not reported"), which the server skips.
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
      return /^(yes|no)$/i.test(value) ? null : { level: 'error', message: "Must be 'yes' or 'no'" }

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
      return null
  }
}

export interface HeaderReport {
  /** Dictionary columns absent from the file. */
  missing: string[]
  /** File headers absent from the dictionary. */
  unexpected: string[]
}

export function validateHeaders(columns: DictColumn[], headers: string[]): HeaderReport {
  const known = new Set(columns.map((column) => column.name))
  const present = new Set(headers)
  return {
    missing: columns.map((column) => column.name).filter((name) => !present.has(name)),
    unexpected: headers.filter((header) => !known.has(header))
  }
}

/** Per-cell issues for a whole sheet, keyed by row index then column name. */
export type SheetIssues = Map<number, Record<string, CellIssue>>

/**
 * Validate every cell of every row, plus sheet rules the server cannot see but
 * that would break the upload: a specimen must have an id, and ids must be
 * unique (a time-series file's foreign key is its filename `<id>.csv`).
 */
export function validateSheet(
  columns: DictColumn[],
  rows: Array<Record<string, string>>
): SheetIssues {
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

  const idRows = new Map<string, number[]>()
  rows.forEach((cells, rowIndex) => {
    const id = (cells.id ?? '').trim()
    if (id === '') {
      setIssue(rowIndex, 'id', { level: 'error', message: 'A specimen id is required.' })
      return
    }
    if (!SAFE_ID.test(id)) {
      setIssue(rowIndex, 'id', {
        level: 'error',
        message: `Specimen id "${id}" cannot be used as a file name: ${SAFE_ID_RULE}.`
      })
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
