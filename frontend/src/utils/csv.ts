/**
 * Minimal RFC 4180 reader for the contribution importer.
 *
 * The app already parses CSV in two places, but neither fits: the `assets/`
 * section tables are compiled by a Vite plugin at build time, and the dataset
 * loaders receive JSON from the API. This reads a user-supplied file at runtime,
 * so it has to handle quoted fields, embedded commas/newlines and escaped
 * quotes itself.
 */

/**
 * Make a contributor's CSV acceptable to the data repository without touching
 * its data: drop a UTF-8 BOM, use LF line endings, end with exactly one
 * newline. Spreadsheet exports routinely violate all three and the data
 * repository's CI rejects them; the server applies the same rule on submit.
 */
export function normalizeCsvText(text: string): string {
  const body = text
    .replace(/^\uFEFF/, '')
    .replace(/\r\n?/g, '\n')
    .replace(/\n+$/, '')
  return body ? body + '\n' : ''
}

/** Split CSV text into rows of raw cell strings. */
export function parseCsv(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false

  // Strip a UTF-8 BOM; Excel writes one and it would corrupt the first header.
  const input = text.replace(/^\uFEFF/, '')

  for (let i = 0; i < input.length; i++) {
    const char = input[i]

    if (quoted) {
      if (char === '"') {
        if (input[i + 1] === '"') {
          cell += '"'
          i++
        } else {
          quoted = false
        }
      } else {
        cell += char
      }
      continue
    }

    if (char === '"') {
      quoted = true
    } else if (char === ',') {
      row.push(cell)
      cell = ''
    } else if (char === '\n' || char === '\r') {
      // Treat CRLF as one break.
      if (char === '\r' && input[i + 1] === '\n') i++
      row.push(cell)
      rows.push(row)
      row = []
      cell = ''
    } else {
      cell += char
    }
  }

  // A final line without a trailing newline still holds a row.
  if (cell !== '' || row.length > 0) {
    row.push(cell)
    rows.push(row)
  }

  return rows.filter((entry) => entry.some((value) => value.trim() !== ''))
}

export interface CsvTable {
  /** One header-to-value map per data row, aligned to the target columns. */
  rows: Array<Record<string, string>>
  /** Headers that matched a column of the target database. */
  matched: string[]
  /** Headers absent from the target database. */
  unknown: string[]
  /** Columns of the target database absent from the file. */
  missing: string[]
}

/**
 * Read every data row of a CSV and align each to a database's columns.
 *
 * Keeps all rows (one experiment per row).
 * `NR` collapses to an empty cell — it round-trips back to `NR` on submit, and
 * an empty grid cell reads more clearly than a literal "NR". `NA` is kept
 * verbatim: it is meaningful data ("not applicable" on a nullable column), not
 * an absence.
 */
export function readCsvTable(text: string, columns: string[]): CsvTable {
  const parsed = parseCsv(text)
  if (parsed.length === 0) {
    throw new Error('The file is empty.')
  }

  const headers = parsed[0].map((header) => header.trim())
  const dataRows = parsed.slice(1)
  if (dataRows.length === 0) {
    throw new Error('The file has a header but no data rows.')
  }

  const known = new Set(columns)
  const rows = dataRows.map((cells) => {
    const values: Record<string, string> = {}
    headers.forEach((header, index) => {
      if (!known.has(header)) return
      const raw = (cells[index] ?? '').trim()
      values[header] = raw.toUpperCase() === 'NR' ? '' : raw
    })
    return values
  })

  const headerSet = new Set(headers)
  return {
    rows,
    matched: headers.filter((header) => known.has(header)),
    unknown: headers.filter((header) => !known.has(header)),
    missing: columns.filter((column) => !headerSet.has(column))
  }
}
