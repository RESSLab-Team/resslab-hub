import type { DictColumn } from '@/stores/dictionary'
import { readCsvTable } from '@/utils/csv'
import { buildDictionaryCsv, buildTemplateCsv } from '@/utils/templates'
import { describe, expect, it } from 'vitest'

const COLUMNS: DictColumn[] = [
  { name: 'id', description: 'Identifier', symbol: '', unit: '-', type: 'String', example: 'B1', nullable: false },
  { name: 'area', description: 'Cross-section, "gross"', symbol: 'A', unit: 'mm2', type: 'Numeric', example: '120.5', nullable: true }
]

describe('templates', () => {
  it('template CSV round-trips with no missing or unknown columns', () => {
    const table = readCsvTable(buildTemplateCsv(COLUMNS), COLUMNS.map((column) => column.name))
    expect(table.missing).toEqual([])
    expect(table.unknown).toEqual([])
    expect(table.rows).toEqual([{ id: 'B1', area: '120.5' }])
  })

  it('dictionary CSV has a header plus one quoted row per column', () => {
    const csv = buildDictionaryCsv(COLUMNS)
    const lines = csv.trimEnd().split('\n')
    expect(lines[0]).toBe('column_name,description,symbol,unit,type,example_value,nullable')
    expect(lines.length - 1).toBe(COLUMNS.length)
    expect(lines[2]).toContain('"Cross-section, ""gross"""') // RFC-4180 quoting
  })
})
