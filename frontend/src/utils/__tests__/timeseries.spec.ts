import { BUILT_UP_QP_COLUMNS } from '@/utils/residualBuiltUp'
import { sparkline } from '@/utils/sparkline'
import {
  TIME_SERIES_KINDS,
  checkTimeSeriesFile,
  fileStemFor,
  kindsMatchingHeaders,
  requiredColumns,
  timeSeriesKindsFor
} from '@/utils/timeseries'
import { describe, expect, it } from 'vitest'

const BRACE = timeSeriesKindsFor('braces')[0]

describe('time-series kinds', () => {
  it('declares columns for every kind', () => {
    for (const [database, kinds] of Object.entries(TIME_SERIES_KINDS)) {
      expect(kinds.length, database).toBeGreaterThan(0)
      for (const kind of kinds) {
        expect(kind.columns.length, `${database}/${kind.key}`).toBeGreaterThan(0)
        expect(requiredColumns(kind)).toEqual(kind.columns.map((column) => column.name))
      }
    }
  })

  it('names files after the specimen id, EBF with its id prefix', () => {
    expect(fileStemFor(BRACE, 'B1')).toBe('B1')
    expect(fileStemFor(timeSeriesKindsFor('ebf')[0], '74')).toBe('id74')
  })

  it('tells a kind from the headers, and reports shared header sets as several', () => {
    const connections = timeSeriesKindsFor('connections')
    expect(
      kindsMatchingHeaders(
        connections,
        'panel zone shear distortion (rad),panel zone shear force (kN)\n0,0\n'
      ).map((kind) => kind.key)
    ).toEqual(['panel_zone'])
    expect(
      kindsMatchingHeaders(connections, 'Chord Rotation [rads],Moment [kN-mm]\n0,0\n').map(
        (kind) => kind.key
      )
    ).toEqual(['beam', 'beam_west'])
    expect(kindsMatchingHeaders(connections, 'a,b\n1,2\n')).toEqual([])
  })
})

describe('checkTimeSeriesFile', () => {
  it('reads a clean file: rows, stats, and the two series for the preview', () => {
    const report = checkTimeSeriesFile(
      BRACE,
      'Displacement [mm],Force [kN],extra\n0,0,x\n-10,-200,y\n20,350,z\n'
    )
    expect(report.errors).toEqual([])
    expect(report.warnings).toEqual([])
    expect(report.rows).toBe(3)
    expect(report.stats).toEqual({
      'Displacement [mm]': { min: -10, max: 20 },
      'Force [kN]': { min: -200, max: 350 }
    })
    expect(report.x).toEqual([0, -10, 20])
    expect(report.y).toEqual([0, -200, 350])
  })

  it('ignores a BOM and header padding', () => {
    const report = checkTimeSeriesFile(BRACE, '﻿ Displacement [mm] , Force [kN]\n1,2\n')
    expect(report.errors).toEqual([])
  })

  it('reports an empty file', () => {
    expect(checkTimeSeriesFile(BRACE, 'Displacement [mm],Force [kN]\n').errors).toEqual([
      'The file has no data rows.'
    ])
    expect(checkTimeSeriesFile(BRACE, '').rows).toBe(0)
  })

  it('reports missing columns and still reads the ones present', () => {
    const report = checkTimeSeriesFile(BRACE, 'Displacement [mm],Load\n0,0\n5,1\n')
    expect(report.errors).toEqual(['Missing required column(s): Force [kN]'])
    expect(report.stats['Displacement [mm]']).toEqual({ min: 0, max: 5 })
    expect(report.y).toEqual([])
  })

  it('reports the first non-numeric or empty cell of a column with its line', () => {
    const report = checkTimeSeriesFile(
      BRACE,
      'Displacement [mm],Force [kN]\n0,0\n1,abc\n2,def\n,3\n'
    )
    expect(report.errors).toEqual([
      'Column "Displacement [mm]" has an empty cell (line 5).',
      'Column "Force [kN]" has a value that is not a number (line 3: "abc").'
    ])
    // The good points still feed the preview.
    expect(report.x).toEqual([0])
  })

  it('warns when values sit far above or below the database scale', () => {
    const columns = timeSeriesKindsFor('columns').find((kind) => kind.key === 'moment_strong')!
    // Rotation given in mrad.
    const high = checkTimeSeriesFile(columns, 'Chord Rotation [rads],Moment [kN-mm]\n0,0\n40,1e5\n')
    expect(high.warnings).toHaveLength(1)
    expect(high.warnings[0]).toContain('"Chord Rotation [rads]" reach 40')
    expect(high.warnings[0]).toContain('~0.2 rad')
    // Moment given in MN·m-ish tiny numbers.
    const low = checkTimeSeriesFile(
      columns,
      'Chord Rotation [rads],Moment [kN-mm]\n0,0\n0.02,0.005\n'
    )
    expect(low.warnings).toHaveLength(1)
    expect(low.warnings[0]).toContain('"Moment [kN-mm]" peak at 0.005')
    // An all-zero column has no scale to judge.
    const zero = checkTimeSeriesFile(columns, 'Chord Rotation [rads],Moment [kN-mm]\n0,0\n0,0\n')
    expect(zero.warnings).toEqual([])
  })

  it('never judges an index column', () => {
    const ebf = timeSeriesKindsFor('ebf')[0]
    const report = checkTimeSeriesFile(ebf, 'data_ind,gamma_t,V\n1,0,0\n500000,0.05,120\n')
    expect(report.errors).toEqual([])
    expect(report.warnings).toEqual([])
  })

  it('previews a single-column kind against the row index', () => {
    const qp = timeSeriesKindsFor('residuals').find((kind) => kind.key === 'qp_coefficient')!
    const report = checkTimeSeriesFile(qp, 'qp_coefficient\n10\n-20\n30\n')
    expect(report.x).toEqual([0, 1, 2])
    expect(report.y).toEqual([10, -20, 30])
  })
})

describe('the built-up QP format (#228)', () => {
  const qp = timeSeriesKindsFor('residuals').find((kind) => kind.key === 'qp_coefficient')!
  const names = [...BUILT_UP_QP_COLUMNS]
  const row = (cells: Record<string, string> = {}) =>
    names.map((name) => cells[name] ?? (name.startsWith('d') ? '20' : '-50')).join(',')

  it('accepts one row of the 18 named values', () => {
    const report = checkTimeSeriesFile(qp, `${names.join(',')}\n${row()}\n`)
    expect(report.errors).toEqual([])
    expect(requiredColumns(qp, names)).toEqual(names)
  })

  it('accepts NA for a flame-cut tip stress only', () => {
    const tip = checkTimeSeriesFile(
      qp,
      `${names.join(',')}\n${row({ sigma_ffe_top: 'NA', sigma_ffe_bot: 'NA' })}\n`
    )
    expect(tip.errors).toEqual([])
    const web = checkTimeSeriesFile(qp, `${names.join(',')}\n${row({ sigma_wc: 'NA' })}\n`)
    expect(web.errors.some((error) => error.includes('sigma_wc'))).toBe(true)
  })

  it('reads either header set as a QP file', () => {
    const kinds = timeSeriesKindsFor('residuals')
    expect(kindsMatchingHeaders(kinds, names.join(',')).map((kind) => kind.key)).toEqual([
      'qp_coefficient'
    ])
    expect(kindsMatchingHeaders(kinds, 'qp_coefficient').map((kind) => kind.key)).toEqual([
      'qp_coefficient'
    ])
  })

  it('names the usual column when neither set is complete', () => {
    const report = checkTimeSeriesFile(qp, 'dfc_top\n1\n')
    expect(report.errors[0]).toContain('qp_coefficient')
  })

  it('requires no residual stress distribution', () => {
    expect(timeSeriesKindsFor('residuals').filter((kind) => kind.required)).toEqual([])
  })
})

describe('sparkline', () => {
  it('needs two points and scales them into the viewport', () => {
    expect(sparkline([0], [0])).toBeNull()
    const line = sparkline([0, 10], [0, 5], 100, 20, 0)
    expect(line).toEqual({ points: '0.0,20.0 100.0,0.0', width: 100, height: 20 })
  })
})
