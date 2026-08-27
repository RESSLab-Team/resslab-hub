import type { DictColumn } from '@/stores/dictionary'
import { readCsvTable } from '@/utils/csv'
import {
  EXAMPLE_ID,
  buildDictionaryCsv,
  buildStarterKit,
  buildTemplateCsv,
  examplePath,
  exampleSeriesCsv,
  layoutEntries,
  layoutRoot
} from '@/utils/templates'
import { checkTimeSeriesFile, timeSeriesKindsFor } from '@/utils/timeseries'
import JSZip from 'jszip'
import { describe, expect, it } from 'vitest'

const COLUMNS: DictColumn[] = [
  {
    name: 'id',
    description: 'Identifier',
    symbol: '',
    unit: '-',
    type: 'String',
    example: 'B1',
    nullable: false
  },
  {
    name: 'area',
    description: 'Cross-section, "gross"',
    symbol: 'A',
    unit: 'mm2',
    type: 'Numeric',
    example: '120.5',
    nullable: true
  }
]

describe('templates', () => {
  it('template CSV round-trips with no missing or unknown columns', () => {
    const table = readCsvTable(
      buildTemplateCsv(COLUMNS),
      COLUMNS.map((column) => column.name)
    )
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

  it('writes an example file per kind that passes the file check', () => {
    for (const database of ['columns', 'ebf', 'residuals'] as const) {
      for (const kind of timeSeriesKindsFor(database)) {
        const report = checkTimeSeriesFile(kind, exampleSeriesCsv(kind))
        expect(report.errors, kind.key).toEqual([])
        expect(report.warnings, kind.key).toEqual([])
        expect(report.rows).toBe(6)
      }
    }
    expect(examplePath(timeSeriesKindsFor('ebf')[0])).toBe(
      `eccentric_braced_frames/processed_data/id${EXAMPLE_ID}.csv`
    )
  })

  it('lays the starter kit out like the repository', async () => {
    const kinds = timeSeriesKindsFor('columns')
    const zip = await JSZip.loadAsync(await buildStarterKit('columns', COLUMNS, kinds))
    const paths = Object.keys(zip.files)
      .filter((path) => !zip.files[path].dir)
      .sort()
    expect(paths).toEqual([
      'README.txt',
      `columns/axial_shortening_rotation/${EXAMPLE_ID}.csv`,
      `columns/moment_rotation_strong/${EXAMPLE_ID}.csv`,
      `columns/moment_rotation_weak/${EXAMPLE_ID}.csv`,
      'columns/steel_columns.csv'
    ])
    expect(await zip.file('columns/steel_columns.csv')!.async('string')).toBe(
      buildTemplateCsv(COLUMNS)
    )
    expect(await zip.file('README.txt')!.async('string')).toContain('moment_rotation_strong/')
  })

  it('describes the expected layout relative to the database folder', () => {
    expect(layoutRoot('tensile')).toBe('material/tensile_coupons/')
    expect(layoutEntries('tensile', timeSeriesKindsFor('tensile')).map((e) => e.path)).toEqual([
      'tensile_coupons.csv',
      'stress_strain/<id>.csv'
    ])
    expect(layoutEntries('ebf', timeSeriesKindsFor('ebf'))[1].path).toBe(
      'processed_data/id<id>.csv'
    )
  })
})
