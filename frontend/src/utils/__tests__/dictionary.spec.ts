import {
  BraceField,
  ColumnField,
  ConnectionField,
  DuctileFractureField,
  EccentricBracedFrameField,
  HSSColumnField,
  MaterialField,
  ResidualStressField,
  TensileCouponField
} from '@/backend'
import { dictionaryFor } from '@/utils/dictionary'
import type { DatabaseId } from '@/utils/navigation'
import { describe, expect, it } from 'vitest'
import { buildDictionaryCsv, buildTemplateCsv } from '@/utils/templates'
import { readCsvRecord } from '@/utils/csv'

/**
 * The generated `*Field` constants expose the API-visible columns. Everything
 * they list (minus relationship `_count`s and `column_property` derived values,
 * which are not real table columns) must also live in the dictionary — else the
 * dictionary and the OpenAPI schema have drifted and a submission would fail
 * validation with "Missing required columns".
 */
const FIELDS: Record<DatabaseId, Record<string, string>> = {
  connections: ConnectionField,
  columns: ColumnField,
  braces: BraceField,
  hss: HSSColumnField,
  cyclic: MaterialField,
  residuals: ResidualStressField,
  ebf: EccentricBracedFrameField,
  tensile: TensileCouponField,
  'ductile-fracture': DuctileFractureField
}

// Derived (column_property) columns the API exposes but that are absent from the
// data dictionary / table columns.
const DERIVED: Partial<Record<DatabaseId, string[]>> = {
  columns: ['built_up'],
  residuals: ['h_over_b'],
  cyclic: ['type', 'year']
}

describe('data dictionary vs generated API fields', () => {
  for (const database of Object.keys(FIELDS) as DatabaseId[]) {
    it(`${database}: dictionary covers every real API column`, () => {
      const dictionaryNames = new Set(dictionaryFor(database).map((column) => column.name))
      const derived = DERIVED[database] ?? []
      const apiColumns = [...new Set(Object.values(FIELDS[database]))].filter(
        (column) => !column.endsWith('_count') && !derived.includes(column)
      )
      const missing = apiColumns.filter((column) => !dictionaryNames.has(column))
      expect(missing, `dictionary is missing: ${missing.join(', ')}`).toEqual([])
    })
  }
})

describe('templates', () => {
  it('template CSV round-trips with no missing or unknown columns', () => {
    const columns = dictionaryFor('braces').map((column) => column.name)
    const record = readCsvRecord(buildTemplateCsv('braces'), columns)
    expect(record.missing).toEqual([])
    expect(record.unknown).toEqual([])
    expect(record.rowCount).toBe(1)
  })

  it('dictionary CSV has a header plus one row per column', () => {
    const csv = buildDictionaryCsv('braces')
    const lines = csv.trimEnd().split('\n')
    expect(lines[0]).toContain('column_name')
    expect(lines.length - 1).toBe(dictionaryFor('braces').length)
  })
})
