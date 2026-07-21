/**
 * Minimal RFC 4180 reader for the contribution importer.
 *
 * The app already parses CSV in two places, but neither fits: the `assets/`
 * section tables are compiled by a Vite plugin at build time, and the dataset
 * loaders receive JSON from the API. This reads a user-supplied file at runtime,
 * so it has to handle quoted fields, embedded commas/newlines and escaped
 * quotes itself.
 */

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

export interface CsvRecord {
  /** Header-to-value map for the first data row. */
  values: Record<string, string>
  /** Headers that matched a column of the target database. */
  matched: string[]
  /** Headers absent from the target database. */
  unknown: string[]
  /** Columns of the target database absent from the file. */
  missing: string[]
  /** Data rows found; only the first is imported. */
  rowCount: number
}

/**
 * Read the first data row of a CSV and align it to a database's columns.
 *
 * Values of `NA`/`NR` are dropped rather than imported: they are the archive's
 * way of writing "no value", and carrying them into the form would show them as
 * if the contributor had typed them.
 */
export function readCsvRecord(text: string, columns: string[]): CsvRecord {
  const rows = parseCsv(text)
  if (rows.length === 0) {
    throw new Error('The file is empty.')
  }

  const headers = rows[0].map((header) => header.trim())
  const dataRows = rows.slice(1)
  if (dataRows.length === 0) {
    throw new Error('The file has a header but no data rows.')
  }

  const known = new Set(columns)
  const values: Record<string, string> = {}

  headers.forEach((header, index) => {
    if (!known.has(header)) return
    const raw = (dataRows[0][index] ?? '').trim()
    if (raw === '' || raw.toUpperCase() === 'NA' || raw.toUpperCase() === 'NR') return
    values[header] = raw
  })

  const headerSet = new Set(headers)
  return {
    values,
    matched: headers.filter((header) => known.has(header)),
    unknown: headers.filter((header) => !known.has(header)),
    missing: columns.filter((column) => !headerSet.has(column)),
    rowCount: dataRows.length
  }
}
