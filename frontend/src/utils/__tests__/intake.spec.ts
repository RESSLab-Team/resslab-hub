import {
  classifyIntake,
  collectFromFileList,
  isNoise,
  matchId,
  type IntakeFile
} from '@/utils/intake'
import { timeSeriesKindsFor } from '@/utils/timeseries'
import { describe, expect, it } from 'vitest'

const COLUMNS = ['id', 'investigator', 'area', 'grade']
const PRIMARY = 'id,investigator,area,grade\nB1,X,10,S355\nB2,Y,12,S355\n'

function file(path: string, text: string): IntakeFile {
  return {
    path,
    name: path.slice(path.lastIndexOf('/') + 1),
    size: text.length,
    text: async () => text
  }
}

const options = (database: 'braces' | 'columns' | 'connections' | 'residuals' | 'ebf') => ({
  columns: COLUMNS,
  primaryName: 'steel_braces.csv',
  kinds: timeSeriesKindsFor(database),
  ids: [] as string[]
})

describe('intake: noise and paths', () => {
  it('skips hidden, editor and OS leftovers wherever they sit', () => {
    expect(isNoise('.DS_Store')).toBe(true)
    expect(isNoise('braces/__MACOSX/x.csv')).toBe(true)
    expect(isNoise('braces/~$steel_braces.xlsx')).toBe(true)
    expect(isNoise('Thumbs.db')).toBe(true)
    expect(isNoise('braces/force_displacement/B1.csv')).toBe(false)
  })

  it('keeps the relative path of files picked from a folder', () => {
    const picked = new File(['x'], 'B1.csv')
    Object.defineProperty(picked, 'webkitRelativePath', {
      value: 'braces/force_displacement/B1.csv'
    })
    const loose = new File(['x'], 'B2.csv')
    expect(collectFromFileList([picked, loose]).map((entry) => entry.path)).toEqual([
      'braces/force_displacement/B1.csv',
      'B2.csv'
    ])
  })
})

describe('intake: classifying a drop', () => {
  it('places a whole folder: primary by headers, files by folder and stem', async () => {
    const plan = await classifyIntake(
      [
        file('braces/steel_braces.csv', PRIMARY),
        file('braces/force_displacement/B1.csv', 'Displacement [mm],Force [kN]\n0,0\n1,2\n'),
        file('braces/force_displacement/b2.csv', 'Displacement [mm],Force [kN]\n0,0\n'),
        file('braces/.DS_Store', ''),
        file('braces/notes.xlsx', '')
      ],
      options('braces')
    )
    expect(plan.primary?.file.name).toBe('steel_braces.csv')
    expect(plan.primary?.table.rows).toHaveLength(2)
    expect(plan.matched.map((match) => [match.id, match.kind.key])).toEqual([
      ['B1', 'force_displacement'],
      ['B2', 'force_displacement'] // case-insensitive stem
    ])
    expect(plan.pending).toEqual([])
    expect(plan.skipped.map((entry) => entry.name)).toEqual(['notes.xlsx'])
    expect(plan.noise).toBe(1)
  })

  it('reads the response type from the folder when headers are shared', async () => {
    const text = 'coordinate,residual_stress\n0,10\n'
    const plan = await classifyIntake(
      [
        file('residual_stresses/Distributions/Distributions_F1/R1.csv', text),
        file('residual_stresses/Distributions/distributions_f2/R1.csv', text),
        file('R1.csv', text)
      ],
      { ...options('residuals'), ids: ['R1'] }
    )
    expect(plan.matched.map((match) => match.kind.key)).toEqual([
      'distribution_f1',
      'distribution_f2'
    ])
    expect(plan.pending).toHaveLength(1)
    expect(plan.pending[0].reason).toBe('ambiguous')
    expect(plan.pending[0].kinds.map((kind) => kind.key)).toEqual([
      'distribution_f1',
      'distribution_f2',
      'distribution_w1'
    ])
  })

  it('accepts the kind key and its label as folder names', async () => {
    const text = 'Chord Rotation [rads],Moment [kN-mm]\n0,0\n'
    const plan = await classifyIntake(
      [file('moment_strong/C1.csv', text), file('Moment – rotation, weak axis/C1.csv', text)],
      {
        ...options('columns'),
        ids: ['C1'],
        aliases: (kind) => (kind.key === 'moment_weak' ? ['Moment – rotation, weak axis'] : [])
      }
    )
    expect(plan.matched.map((match) => match.kind.key)).toEqual(['moment_strong', 'moment_weak'])
  })

  // #282: a folder drop that lost its folder names (files picked one by one, or
  // a folder dragged out of a zip on Windows) left both moment files pending
  // and every card said the strong axis was missing.
  const MOMENT = 'Chord Rotation [rads],Moment [kN-mm]\n0,0\n'
  const AXIAL = 'Chord Rotation [rads],Axial Shortening [mm]\n0,0\n'

  it('places the columns sample with no folder names: moment files go to the strong axis', async () => {
    const primary = 'id,investigator,area,grade\nC1,X,10,S355\nC2,Y,12,S355\n'
    const plan = await classifyIntake(
      [
        file('steel_columns.csv', primary),
        file('C1.csv', AXIAL),
        file('C2.csv', AXIAL),
        file('C1.csv', MOMENT),
        file('C2.csv', MOMENT)
      ],
      { ...options('columns'), primaryName: 'steel_columns.csv' }
    )
    expect(plan.pending).toEqual([])
    expect(plan.matched.map((match) => [match.id, match.kind.key, !!match.assumed])).toEqual([
      ['C1', 'axial_shortening', false],
      ['C2', 'axial_shortening', false],
      ['C1', 'moment_strong', true],
      ['C2', 'moment_strong', true]
    ])
  })

  // #437: the same drop with both moment files per specimen. Strong and weak
  // share the name and the headers, so nothing tells them apart: no guess,
  // and every one is flagged for the "extract the zip first" message.
  it('does not guess a flat drop of the columns sample, and flags the lost folders', async () => {
    const primary = 'id,investigator,area,grade\nC1,X,10,S355\nC2,Y,12,S355\n'
    const plan = await classifyIntake(
      [
        file('steel_columns.csv', primary),
        file('steel_columns.invalid.csv', primary),
        file('C1.csv', AXIAL),
        file('C2.csv', AXIAL),
        file('C1.csv', MOMENT),
        file('C2.csv', MOMENT),
        file('C1.csv', MOMENT),
        file('C2.csv', MOMENT)
      ],
      { ...options('columns'), primaryName: 'steel_columns.csv' }
    )
    expect(plan.primary?.file.name).toBe('steel_columns.csv')
    expect(plan.matched.map((match) => [match.id, match.kind.key])).toEqual([
      ['C1', 'axial_shortening'],
      ['C2', 'axial_shortening']
    ])
    expect(plan.pending.map((entry) => [entry.file.name, entry.reason, entry.lostFolder])).toEqual([
      ['C1.csv', 'ambiguous', true],
      ['C2.csv', 'ambiguous', true],
      ['C1.csv', 'ambiguous', true],
      ['C2.csv', 'ambiguous', true]
    ])
  })

  it('does not guess when two files compete for the same experiment', async () => {
    const plan = await classifyIntake([file('a/C1.csv', MOMENT), file('b/c1.csv', MOMENT)], {
      ...options('columns'),
      ids: ['C1']
    })
    expect(plan.matched).toEqual([])
    expect(plan.pending.map((entry) => entry.reason)).toEqual(['ambiguous', 'ambiguous'])
  })

  it('does not guess when no candidate type is required', async () => {
    const plan = await classifyIntake([file('C1.csv', MOMENT)], {
      ...options('connections'),
      ids: ['C1']
    })
    expect(
      plan.pending.map((entry) => [entry.reason, entry.kinds.map((kind) => kind.key)])
    ).toEqual([['ambiguous', ['beam', 'beam_west']]])
    expect(plan.pending[0].lostFolder).toBeUndefined()
  })

  it('keeps every candidate type on a guessed file that matches no experiment', async () => {
    const plan = await classifyIntake([file('C9.csv', MOMENT)], {
      ...options('columns'),
      ids: ['C1']
    })
    expect(
      plan.pending.map((entry) => [entry.reason, entry.kinds.map((kind) => kind.key)])
    ).toEqual([['orphan', ['moment_strong', 'moment_weak']]])
  })

  it('falls back to the headers for loose files, and reports what it cannot place', async () => {
    const plan = await classifyIntake(
      [
        file('C1.csv', 'Chord Rotation [rads],Axial Shortening [mm]\n0,0\n'),
        file('C9.csv', 'Chord Rotation [rads],Axial Shortening [mm]\n0,0\n'),
        file('C1_strain.csv', 'time,strain\n0,0\n'),
        file('other.csv', 'id,foo,bar\n1,2,3\n')
      ],
      { ...options('columns'), ids: ['C1'] }
    )
    expect(plan.matched.map((match) => [match.id, match.kind.key])).toEqual([
      ['C1', 'axial_shortening']
    ])
    expect(plan.pending.map((entry) => [entry.file.name, entry.reason])).toEqual([
      ['other.csv', 'foreign'],
      ['C9.csv', 'orphan'],
      ['C1_strain.csv', 'unknown']
    ])
    const orphan = plan.pending.find((entry) => entry.reason === 'orphan')!
    expect(orphan.kinds.map((kind) => kind.key)).toEqual(['axial_shortening'])
    const unknown = plan.pending.find((entry) => entry.reason === 'unknown')!
    expect(unknown.kinds).toHaveLength(3)
  })

  it('follows the EBF naming rule for stems', async () => {
    const kind = timeSeriesKindsFor('ebf')[0]
    expect(matchId(kind, 'id74', ['74', '7'])).toBe('74')
    expect(matchId(kind, 'ID74', ['74'])).toBe('74')
    expect(matchId(kind, '74', ['74'])).toBeUndefined()
  })

  it('prefers the repository name between two primary candidates, else asks', async () => {
    const both = [
      file('braces/steel_braces.csv', PRIMARY),
      file('braces/steel_braces.invalid.csv', PRIMARY)
    ]
    const plan = await classifyIntake(both, options('braces'))
    expect(plan.primary?.file.name).toBe('steel_braces.csv')
    expect(plan.primaryCandidates.map((entry) => entry.name)).toEqual(['steel_braces.invalid.csv'])

    const neither = await classifyIntake(
      [file('a.csv', PRIMARY), file('b.csv', PRIMARY)],
      options('braces')
    )
    expect(neither.primary).toBeNull()
    expect(neither.primaryCandidates).toHaveLength(2)
  })

  it('matches curve files against the ids of a primary CSV in the same drop', async () => {
    const plan = await classifyIntake(
      [
        file('force_displacement/B2.csv', 'Displacement [mm],Force [kN]\n0,0\n'),
        file('steel_braces.csv', PRIMARY)
      ],
      options('braces')
    )
    expect(plan.matched.map((match) => match.id)).toEqual(['B2'])
  })
})
