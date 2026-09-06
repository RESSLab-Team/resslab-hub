import type { ExperimentRow } from '@/stores/contribution'
import { mapResponse } from '@/utils/qualityReport'
import type { ValidationResponse } from '@/utils/validationResponse'
import { describe, expect, it } from 'vitest'

function rows(...ids: string[]): ExperimentRow[] {
  return ids.map((id, index) => ({ uid: index, cells: { id } }))
}

describe('mapResponse — primary CSV', () => {
  const response: ValidationResponse = {
    valid: false,
    message: '',
    error_count: 3,
    results: [
      {
        file: 'steel_braces.csv',
        path: 'braces/steel_braces.csv',
        valid: false,
        errors: [
          { row: 1, column: 'area', value: 'x', message: 'Must be a number' },
          { row: 5, column: 'area', value: 'y', message: 'Must be a number' } // out of range
        ],
        warnings: [{ row: 0, column: 'headers', value: null, message: 'Unexpected columns: foo' }]
      }
    ]
  }

  it('maps a data-row error to the right experiment cell', () => {
    const report = mapResponse('braces', rows('B1', 'B2'), response)
    const first = report.experiments.find((e) => e.uid === 0)!
    expect(first.level).toBe('fail')
    expect(first.cellIssues[0].ref).toEqual({ uid: 0, column: 'area' })
  })

  it('sends row-0 and out-of-range issues to the global list', () => {
    const report = mapResponse('braces', rows('B1', 'B2'), response)
    // header warning (row 0) + the row-5 error that has no matching experiment
    expect(report.global.length).toBe(2)
    expect(report.experiments.find((e) => e.uid === 1)!.level).toBe('pass')
  })
})

describe('mapResponse — time-series kind disambiguation', () => {
  it('routes same-basename files to distinct kinds on one experiment', () => {
    const response: ValidationResponse = {
      valid: false,
      message: '',
      error_count: 2,
      results: [
        {
          file: 'S1.csv',
          path: 'residual_stresses/Distributions/Distributions_F1/S1.csv',
          valid: false,
          errors: [{ row: 2, column: 'coordinate', value: '', message: 'Required field is empty' }],
          warnings: []
        },
        {
          file: 'S1.csv',
          path: 'residual_stresses/QP_Coefficients/S1.csv',
          valid: false,
          errors: [{ row: 1, column: 'qp_coefficient', value: 'x', message: 'Must be a number' }],
          warnings: []
        }
      ]
    }
    const report = mapResponse('residuals', rows('S1'), response)
    const experiment = report.experiments[0]
    const kinds = experiment.fileIssues.map((f) => f.kindKey).sort()
    expect(kinds).toEqual(['distribution_f1', 'qp_coefficient'])
    expect(experiment.level).toBe('fail')
  })

  it('sends an unmatched time-series file to the global list', () => {
    const response: ValidationResponse = {
      valid: false,
      message: '',
      error_count: 1,
      results: [
        {
          file: 'GHOST.csv',
          path: 'residual_stresses/QP_Coefficients/GHOST.csv',
          valid: false,
          errors: [{ row: 0, column: 'id', value: 'GHOST', message: 'Foreign key not found' }],
          warnings: []
        }
      ]
    }
    const report = mapResponse('residuals', rows('S1'), response)
    expect(report.global.length).toBe(1)
    expect(report.experiments[0].level).toBe('pass')
  })
})

describe('mapResponse — file naming', () => {
  it('matches an EBF file by its id-prefixed stem', () => {
    const response: ValidationResponse = {
      valid: false,
      message: '',
      error_count: 1,
      results: [
        {
          file: 'id74.csv',
          path: 'eccentric_braced_frames/processed_data/id74.csv',
          valid: false,
          errors: [{ row: 2, column: 'V', value: 'x', message: 'Must be a number' }],
          warnings: []
        }
      ]
    }
    const report = mapResponse('ebf', rows('74'), response)
    expect(report.global).toEqual([])
    expect(report.experiments[0].fileIssues.map((f) => f.kindKey)).toEqual(['processed_data'])
  })
})

describe('mapResponse — the README rules (resslab-hub#243)', () => {
  // The shapes /validate really returns for the rules added with the
  // contributor READMEs. What matters here is where each one lands: a cell
  // the grid can scroll to, or the global list.
  const response: ValidationResponse = {
    valid: false,
    message: '',
    error_count: 2,
    results: [
      {
        file: 'steel_braces.csv',
        path: 'braces/steel_braces.csv',
        valid: false,
        errors: [
          {
            row: 1,
            column: 'date',
            value: '2024.7',
            message: 'Must be a whole number, for example 2024, not 2024.5.'
          },
          {
            row: 2,
            column: 'area',
            value: '1,5',
            message: 'Use a decimal point and no thousands separator: write 1234.5, not 1,5.'
          }
        ],
        warnings: [
          {
            row: 1,
            column: 'investigator',
            value: 'NR',
            message: "This column is mandatory. NR is stored as 'Not reported'."
          },
          {
            row: 0,
            column: 'file',
            value: 'steel_braces.csv',
            message: 'File uses Windows line endings (CRLF). Save it with LF line endings.'
          }
        ]
      },
      {
        file: 'B1.csv',
        path: 'braces/force_displacement/B1.csv',
        valid: true,
        errors: [],
        warnings: [
          {
            row: 12,
            column: 'Force [kN]',
            value: null,
            message: 'Rows 12, 13, 14 and 47 more: NaN means no reading.'
          }
        ]
      }
    ]
  }

  it('puts every cell rule on the cell the grid can open', () => {
    const report = mapResponse('braces', rows('B1', 'B2'), response)
    const first = report.experiments.find((e) => e.uid === 0)!
    const second = report.experiments.find((e) => e.uid === 1)!

    expect(first.cellIssues.map((entry) => entry.ref.column).sort()).toEqual([
      'date',
      'investigator'
    ])
    expect(second.cellIssues.map((entry) => entry.ref.column)).toEqual(['area'])
    expect(first.level).toBe('fail')
  })

  it('keeps a file-level warning out of the cells', () => {
    const report = mapResponse('braces', rows('B1', 'B2'), response)

    expect(report.global.map((entry) => entry.issue.column)).toEqual(['file'])
    expect(report.global[0].severity).toBe('warning')
  })

  it('attaches a grouped time-series warning to its experiment and kind', () => {
    const report = mapResponse('braces', rows('B1', 'B2'), response)
    const first = report.experiments.find((e) => e.uid === 0)!

    expect(first.fileIssues[0].kindKey).toBe('force_displacement')
    // The row number lives in the message: the sparkline shows no column.
    expect(first.fileIssues[0].issue.message).toContain('Rows 12, 13, 14')
  })
})
