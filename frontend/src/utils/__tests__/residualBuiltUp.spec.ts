/**
 * The built-up models against the lab's own Python (#228).
 *
 * `fixtures/residualBuiltUp.json` holds the curves that `functions_models.py`
 * (delivered with the extended database on #228) computes for 8 built-up
 * records of the data repo, one per branch of the models: doubly symmetric
 * with and without flame-cut flanges, monosymmetric with and without, a
 * measured yield strength missing (expected one used), a hybrid web, a fillet
 * size not reported, a record with no QP file. A `null` curve is a model the
 * Python reports as unavailable for that record.
 *
 * To make it again: copy `functions_models.py` into an empty folder, run
 * `available_model_curves(row, ["QP_fit", "Proposed_model", "Schaper",
 * "prEN1993_1_14"], <data repo>/residual_stresses/QP_Coefficients)` on each row
 * of `residual_stresses.csv` (read with `keep_default_na=False`), and keep the
 * plate, coordinate and residual_stress columns.
 */
import fixture from '@/utils/__tests__/fixtures/residualBuiltUp.json'
import {
  BUILT_UP_MODELS,
  ModelUnavailable,
  builtUpModelCurves,
  createBuiltUpLineSeries,
  geometry,
  modelCurves,
  type BuiltUpModel,
  type Plate
} from '@/utils/residualBuiltUp'
import { describe, expect, it } from 'vitest'

type Row = [Plate, number, number]

interface Case {
  record: Record<string, number | string | null>
  qp: Record<string, number>
  models: Record<BuiltUpModel, Row[] | null>
}

const cases = (fixture as unknown as { records: Case[] }).records

function close(actual: number, expected: number): boolean {
  return Math.abs(actual - expected) <= 1e-9 * Math.max(1, Math.abs(expected))
}

describe('residualBuiltUp matches functions_models.py', () => {
  for (const { record, qp, models } of cases) {
    describe(String(record.id), () => {
      for (const model of BUILT_UP_MODELS) {
        const expected = models[model]
        if (expected === null) {
          it(`${model} is unavailable`, () => {
            expect(() => modelCurves(record, model, qp)).toThrow(ModelUnavailable)
          })
          continue
        }
        it(`${model} gives the same curve`, () => {
          const curves = modelCurves(record, model, qp)
          const actual = (['F1', 'F2', 'W1'] as Plate[]).flatMap((plate) =>
            curves[plate].map(([x, stress]) => [plate, x, stress] as Row)
          )
          expect(actual.length).toBe(expected.length)
          actual.forEach(([plate, x, stress], i) => {
            const [plateExpected, xExpected, stressExpected] = expected[i]
            expect(plate).toBe(plateExpected)
            expect(close(x, xExpected), `${plate} x ${x} vs ${xExpected}`).toBe(true)
            expect(close(stress, stressExpected), `${plate} σ ${stress} vs ${stressExpected}`).toBe(
              true
            )
          })
        })
      }
    })
  }
})

describe('residualBuiltUp.geometry', () => {
  it('gives the bottom flange the top flange dimensions when b2 and tf2 are empty', () => {
    const g = geometry({ h: 300, b: 200, tf: 10, b2: null, tf2: null, tw: 6, A: null })
    expect(g.widthBottom).toBe(200)
    expect(g.tFlangeBottom).toBe(10)
    expect(g.webDepth).toBe(280)
    expect(g.area).toBe(200 * 10 * 2 + 280 * 6)
  })
})

describe('residualBuiltUp.builtUpModelCurves', () => {
  it('leaves out the models that do not apply, without an error', () => {
    const mono = cases.find(({ record }) => record.id === 'Wang_2018_306x126x126x6x10x16_206')!
    const names = builtUpModelCurves(mono.record, mono.qp).map(({ model }) => model)
    expect(names).toEqual(['Schaper', 'prEN1993_1_14'])
  })

  it('returns nothing for a record with no section', () => {
    expect(builtUpModelCurves({ sym: 'doubly' }, {})).toEqual([])
  })
})

describe('residualBuiltUp.createBuiltUpLineSeries', () => {
  const byId = (id: string) => cases.find(({ record }) => record.id === id)!
  const flange: number[][] = [
    [10, 100],
    [50, -50]
  ]
  const web: number[][] = [
    [100, -20],
    [200, -40]
  ]
  const names = (series: { name?: unknown }[]) => series.map(({ name }) => String(name))

  it('gives a monosymmetric section one chart per flange', () => {
    const { record, qp } = byId('Schaper_et_al_2022_150x150x170x8x8x8_103')
    const series = createBuiltUpLineSeries(
      { ...record, flange_nr_data: 2 },
      qp,
      flange,
      flange,
      web
    )
    expect(series.separateFlanges).toBe(true)
    expect(names(series.flange1)).toContain('QP fit')
    expect(names(series.flange2)).toContain('Skiadopoulos et al. (2027)')
    expect(names(series.flange2)[0]).toBe('Measured residual stresses')
  })

  it('draws one flange line per model when F1 and F2 are the same', () => {
    const { record, qp } = byId('Zhu_et_al_2017_314x312x12x25_86')
    const series = createBuiltUpLineSeries(record, qp, flange, [], web)
    expect(series.separateFlanges).toBe(false)
    expect(series.flange2).toEqual([])
    const flangeNames = names(series.flange1)
    expect(flangeNames).toContain('Schaper et al. (2022)')
    expect(flangeNames).not.toContain('Schaper et al. (2022) F2')
  })

  it('centres each flange on its own middle', () => {
    const { record, qp } = byId('Zhu_et_al_2017_314x312x12x25_86')
    const series = createBuiltUpLineSeries(record, qp, flange, [], web)
    const measured = series.flange1[0].data as number[][]
    expect(measured[0][0]).toBeCloseTo(10 - Number(record.b) / 2)
    // The web chart puts the stress on x and the height on y.
    expect(series.web[0].data).toEqual([
      [-20, 100],
      [-40, 200]
    ])
  })

  it('shows the measured F2 only when two flanges were measured', () => {
    const { record, qp } = byId('Zhu_et_al_2017_314x312x12x25_86')
    const one = createBuiltUpLineSeries({ ...record, flange_nr_data: 1 }, qp, flange, flange, web)
    const two = createBuiltUpLineSeries({ ...record, flange_nr_data: 2 }, qp, flange, flange, web)
    expect(names(one.flange1)).not.toContain('Measured residual stresses F2')
    expect(names(two.flange1)).toContain('Measured residual stresses F2')
  })
})
