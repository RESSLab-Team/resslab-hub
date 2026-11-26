/* eslint-disable @typescript-eslint/no-unused-vars */
//Removing warning for unused variables as they might be used in the future
//They exist in the matlab code and might be used in the future
import type { ResidualStressModel } from '@/backend'
import i18n from '@/plugins/i18n'
import { colorPalette } from '@/utils/vuetify'
import type { LineSeriesOption } from 'echarts'

import { inv, matrix, multiply } from 'mathjs'

function linspace(start: number, end: number, n: number): number[] {
  const diff = end - start
  const step = diff / (n - 1)
  return Array(n)
    .fill(0)
    .map((_, i) => start + ~~(i * step))
}

function incorpatePointsFromDistribution(linspace: number[], distribution: number[]) {
  const step = linspace[1] - linspace[0]
  const filteredLinspace = linspace.filter(
    (x) => !distribution.some((x_measured) => Math.abs(x - x_measured) < step * 2) // this way tooltip is triggered for measurements points easily because they are not too close to each other
  )
  return [...new Set(filteredLinspace.concat(distribution).sort((a, b) => a - b))]
}

export function validateResidualModelParams(residual: ResidualStressModel): boolean {
  const requiredFields: Array<keyof ResidualStressModel> = ['fy_n', 'b', 'tf', 'tw', 'h', 'A']
  return requiredFields.every((field) => residual[field] != null && residual[field] != undefined)
}

export function createResidualModels(
  residual: ResidualStressModel,
  qpCoefficient: number[][],
  distributionF1: number[][],
  distributionW1: number[][],
  distributionF2?: number[][]
) {
  const { h_over_b, h, A, b, tf, tw, fy_n } = residual

  if (!(h && tf && b && tw && fy_n && A && qpCoefficient)) {
    return
  } else {
    const coeff = qpCoefficient.map((serie) => serie[0])
    // The saved fit of this record (four coefficients, README of the data repo).
    const hasQpFit = coeff.length === 4 && coeff.every((value) => Number.isFinite(value))

    const h0 = h - 2 * tf

    const h_b_norm_full = 2 * ((h_over_b - 0.95) / (3.04 - 0.95)) - 1
    const h_norm_full = 2 * ((h - 96) / (1090 - 96)) - 1
    const Area_norm_full = 2 * ((A - 1320) / (175000 - 1320)) - 1

    // Calculate coefficients a, c, d and b for the full model
    const coeff_a_full = 107 + 51 * h_b_norm_full + 20 * Area_norm_full
    const coeff_c_full = -(142 + 84 * h_b_norm_full)
    const coeff_d_full = ((coeff_a_full - coeff_c_full) / Math.pow(h - tf, 2)) * 4
    const coeff_b_full =
      (-(
        2 * tf * b * coeff_a_full +
        tw * (h - 2 * tf) * coeff_c_full +
        ((tw * Math.pow(h - 2 * tf, 3)) / 12) * coeff_d_full
      ) /
        (2 * tf * Math.pow(b, 3))) *
      12

    // Define the quadratic polynomial models for the flange and web in RS
    const QP_Model_full_flange_RS = (x: number) =>
      coeff_a_full + coeff_b_full * Math.pow(x - b / 2, 2)
    const QP_Model_full_web_RS = (y: number) => coeff_c_full + coeff_d_full * Math.pow(y - h / 2, 2)

    // Define the quadratic polynomial models for the flange and web
    const QP_flange_RS = (x: number) => coeff[0] + coeff[1] * Math.pow(x - b / 2, 2)
    const QP_web_RS = (y: number) => coeff[2] + coeff[3] * Math.pow(y - h / 2, 2)

    // Define evenly spaced vectors x, y and their variants
    const N_POINTS = 100

    const x_measured = distributionF1
      .map((x) => x[0])
      .concat(distributionF2?.map((x) => x[0]) ?? [])
      .concat([0])

    const x = incorpatePointsFromDistribution(linspace(0, b, N_POINTS), x_measured)
    const x_mod = linspace(0, b, 3)
    const x1 = linspace(0, b / 2, 2)
    const x2 = linspace(b / 2, b, 2)
    const x3 = incorpatePointsFromDistribution(
      linspace(-b / 2, b / 2, N_POINTS),
      x_measured.map((x) => x - b / 2)
    )

    const x3_scatter = linspace(-b / 2, b / 2, 3)

    const y_measured = distributionW1.map((y) => y[0])

    const y = incorpatePointsFromDistribution(linspace(0, h, N_POINTS), y_measured)

    const y_mod = linspace(0, h, 3)
    const y1 = linspace(tf / 2, h / 2, 2)
    const y2 = linspace(h / 2, h - tf / 2, 2)
    const y3 = incorpatePointsFromDistribution(
      linspace(-(h - tf) / 2, (h - tf) / 2, N_POINTS),
      y_measured.map((y) => y - h / 2)
    )

    const y3_scatter = linspace(-(h - tf) / 2, (h - tf) / 2, 3)
    const y4 = incorpatePointsFromDistribution(linspace(tf / 2, h - tf / 2, N_POINTS), y_measured)

    const y4_mod = linspace(tf / 2, h - tf / 2, 3)

    // Galambos and Ketter 1959
    const sigma_c_GK = -0.3 * fy_n
    const sigma_t_GK = -sigma_c_GK / (1 + ((h * tw) / (b * tf)) * (1 - (2 * tf) / h))

    // Define the stress functions GK_flange_RS1, GK_flange_RS2 and GK_web_RS
    const GK_flange_RS1 = (x1: number) => (2 / b) * (sigma_t_GK - sigma_c_GK) * x1 + sigma_c_GK
    const GK_flange_RS2 = (x2: number) =>
      (2 / b) * (sigma_c_GK - sigma_t_GK) * x2 + 2 * sigma_t_GK - sigma_c_GK
    const GK_flange = (x: number) => (x < b / 2 ? GK_flange_RS1(x) : GK_flange_RS2(x))

    const GK_web_RS = sigma_t_GK

    // ECCS 1984

    let alpha = 0.5

    // Determine alpha based on h/b ratio
    if (h / b > 1.2) {
      alpha = 0.3
    }

    // Calculate sigma_t_ECCS and sigma_c_ECCS based on fy and alpha
    const sigma_t_ECCS = fy_n * alpha
    const sigma_c_ECCS = -fy_n * alpha

    // Define the stress functions for ECCS model
    const ECCS_flange_RS1 = (x: number) =>
      (2 / b) * (sigma_t_ECCS - sigma_c_ECCS) * x + sigma_c_ECCS
    const ECCS_flange_RS2 = (x: number) =>
      (2 / b) * (sigma_c_ECCS - sigma_t_ECCS) * x + 2 * sigma_t_ECCS - sigma_c_ECCS
    const ECCS_flange = (x: number) => (x < b / 2 ? ECCS_flange_RS1(x) : ECCS_flange_RS2(x))

    const ECCS_web_RS1 = (y: number) => (2 / h) * (sigma_c_ECCS - sigma_t_ECCS) * y + sigma_t_ECCS
    const ECCS_web_RS2 = (y: number) =>
      (2 / h) * (sigma_t_ECCS - sigma_c_ECCS) * y + 2 * sigma_c_ECCS - sigma_t_ECCS
    const ECCS_web = (x: number) => (x < h / 2 ? ECCS_web_RS1(x) : ECCS_web_RS2(x))

    // Young 1975

    // Calculate sigma values according to Young 1975 model
    const sigma_t_YOUNG = 100 * (0.7 + (h0 * tw) / (2 * b * tf))
    const sigma_c1_YOUNG = -165 * (1 - (h0 * tw) / (2.4 * b * tf))
    const sigma_c2_YOUNG = -100 * (1.5 + (h0 * tw) / (2.4 * b * tf))

    // Define the stress functions for Young model
    const YOUNG_flange_RS = (x3: number) =>
      (4 / Math.pow(b, 2)) * (sigma_c1_YOUNG - sigma_t_YOUNG) * Math.pow(x3, 2) + sigma_t_YOUNG
    const YOUNG_web_RS = (y3: number) =>
      (4 / Math.pow(h - tf, 2)) * (sigma_t_YOUNG - sigma_c2_YOUNG) * Math.pow(y3, 2) +
      sigma_c2_YOUNG

    // Szalai and Papp 2005

    // Define alpha_SP and calculate parameters af, aw, cf, and cw
    const alpha_SP = 0.35

    const af =
      (-alpha_SP *
        fy_n *
        (20 * Math.pow(b, 3) * tf + 48 * b * Math.pow(h0, 2) * tf + 4 * Math.pow(h0, 3) * tw)) /
      (Math.pow(b, 2) *
        (2 * Math.pow(b, 3) * tf + 8 * b * Math.pow(h0, 2) * tf + Math.pow(h0, 3) * tw))
    const aw =
      (alpha_SP *
        fy_n *
        2 *
        b *
        tf *
        (8 * Math.pow(b, 3) * tf + 9 * Math.pow(b, 2) * h0 * tw + 10 * Math.pow(h0, 3) * tw)) /
      (Math.pow(h0, 3) *
        tw *
        (2 * Math.pow(b, 3) * tf + 8 * b * Math.pow(h0, 2) * tf + Math.pow(h0, 3) * tw))
    const cf =
      (alpha_SP * fy_n * b * tf * (3 * Math.pow(b, 2) + 4 * Math.pow(h0, 2))) /
      (2 * Math.pow(b, 3) * tf + 8 * b * Math.pow(h0, 2) * tf + Math.pow(h0, 3) * tw)
    const cw =
      (-alpha_SP *
        fy_n *
        b *
        tf *
        (8 * Math.pow(b, 3) * tf + 3 * Math.pow(b, 2) * h0 * tw + 2 * Math.pow(h0, 3) * tw)) /
      (2 *
        h0 *
        tw *
        (2 * Math.pow(b, 3) * tf + 8 * b * Math.pow(h0, 2) * tf + Math.pow(h0, 3) * tw))

    // Define the stress functions for Szalai and Papp model
    const SP_flange_RS = (x3: number) => cf + af * Math.pow(x3, 2)
    const SP_web_RS = (y3: number) => cw + aw * Math.pow(y3, 2)

    // Bradford and Trahair 1985
    // Define matrix and vector for Bradford and Trahair 1985 model
    const MAT_A = matrix([
      [1, 0, 0, 0, 0],
      [0, 1, 0, 0, 0],
      [0, 0, 1, 1, 1],
      [0, 0, 1, 1 / 3, 1 / 5],
      [0, 0, 1 / 3, 1 / 5, 1 / 7]
    ])
    const Af_Aw: number = (2 * b * tf) / (h0 * tw)
    const VECT_b = matrix([
      [1 / 2],
      [17 / 20],
      [1 / 2],
      [(-13 / 60) * Af_Aw],
      [(Af_Aw * (Math.pow(b, 2) - 11 * Math.pow(h0 + tf, 2))) / (300 * Math.pow(h0, 2))]
    ])

    // Solve system to get coefficients
    const coeff_BT = multiply(inv(MAT_A), VECT_b)

    // Define the stress functions for Bradford and Trahair model
    const BT_flange_RS = (x3: number) =>
      fy_n * (coeff_BT.get([0, 0]) - coeff_BT.get([1, 0]) * Math.pow((2 * x3) / b, 2))
    const BT_web_RS = (y3: number) =>
      fy_n *
      (coeff_BT.get([2, 0]) +
        coeff_BT.get([3, 0]) * Math.pow((2 * y3) / ((h ?? 0) - (tf ?? 0)), 2) +
        coeff_BT.get([4, 0]) * Math.pow((2 * y3) / ((h ?? 0) - (tf ?? 0)), 4))

    return {
      x,
      x3,
      y,
      y3,
      y4,
      QP_Model_full_flange_RS,
      GK_flange,
      ECCS_flange,
      YOUNG_flange_RS,
      SP_flange_RS,
      BT_flange_RS,
      QP_Model_full_web_RS,
      GK_web_RS,
      ECCS_web,
      YOUNG_web_RS,
      SP_web_RS,
      BT_web_RS,
      QP_flange_RS: hasQpFit ? QP_flange_RS : undefined,
      QP_web_RS: hasQpFit ? QP_web_RS : undefined
    }
  }
}

/** Name of the saved fit's curve, for hot-rolled and built-up records (#228). */
export const QP_FIT_NAME = 'QP fit'

export function createLineSeries(
  residual: ResidualStressModel,
  qpCoefficient: number[][],
  distributionF1: number[][],
  distributionW1: number[][],

  distributionF2?: number[][]
): { flangeSeries: LineSeriesOption[]; webSeries: LineSeriesOption[] } {
  const { h_over_b, h, A, b, tf, tw, fy_n, flange_nr_data } = residual

  if (!validateResidualModelParams(residual)) {
    return { flangeSeries: [], webSeries: [] }
  }

  // Call the model creation function
  const models = createResidualModels(
    residual,
    qpCoefficient,
    distributionF1,
    distributionW1,
    distributionF2
  )

  // If models are undefined, return empty series
  if (!models) {
    console.warn('Model creation failed due to missing parameters.')
    return { flangeSeries: [], webSeries: [] }
  }

  const {
    x,
    x3,
    y,
    y3,
    y4,
    QP_Model_full_flange_RS,
    GK_flange,
    ECCS_flange,
    YOUNG_flange_RS,
    SP_flange_RS,
    BT_flange_RS,
    QP_Model_full_web_RS,
    GK_web_RS,
    ECCS_web,
    YOUNG_web_RS,
    SP_web_RS,
    BT_web_RS,
    QP_flange_RS,
    QP_web_RS
  } = models

  const flangeSeries = [
    {
      name: i18n.global.t('enum.measuredResidualStresses') + (flange_nr_data == 2 ? ' F1' : ''),
      showSymbol: true,
      lineStyle: {
        width: 3
      },

      data: distributionF1.map((x) => [b ? x[0] - b / 2 : x[0], x[1]])
    },
    {
      name: i18n.global.t('enum.measuredResidualStressesF2'),
      showSymbol: true,
      lineStyle: {
        width: 3
      },
      color: colorPalette.at(-1),
      data:
        flange_nr_data > 1 && distributionF2
          ? distributionF2.map((x) => [b ? x[0] - b / 2 : x[0], x[1]])
          : []
    },
    {
      name: 'Skiadopoulos et al., 2023',

      lineStyle: {
        width: 3
      },
      xAxis: {
        max: 100
      },
      data: x.map((x) => [b ? x - b / 2 : x, QP_Model_full_flange_RS(x)])
    },

    {
      name: 'Galambos and Ketter 1959',

      lineStyle: { type: 'dashed' },
      data: x.map((x) => [b ? x - b / 2 : x, GK_flange(x)])
    },
    {
      name: 'ECCS 1984',

      lineStyle: { type: 'dashed' },
      data: x.map((x) => [b ? x - b / 2 : x, ECCS_flange(x)])
    },
    {
      name: 'Young 1975',

      lineStyle: { type: 'dashed' },
      data: x3.map((x) => [x, YOUNG_flange_RS(x)])
    },
    {
      name: 'Szalai and Papp 2005',

      lineStyle: { type: 'dashed' },
      data: x3.map((x) => [x, SP_flange_RS(x)])
    },
    {
      name: 'Bradford and Trahair 1985',

      lineStyle: { type: 'dashed' },
      data: x3.map((x) => [x, BT_flange_RS(x)])
    }
  ]
    .filter((d) =>
      d.name == i18n.global.t('enum.measuredResidualStressesF2') ? flange_nr_data == 2 : true
    )
    .map((d) => ({ ...d })) as LineSeriesOption[]
  // Last, so the series above keep their palette colors.
  if (QP_flange_RS) {
    flangeSeries.push({
      name: QP_FIT_NAME,
      type: 'line',
      lineStyle: { width: 2 },
      data: x.map((x) => [b ? x - b / 2 : x, QP_flange_RS(x)])
    })
  }

  const webSeries = [
    {
      name: i18n.global.t('enum.measuredResidualStresses'),
      showSymbol: true,
      lineStyle: {
        width: 3
      },
      triggerLineEvent: true,
      data: distributionW1.map((y) => y.reverse())
    },
    {
      name: 'Skiadopoulos et al., 2023',

      lineStyle: {
        width: 3
      },
      data: y4.map((y) => [QP_Model_full_web_RS(y), y])
    },

    {
      name: 'Galambos and Ketter 1959',

      lineStyle: { type: 'dashed' },
      data: y4.map((y) => [GK_web_RS, y])
    },
    {
      name: 'ECCS 1984',

      lineStyle: { type: 'dashed' },
      data: y4.map((y) => [ECCS_web(y), y])
    },
    {
      name: 'Young 1975',

      lineStyle: { type: 'dashed' },
      data: y3.map((y, i) => [YOUNG_web_RS(y), h ? y + h / 2 : y])
    },
    {
      name: 'Szalai and Papp 2005',

      lineStyle: { type: 'dashed' },
      data: y3.map((y, i) => [SP_web_RS(y), h ? y + h / 2 : y])
    },
    {
      name: 'Bradford and Trahair 1985',

      lineStyle: { type: 'dashed' },
      data: y3.map((y, i) => [BT_web_RS(y), h ? y + h / 2 : y])
    }
  ].map((d) => ({ ...d, encode: { tooltip: [0] } })) as LineSeriesOption[]
  if (QP_web_RS) {
    webSeries.push({
      name: QP_FIT_NAME,
      type: 'line',
      lineStyle: { width: 2 },
      data: y4.map((y) => [QP_web_RS(y), y]),
      encode: { tooltip: [0] }
    })
  }

  return { flangeSeries, webSeries }
}
