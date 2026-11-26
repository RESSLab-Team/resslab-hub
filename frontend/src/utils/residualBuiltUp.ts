/**
 * Residual stress models of built-up (welded) sections (#228).
 *
 * A port of the built-up part of the lab's `functions_models.py` (delivered on
 * #228 with the extended database): the saved QP fit of a record, the proposed
 * model "Skiadopoulos et al. (2027)", Schaper et al. (2022) and prEN1993-1-14.
 * Every model is piecewise linear, in mm and MPa:
 *
 * - flange coordinates start at the left edge of each flange (F1 is the top
 *   flange, with `b` and `tf`; F2 the bottom one, with `b2` and `tf2`);
 * - the web coordinate goes up from the outer bottom face of the section, so
 *   the clear web runs from `tf2` to `h - tf`;
 * - a stress jump is two points at the same coordinate, in order.
 *
 * The hot-rolled models stay in `residual.ts`. A model that cannot be computed
 * for a record (a missing input, a section the model does not cover) throws
 * `ModelUnavailable`, which `builtUpModelCurves` turns into "no curve".
 * Tested against curves computed with the lab's Python
 * (`__tests__/residualBuiltUp.spec.ts`).
 */
import i18n from '@/plugins/i18n'
import { colorPalette } from '@/utils/palette'
import type { LineSeriesOption } from 'echarts'

export class ModelUnavailable extends Error {}

/** A record as the API serves it: numbers, or null for NA and NR. */
export type BuiltUpRecord = Record<string, unknown>

export type Plate = 'F1' | 'F2' | 'W1'
/** [coordinate in mm, stress in MPa] */
export type Point = [number, number]
export type PlateCurves = Record<Plate, Point[]>
type Parameters = Record<string, number>

/** The named values of a built-up QP file (README of the data repo). */
export const BUILT_UP_QP_COLUMNS = [
  'dfc_top',
  'dfe_top',
  'dffe_top',
  'sigma_fc_top',
  'sigma_fe_top',
  'sigma_ffe_top',
  'dwc',
  'dwe_top',
  'dwe_bot',
  'sigma_wc',
  'sigma_we_top',
  'sigma_we_bot',
  'dfc_bot',
  'dfe_bot',
  'dffe_bot',
  'sigma_fc_bot',
  'sigma_fe_bot',
  'sigma_ffe_bot'
] as const

export const BUILT_UP_MODELS = ['QP_fit', 'Proposed_model', 'Schaper', 'prEN1993_1_14'] as const
export type BuiltUpModel = (typeof BUILT_UP_MODELS)[number]

export const BUILT_UP_MODEL_LABELS: Record<BuiltUpModel, string> = {
  QP_fit: 'QP fit',
  Proposed_model: 'Skiadopoulos et al. (2027)',
  Schaper: 'Schaper et al. (2022)',
  prEN1993_1_14: 'prEN1993-1-14'
}

/** A finite number of the record, else the fallback, else ModelUnavailable. */
function numeric(record: BuiltUpRecord, key: string, fallback?: number): number {
  const raw = record[key]
  const value = typeof raw === 'string' && raw.trim() !== '' ? Number(raw) : raw
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (fallback !== undefined) return fallback
  throw new ModelUnavailable(`Missing numeric input: ${key}`)
}

function text(record: BuiltUpRecord, key: string): string {
  const value = record[key]
  return typeof value === 'string' ? value.trim().toLowerCase() : ''
}

/** numpy.isclose with its defaults, or the given tolerances. */
function isClose(a: number, b: number, rtol = 1e-5, atol = 1e-8): boolean {
  return Math.abs(a - b) <= atol + rtol * Math.abs(b)
}

export interface Geometry {
  height: number
  widthTop: number
  widthBottom: number
  tFlangeTop: number
  tFlangeBottom: number
  tWeb: number
  webDepth: number
  area: number
}

/** The section dimensions. F2 takes the F1 values when `b2` or `tf2` is empty. */
export function geometry(record: BuiltUpRecord): Geometry {
  const h = numeric(record, 'h')
  const b = numeric(record, 'b')
  const tf = numeric(record, 'tf')
  const b2 = numeric(record, 'b2', b)
  const tf2 = numeric(record, 'tf2', tf)
  const tw = numeric(record, 'tw')
  const depth = h - tf - tf2
  if (Math.min(h, b, b2, tf, tf2, tw, depth) <= 0) {
    throw new ModelUnavailable('Section dimensions and clear web depth must be positive')
  }
  const area = numeric(record, 'A', b * tf + b2 * tf2 + depth * tw)
  if (area <= 0) throw new ModelUnavailable('Section area must be positive')
  return {
    height: h,
    widthTop: b,
    widthBottom: b2,
    tFlangeTop: tf,
    tFlangeBottom: tf2,
    tWeb: tw,
    webDepth: depth,
    area
  }
}

export function isBuiltUp(record: BuiltUpRecord): boolean {
  return text(record, 'profile_type').includes('built-up')
}

export function isMonosymmetric(record: BuiltUpRecord): boolean {
  return ['mono', 'monosymmetric'].includes(text(record, 'sym'))
}

/** The flange plates were flame-cut: the models add a tip zone at each edge. */
export function isFlameCut(record: BuiltUpRecord): boolean {
  return text(record, 'plt_cut_f') === 'flame-cut'
}

function positiveYield(record: BuiltUpRecord, key: string, fallback?: number): number {
  const value = numeric(record, key, fallback)
  if (value <= 0) throw new ModelUnavailable(`Positive yield strength ${key} is required`)
  return value
}

// --- Piecewise curves ---------------------------------------------------------

/** [width, stress at the start, stress at the end] */
type Segment = [number, number, number]

function piecewiseSegments(
  plate: Plate,
  origin: number,
  length: number,
  segments: Segment[]
): Point[] {
  const widths = segments.map(([width]) => width)
  if (!segments.flat().every((value) => Number.isFinite(value))) {
    throw new Error(`Nonfinite piecewise parameter for ${plate}.`)
  }
  if (widths.some((width) => width < 0)) throw new Error(`Negative piecewise width for ${plate}.`)
  const total = widths.reduce((sum, width) => sum + width, 0)
  if (!isClose(total, length, 1e-9, 1e-9)) {
    throw new Error(`${plate} zone widths do not close over the plate length.`)
  }
  const points: Point[] = []
  let x = origin
  for (const [width, start, end] of segments) {
    if (width <= 0) continue
    const right = x + width
    points.push([x, start], [right, end])
    x = right
  }
  if (points.length === 0) throw new Error(`No positive piecewise zone for ${plate}.`)
  // The widths close up to the floating-point sum, the last point exactly.
  points[points.length - 1] = [origin + length, points[points.length - 1][1]]
  return points
}

/**
 * The curves of named zone parameters. `flame` adds the flame-cut tip zones,
 * `transition` the linear transitions (prEN1993-1-14 only).
 */
export function piecewiseCurve(
  profile: Parameters,
  geom: Geometry,
  flame = false,
  transition = false
): PlateCurves {
  const get = (key: string) => profile[key] ?? 0
  const flange = (side: 'top' | 'bot', plate: Plate, width: number): Point[] => {
    const dc = profile[`dfc_${side}`]
    const de = profile[`dfe_${side}`]
    const dt = transition ? get(`dft_${side}`) : 0
    const df = flame ? get(`dffe_${side}`) : 0
    const dft = flame && transition ? get(`dfft_${side}`) : 0
    const sc = profile[`sigma_fc_${side}`]
    const se = profile[`sigma_fe_${side}`]
    const sf = flame ? get(`sigma_ffe_${side}`) : 0
    return piecewiseSegments(plate, 0, width, [
      [df, sf, sf],
      [dft, sf, se],
      [de, se, se],
      [dt, se, sc],
      [dc, sc, sc],
      [dt, sc, se],
      [de, se, se],
      [dft, se, sf],
      [df, sf, sf]
    ])
  }
  const dbt = transition ? get('dwt_bot') : 0
  const dtt = transition ? get('dwt_top') : 0
  const [sc, sb, st] = [profile.sigma_wc, profile.sigma_we_bot, profile.sigma_we_top]
  return {
    F1: flange('top', 'F1', geom.widthTop),
    F2: flange('bot', 'F2', geom.widthBottom),
    W1: piecewiseSegments('W1', geom.tFlangeBottom, geom.webDepth, [
      [profile.dwe_bot, sb, sb],
      [dbt, sb, sc],
      [profile.dwc, sc, sc],
      [dtt, sc, st],
      [profile.dwe_top, st, st]
    ])
  }
}

// --- The models -----------------------------------------------------------------

/** prEN1993-1-14, each plate on its own width, with linear transitions. */
export function prenParameters(record: BuiltUpRecord): Parameters {
  const g = geometry(record)
  const fy = positiveYield(record, 'fy_n')
  const p: Parameters = {}
  for (const [side, width] of [
    ['top', g.widthTop],
    ['bot', g.widthBottom]
  ] as const) {
    Object.assign(p, {
      [`dfc_${side}`]: 0.15 * width,
      [`dft_${side}`]: 0.05 * width,
      [`dfe_${side}`]: 0.375 * width,
      [`dfft_${side}`]: 0,
      [`dffe_${side}`]: 0,
      [`sigma_fc_${side}`]: fy,
      [`sigma_fe_${side}`]: -0.25 * fy,
      [`sigma_ffe_${side}`]: 0
    })
  }
  const d = g.webDepth
  p.dwc = 0.75 * d
  p.sigma_wc = -0.25 * fy
  for (const side of ['top', 'bot']) {
    p[`dwe_${side}`] = 0.075 * d
    p[`dwt_${side}`] = 0.05 * d
    p[`sigma_we_${side}`] = fy
  }
  return p
}

/**
 * Schaper et al. (2022). The weld zone of a flange is min(tw + 5a, b/5), or b/5
 * when the throat `a` (`fillet_size`) is not reported. Flame-cut tips take b/16
 * each at half the weld tension. Compression balances each plate.
 */
export function schaperParameters(record: BuiltUpRecord): Parameters {
  const g = geometry(record)
  const fy = positiveYield(record, 'fy_n')
  const tension = Math.sqrt(235 / fy) * fy
  const raw = record.fillet_size
  const throat = typeof raw === 'number' ? raw : Number.NaN
  if (Number.isFinite(throat) && throat < 0) {
    throw new ModelUnavailable('The fillet weld throat cannot be negative.')
  }
  const flame = isFlameCut(record)
  const p: Parameters = {}
  for (const [side, width] of [
    ['top', g.widthTop],
    ['bot', g.widthBottom]
  ] as const) {
    const dc = Number.isFinite(throat) ? Math.min(g.tWeb + 5 * throat, width / 5) : width / 5
    const df = flame ? width / 16 : 0
    const de = (width - dc - 2 * df) / 2
    if (de <= 0) throw new ModelUnavailable('Schaper requires a positive compressive flange zone.')
    const tipTension = flame ? 0.5 * tension : 0
    const compression = -(dc * tension + 2 * df * tipTension) / (2 * de)
    Object.assign(p, {
      [`dfc_${side}`]: dc,
      [`dft_${side}`]: 0,
      [`dfe_${side}`]: de,
      [`dfft_${side}`]: 0,
      [`dffe_${side}`]: df,
      [`sigma_fc_${side}`]: tension,
      [`sigma_fe_${side}`]: compression,
      [`sigma_ffe_${side}`]: tipTension
    })
  }
  const d = g.webDepth
  p.dwc = 0.8 * d
  for (const side of ['top', 'bot']) {
    p[`dwe_${side}`] = 0.1 * d
    p[`dwt_${side}`] = 0
    p[`sigma_we_${side}`] = tension
  }
  p.sigma_wc = (-(p.dwe_top + p.dwe_bot) * tension) / p.dwc
  return p
}

// The calibration of the proposed model (Process_RS_statistics.ipynb of the lab).
// Predictors, in this order: Aw/A, h, b/(2tf), E/fy, each scaled to [-1, 1].
interface Calibration {
  bounds: [number, number][]
  constant: Record<string, number>
  linear: Record<string, number[]>
  flangeClosure: string
  webClosure: string
  equilibrium: string
}

const PROPOSED: Record<'doubly_no_flame' | 'doubly_flame', Calibration> = {
  doubly_no_flame: {
    bounds: [
      [0.1764705882352941, 0.5401882693700217],
      [139.36, 800.0],
      [2.8000000000000003, 25.5],
      [206.18556701030928, 1015.2284263959391]
    ],
    constant: { dfe_top_over_b: 0.3802613046481681 },
    linear: {
      dwc_over_d: [
        0.7892295860046206, 0.06142196434947646, 0.1419199801043955, 0.04696903371326695,
        -0.04394966880130116
      ],
      sigma_fc_top: [
        0.5498583051599492, -0.22226836963068694, 0.13987899025148587, 0.18840254193899048,
        0.08552612786370302
      ],
      sigma_fe_top: [
        -0.1657009301526215, 0.07139148842934573, 0.04321071511360974, -0.03483179612975222,
        -0.10505688336008749
      ]
    },
    flangeClosure: 'dfc_top_over_b',
    webClosure: 'dwe_top_over_d',
    equilibrium: 'sigma_wc'
  },
  doubly_flame: {
    bounds: [
      [0.09560723514211886, 0.5462765842199868],
      [110.0, 750.0],
      [2.0, 14.5],
      [200.40080160320642, 900.9009009009009]
    ],
    constant: { dfc_top_over_b: 0.20273940579783864, dfe_top_over_b: 0.32023466769513 },
    linear: {
      dwe_top_over_d: [
        0.0844707366292005, -0.035253943763982824, -0.04179356635612762, -0.05292941383156082,
        -0.01596024652085378
      ],
      sigma_fc_top: [
        0.4610803127969198, 0.013868313686763688, -0.13246947286596134, 0.024285082605596774,
        0.3151235440433726
      ],
      sigma_ffe_top: [
        0.14289182350548874, -0.20054384004328832, 0.11184813974640154, -0.060705074208740634,
        0.007271804688259753
      ],
      sigma_wc: [
        -0.09681822296698392, -0.08033843227215867, 0.12399288546980151, -0.060918811389686106,
        -0.08280163515708513
      ]
    },
    flangeClosure: 'dffe_top_over_b',
    webClosure: 'dwc_over_d',
    equilibrium: 'sigma_fe_top'
  }
}

const MONO = {
  dfc: 0.25534901058119963,
  dft: 0.0,
  dffe: 0.057083907555200104,
  dfft: 0.0,
  sigma_fc: 0.4253255722957469,
  sigma_ffe: 0.0761236215583143,
  dwe: 0.10478275021906125
} as const

/** Measured flange fy, else the expected one. Never the nominal one. */
function referenceYield(record: BuiltUpRecord): number {
  const measured = numeric(record, 'fy_mf', Number.NaN)
  if (Number.isFinite(measured) && measured > 0) return measured
  return positiveYield(record, 'fy_e')
}

/** The width fractions, bounded below, the closure taking what is left. */
function closeWidths(values: Parameters, names: string[], closure: string): Parameters {
  const weight = (name: string) => (names.indexOf(name) === 0 ? 1 : 2)
  const modeled = names.filter((name) => name !== closure)
  const bounded = Object.fromEntries(modeled.map((name) => [name, Math.max(values[name], 0.005)]))
  const contribution = modeled.reduce((sum, name) => sum + weight(name) * bounded[name], 0)
  const factor = Math.min((1 - weight(closure) * 0.005) / contribution, 1)
  const result: Parameters = Object.fromEntries(
    modeled.map((name) => [name, bounded[name] * factor])
  )
  result[closure] =
    (1 - modeled.reduce((sum, name) => sum + weight(name) * result[name], 0)) / weight(closure)
  return result
}

/** A flame-cut tip less in tension than the edge zone: both take their mean. */
function orderStresses(
  edge: number,
  flame: number,
  edgeWeight: number,
  flameWeight: number
): [number, number] {
  if (flame < edge) {
    const pooled = (edgeWeight * edge + flameWeight * flame) / (edgeWeight + flameWeight)
    return [pooled, pooled]
  }
  return [edge, flame]
}

/** Scale every stress down when one goes past the yield limit of its plate. */
function yieldReduction(p: Parameters, flangeLimit: number, webLimit: number): Parameters {
  const names = Object.keys(p)
  const flangeNames = names.filter((name) => /^sigma_(fc|fe|ffe)_/.test(name))
  const webNames = names.filter((name) => name === 'sigma_wc' || name.startsWith('sigma_we_'))
  const maxFlange = Math.max(...flangeNames.map((name) => Math.abs(p[name])))
  const maxWeb = Math.max(...webNames.map((name) => Math.abs(p[name])))
  const utilization = Math.max(maxFlange / flangeLimit, maxWeb / webLimit, 1)
  for (const name of [...flangeNames, ...webNames]) p[name] *= 1 / utilization
  return p
}

/** Monosymmetric and flame-cut: pooled constants, each plate in equilibrium. */
function monoParameters(record: BuiltUpRecord, g: Geometry): Parameters {
  const fy = positiveYield(record, 'fy_n')
  const p: Parameters = {}
  for (const [side, b] of [
    ['top', g.widthTop],
    ['bot', g.widthBottom]
  ] as const) {
    for (const stem of ['dfc', 'dft', 'dffe', 'dfft'] as const)
      p[`${stem}_${side}`] = MONO[stem] * b
    p[`dfe_${side}`] =
      (b - p[`dfc_${side}`]) / 2 - (p[`dft_${side}`] + p[`dffe_${side}`] + p[`dfft_${side}`])
    if (p[`dfe_${side}`] <= 0) {
      throw new ModelUnavailable('Pooled flange widths leave no compression zone')
    }
    p[`sigma_fc_${side}`] = MONO.sigma_fc * fy
    p[`sigma_ffe_${side}`] = MONO.sigma_ffe * fy
    const [dc, de, df] = [p[`dfc_${side}`], p[`dfe_${side}`], p[`dffe_${side}`]]
    p[`sigma_fe_${side}`] =
      -(dc * p[`sigma_fc_${side}`] + 2 * df * p[`sigma_ffe_${side}`]) / (2 * de)
    ;[p[`sigma_fe_${side}`], p[`sigma_ffe_${side}`]] = orderStresses(
      p[`sigma_fe_${side}`],
      p[`sigma_ffe_${side}`],
      2 * de,
      2 * df
    )
  }
  const d = g.webDepth
  p.dwe_top = p.dwe_bot = MONO.dwe * d
  p.dwt_top = p.dwt_bot = 0
  p.dwc = d - 2 * p.dwe_top
  if (p.dwc <= 0) throw new ModelUnavailable('Pooled web widths leave no compression zone')
  p.sigma_we_top = p.sigma_we_bot = p.sigma_fc_top
  p.sigma_wc = (-(p.dwe_top + p.dwe_bot) * p.sigma_we_top) / p.dwc
  return yieldReduction(p, fy, positiveYield(record, 'fy_nw', fy))
}

/** Skiadopoulos et al. (2027), from the geometry and the material only. */
export function proposedParameters(record: BuiltUpRecord): Parameters {
  const g = geometry(record)
  const symmetry = text(record, 'sym')
  if (symmetry !== 'doubly' && symmetry !== 'mono') {
    throw new ModelUnavailable('Built-up model requires sym=doubly or mono')
  }
  const flame = isFlameCut(record)
  if (symmetry === 'mono') {
    if (!flame) {
      throw new ModelUnavailable(
        'No Skiadopoulos et al. (2027) model calibrated for monosymmetric non-flame-cut sections'
      )
    }
    return monoParameters(record, g)
  }
  if (!isClose(g.widthTop, g.widthBottom) || !isClose(g.tFlangeTop, g.tFlangeBottom)) {
    throw new ModelUnavailable('Doubly symmetric model requires matching flange geometry')
  }
  const config = PROPOSED[flame ? 'doubly_flame' : 'doubly_no_flame']
  const reference = referenceYield(record)
  const b = g.widthTop
  const tf = 0.5 * (g.tFlangeTop + g.tFlangeBottom)
  const d = g.webDepth
  const tw = g.tWeb
  const webArea = d * tw
  const plateArea = webArea + b * (g.tFlangeTop + g.tFlangeBottom)
  const predictors = [webArea / plateArea, g.height, b / (2 * tf), 200000 / reference]
  const design = [
    1,
    ...predictors.map((x, i) => {
      const [lower, upper] = config.bounds[i]
      return (2 * (x - lower)) / (upper - lower) - 1
    })
  ]
  const values: Parameters = { ...config.constant }
  for (const [name, coefficients] of Object.entries(config.linear)) {
    values[name] = coefficients.reduce((sum, c, i) => sum + c * design[i], 0)
  }
  const flangeNames = ['dfc_top_over_b', 'dfe_top_over_b', ...(flame ? ['dffe_top_over_b'] : [])]
  const widths = {
    ...closeWidths(values, flangeNames, config.flangeClosure),
    ...closeWidths(values, ['dwc_over_d', 'dwe_top_over_d'], config.webClosure)
  }
  const p: Parameters = {
    dfc_top: b * widths.dfc_top_over_b,
    dfe_top: b * widths.dfe_top_over_b,
    dffe_top: flame ? b * widths.dffe_top_over_b : 0,
    dwc: d * widths.dwc_over_d,
    dwe_top: d * widths.dwe_top_over_d,
    dft_top: 0,
    dfft_top: 0,
    dwt_top: 0
  }
  const stresses = ['sigma_fc_top', 'sigma_fe_top', 'sigma_wc', ...(flame ? ['sigma_ffe_top'] : [])]
  const weights: Parameters = {
    sigma_fc_top: 2 * tf * p.dfc_top + tw * 2 * p.dwe_top,
    sigma_fe_top: 2 * tf * 2 * p.dfe_top,
    sigma_wc: tw * p.dwc
  }
  if (flame) weights.sigma_ffe_top = 2 * tf * 2 * p.dffe_top
  for (const name of stresses) if (name !== config.equilibrium) p[name] = values[name]
  p[config.equilibrium] =
    -stresses
      .filter((name) => name !== config.equilibrium)
      .reduce((sum, name) => sum + weights[name] * p[name], 0) / weights[config.equilibrium]
  if (flame) {
    ;[p.sigma_fe_top, p.sigma_ffe_top] = orderStresses(
      p.sigma_fe_top,
      p.sigma_ffe_top,
      weights.sigma_fe_top,
      weights.sigma_ffe_top
    )
  } else {
    p.sigma_ffe_top = 0
  }
  for (const stem of [
    'dfc',
    'dfe',
    'dffe',
    'dft',
    'dfft',
    'dwt',
    'dwe',
    'sigma_fc',
    'sigma_fe',
    'sigma_ffe'
  ]) {
    p[`${stem}_bot`] = p[`${stem}_top`]
  }
  p.sigma_we_top = p.sigma_we_bot = p.sigma_fc_top
  const nominalFlange = positiveYield(record, 'fy_n')
  const nominalWeb = positiveYield(record, 'fy_nw', nominalFlange)
  yieldReduction(p, nominalFlange / reference, nominalWeb / reference)
  for (const name of Object.keys(p)) if (name.startsWith('sigma_')) p[name] *= reference
  return p
}

/**
 * The saved QP fit of a built-up record: its named zone widths and stresses
 * (`GET /residual-stress/{id}/qp-parameters`), no transitions. A missing
 * flame-cut tip stress is 0 when its zone has no width.
 */
export function qpFitCurves(record: BuiltUpRecord, qp: Parameters): PlateCurves {
  if (Object.keys(qp).length === 0)
    throw new ModelUnavailable('No saved successful specimen QP fit')
  const profile: Parameters = { ...qp }
  for (const side of ['top', 'bot']) {
    if (profile[`dffe_${side}`] === 0 && profile[`sigma_ffe_${side}`] === undefined) {
      profile[`sigma_ffe_${side}`] = 0
    }
  }
  for (const name of BUILT_UP_QP_COLUMNS) {
    const value = profile[name]
    if (!Number.isFinite(value)) throw new Error(`Nonfinite QP parameter ${name}`)
    if (name.startsWith('d') && value < 0) throw new Error(`Negative QP zone width ${name}`)
  }
  const flame = profile.dffe_top > 0 || profile.dffe_bot > 0
  return piecewiseCurve(profile, geometry(record), flame, false)
}

export function modelCurves(record: BuiltUpRecord, model: BuiltUpModel, qp: Parameters) {
  if (model === 'QP_fit') return qpFitCurves(record, qp)
  const parameters = {
    Proposed_model: proposedParameters,
    Schaper: schaperParameters,
    prEN1993_1_14: prenParameters
  }[model](record)
  const transition = model === 'prEN1993_1_14'
  return piecewiseCurve(parameters, geometry(record), isFlameCut(record) && !transition, transition)
}

/** The curves of every built-up model that can be computed for the record. */
export function builtUpModelCurves(
  record: BuiltUpRecord,
  qp: Parameters
): { model: BuiltUpModel; label: string; curves: PlateCurves }[] {
  return BUILT_UP_MODELS.flatMap((model) => {
    try {
      return [
        { model, label: BUILT_UP_MODEL_LABELS[model], curves: modelCurves(record, model, qp) }
      ]
    } catch (error) {
      // A corrupt saved fit is worth a trace; a model that does not apply is not.
      if (!(error instanceof ModelUnavailable)) console.warn(`${model}:`, error)
      return []
    }
  })
}

// --- Chart series -----------------------------------------------------------------

// One color per curve family, so the F1 and F2 lines of a model pair up.
const MEASURED_F1_COLOR = colorPalette[0]
const MEASURED_F2_COLOR = colorPalette[colorPalette.length - 1]
const MODEL_STYLE: Record<BuiltUpModel, { color: string; width: number; type: string }> = {
  QP_fit: { color: colorPalette[1], width: 2, type: 'solid' },
  Proposed_model: { color: colorPalette[5], width: 3, type: 'solid' },
  Schaper: { color: colorPalette[2], width: 2, type: 'dashed' },
  prEN1993_1_14: { color: colorPalette[6], width: 2, type: 'dashed' }
}

function samePoints(a: Point[], b: Point[]): boolean {
  return a.length === b.length && a.every(([x, y], i) => close12(x, b[i][0]) && close12(y, b[i][1]))
}

function close12(a: number, b: number): boolean {
  return Math.abs(a - b) <= 1e-12 + 1e-12 * Math.abs(b)
}

export interface BuiltUpSeries {
  /** Monosymmetric: one chart per flange. Otherwise both flanges share one. */
  separateFlanges: boolean
  flange1: LineSeriesOption[]
  /** Empty unless `separateFlanges`. */
  flange2: LineSeriesOption[]
  web: LineSeriesOption[]
}

/**
 * The drawer charts of a built-up record: the measured distributions and every
 * model that applies, as the hot-rolled charts draw them (flange x from the
 * middle of the flange, web stress on x and height on y).
 */
export function createBuiltUpLineSeries(
  record: BuiltUpRecord,
  qp: Parameters,
  distributionF1: number[][],
  distributionF2: number[][],
  distributionW1: number[][]
): BuiltUpSeries {
  const separateFlanges = isMonosymmetric(record)
  // A second flange counts only when it was measured on its own (README).
  const twoFlanges = Number(record.flange_nr_data) === 2
  let g: Geometry | undefined
  try {
    g = geometry(record)
  } catch {
    g = undefined
  }
  const half = (plate: 'F1' | 'F2') => (g ? (plate === 'F1' ? g.widthTop : g.widthBottom) / 2 : 0)
  const flangePoints = (plate: 'F1' | 'F2', points: number[][]) =>
    points.map(([x, stress]) => [x - half(plate), stress])
  const measured = i18n.global.t('enum.measuredResidualStresses')
  const measuredStyle = { showSymbol: true, lineStyle: { width: 3 } }

  const flange1: LineSeriesOption[] = []
  const flange2: LineSeriesOption[] = []
  const web: LineSeriesOption[] = []
  if (distributionF1.length) {
    flange1.push({
      ...measuredStyle,
      type: 'line',
      name: measured + (twoFlanges && !separateFlanges ? ' F1' : ''),
      color: MEASURED_F1_COLOR,
      data: flangePoints('F1', distributionF1)
    })
  }
  if (twoFlanges && distributionF2.length) {
    ;(separateFlanges ? flange2 : flange1).push({
      ...measuredStyle,
      type: 'line',
      name: separateFlanges ? measured : i18n.global.t('enum.measuredResidualStressesF2'),
      color: separateFlanges ? MEASURED_F1_COLOR : MEASURED_F2_COLOR,
      data: flangePoints('F2', distributionF2)
    })
  }
  if (distributionW1.length) {
    web.push({
      ...measuredStyle,
      type: 'line',
      name: measured,
      color: MEASURED_F1_COLOR,
      triggerLineEvent: true,
      data: distributionW1.map(([y, stress]) => [stress, y])
    })
  }

  for (const { model, label, curves } of builtUpModelCurves(record, qp)) {
    const style = MODEL_STYLE[model]
    const line = (name: string, data: number[][], type = style.type): LineSeriesOption => ({
      type: 'line',
      name,
      color: style.color,
      lineStyle: { width: style.width, type: type as 'solid' },
      data
    })
    const f1 = flangePoints('F1', curves.F1)
    const f2 = flangePoints('F2', curves.F2)
    if (separateFlanges) {
      flange1.push(line(label, f1))
      flange2.push(line(label, f2))
    } else if (samePoints(curves.F1, curves.F2)) {
      flange1.push(line(label, f1))
    } else {
      flange1.push(line(`${label} F1`, f1), line(`${label} F2`, f2, 'dotted'))
    }
    web.push(
      line(
        label,
        curves.W1.map(([y, stress]) => [stress, y])
      )
    )
  }
  return {
    separateFlanges,
    flange1,
    flange2,
    web: web.map((series) => ({ ...series, encode: { tooltip: [0] } }))
  }
}
