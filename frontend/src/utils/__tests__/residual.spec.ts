import type { ResidualStressModel } from '@/backend'
import {
  QP_FIT_NAME,
  createLineSeries,
  createResidualModels,
  validateResidualModelParams
} from '@/utils/residual'
import type { LineSeriesOption } from 'echarts'
import { describe, expect, it } from 'vitest'

const validParams = {
  fy_n: 355,
  b: 300,
  tf: 19,
  tw: 11,
  h: 340,
  A: 17000,
  h_over_b: 1.13
} as unknown as ResidualStressModel

describe('residual.validateResidualModelParams', () => {
  it('passes when every required field is present', () => {
    expect(validateResidualModelParams(validParams)).toBe(true)
  })

  it('fails when a required field is missing or null', () => {
    expect(
      validateResidualModelParams({ ...validParams, tw: null } as unknown as ResidualStressModel)
    ).toBe(false)
    expect(validateResidualModelParams({} as ResidualStressModel)).toBe(false)
  })
})

describe('residual.createResidualModels', () => {
  it('returns undefined when required params or coefficients are missing', () => {
    expect(createResidualModels({} as ResidualStressModel, [], [], [])).toBeUndefined()
  })

  it('returns a model when params and a QP coefficient set are provided', () => {
    const qpCoefficient = [[100], [-120], [150], [0.01]]
    const result = createResidualModels(validParams, qpCoefficient, [[0]], [[0]])
    expect(result).toBeDefined()
  })
})

// Two real hot-rolled records of the data repo, with their files. The snapshot
// was taken before the built-up sections (#228): the hot-rolled curves must
// not move. Only the "QP fit" series is new, so it is left out here.
const KETTER = {
  record: {
    id: 'Ketter_1958_W4x13_1',
    h: 106,
    b: 103,
    tw: 7.1,
    tf: 8.8,
    A: 2470,
    fy_n: 250,
    flange_nr_data: 1,
    h_over_b: 106 / 103
  },
  qp: [[30.9653789509005], [-0.0565117121688848], [26.8139], [0.001751166958143]],
  f1: [
    [20.6, -80.44166667],
    [18.025, -61.28888889],
    [23.175, -42.13611111],
    [23.175, -26.81388889],
    [28.325, -14.04537037],
    [28.325, -6.384259259],
    [30.9, 0],
    [36.05, 7.661111111],
    [38.625, 14.04537037],
    [48.925, 21.70648148],
    [61.8, 21.70648148],
    [66.95, 14.04537037],
    [69.525, 5.107407407],
    [72.1, -3.830555556],
    [74.675, -14.04537037],
    [77.25, -25.53703704],
    [79.825, -38.30555556],
    [82.4, -51.07407407],
    [82.4, -61.28888889],
    [90.125, -70.22685185],
    [87.55, -77.88796296]
  ],
  f2: [],
  w1: [
    [20.52, 36.39027778],
    [29.16, 32.55972222],
    [39.96, 28.72916667],
    [48.6, 26.81388889],
    [57.24, 26.81388889],
    [66.96, 28.72916667],
    [76.68, 30.64444444],
    [89.64, 36.39027778]
  ]
}

const SOUSA = {
  record: {
    id: 'Sousa_and_Lignos_2017_IPE400_18',
    h: 400,
    b: 180,
    tw: 8.6,
    tf: 13.5,
    A: 8450,
    fy_n: 355,
    flange_nr_data: 2,
    h_over_b: 400 / 180
  },
  qp: [[124.462467343733], [-0.021953977753116], [-199.263743058165], [0.00866839829770666]],
  f1: [
    [10.7833333333333, -3.47721948448036],
    [32.35, 14.0409853589921],
    [53.9166666666667, 79.5024947577895],
    [90, 140.199107081941],
    [126.083333333333, 89.1193185873152],
    [147.65, 11.6837857494739],
    [169.216666666667, -3.28055964535146]
  ],
  f2: [
    [10.7833333333333, 0.277706211108789],
    [32.35, 3.65062444769165],
    [53.9166666666667, 83.6861146032769],
    [90, 148.817705983931],
    [126.083333333333, 90.4622403506019],
    [147.65, 21.3490956082956],
    [169.216666666667, -18.6995501351038]
  ],
  w1: [
    [44.84375, -21.4600011397246],
    [106.90625, -144.960578881095],
    [189.65625, -212.015179127498],
    [272.40625, -163.361295416383],
    [355.15625, -19.2299986823]
  ]
}

describe('residual.createLineSeries keeps the hot-rolled curves', () => {
  const copy = (rows: number[][]) => rows.map((row) => [...row])
  it.each([
    ['Ketter_1958_W4x13_1', KETTER],
    ['Sousa_and_Lignos_2017_IPE400_18', SOUSA]
  ])('%s', (_, fixture) => {
    const { flangeSeries, webSeries } = createLineSeries(
      fixture.record as unknown as ResidualStressModel,
      copy(fixture.qp),
      copy(fixture.f1),
      copy(fixture.w1),
      copy(fixture.f2)
    )
    const old = (series: LineSeriesOption[]) => series.filter((s) => s.name !== QP_FIT_NAME)
    expect({ flange: old(flangeSeries), web: old(webSeries) }).toMatchSnapshot()
  })
})

describe('residual.createLineSeries adds the saved QP fit', () => {
  it('draws c1 + c2 (x - b/2)^2 and c3 + c4 (y - h/2)^2', () => {
    const { flangeSeries, webSeries } = createLineSeries(
      KETTER.record as unknown as ResidualStressModel,
      KETTER.qp.map((row) => [...row]),
      KETTER.f1.map((row) => [...row]),
      KETTER.w1.map((row) => [...row]),
      []
    )
    const flange = flangeSeries.find((s) => s.name === QP_FIT_NAME)!.data as number[][]
    const web = webSeries.find((s) => s.name === QP_FIT_NAME)!.data as number[][]
    const [c1, c2, c3, c4] = KETTER.qp.map(([value]) => value)
    // x is centred on mid-width in the chart, y is the height.
    flange.forEach(([x, stress]) => expect(stress).toBeCloseTo(c1 + c2 * x ** 2, 9))
    web.forEach(([stress, y]) => expect(stress).toBeCloseTo(c3 + c4 * (y - 106 / 2) ** 2, 9))
    expect(flangeSeries.at(-1)!.name).toBe(QP_FIT_NAME)
  })

  it('has no QP fit without four coefficients', () => {
    const { flangeSeries, webSeries } = createLineSeries(
      KETTER.record as unknown as ResidualStressModel,
      [],
      KETTER.f1.map((row) => [...row]),
      KETTER.w1.map((row) => [...row]),
      []
    )
    expect(flangeSeries.some((s) => s.name === QP_FIT_NAME)).toBe(false)
    expect(webSeries.some((s) => s.name === QP_FIT_NAME)).toBe(false)
  })
})
