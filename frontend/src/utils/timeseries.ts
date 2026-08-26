import { parseCsv } from '@/utils/csv'
import type { DatabaseId } from '@/utils/navigation'

/**
 * Measured-response files that can accompany a record.
 *
 * Mirrors the subsidiary types the backend expands an `all-*` upload into
 * (`get_args_all` in `backend/resslab_hub/data/uploader.py`) and the column
 * requirements each one is validated against (`validate_one_file` in
 * `backend/resslab_hub/data/validator.py`). The columns of the kinds the
 * backend does not validate yet (EBF, ductile fracture) come from the data
 * repository's READMEs and match every file on disk.
 *
 * Two rules the UI has to respect:
 *  - the file must sit in `directory` inside the archive, and
 *  - its **filename is the foreign key**: `<specimen id>.csv` (see
 *    `fileStemFor`), matched against the `id` column of the primary CSV in
 *    the same archive.
 */
export interface TimeSeriesColumn {
  /** Exact header, as the validator expects it. */
  name: string
  /** Unit of the values, `-` when dimensionless. */
  unit: string
  /**
   * Order of magnitude of the largest |value| seen in the database for this
   * column. A file two decades above or three below it almost always means a
   * unit slip (mrad for rad, Pa for MPa, N for kN); omitted when the column
   * has no natural scale (an index).
   */
  typicalMax?: number
}

export interface TimeSeriesKind {
  /** Stable key, also the i18n suffix under `contribute.timeseries.kind`. */
  key: string
  /** Directory inside the archive, relative to the component root. */
  directory: string
  /** Columns the file must carry, in the order the README documents them. */
  columns: TimeSeriesColumn[]
  /**
   * Expected for every experiment of the database (the primary response the
   * component models are fitted on); the rest is welcome when measured.
   */
  required: boolean
  /** Archive filename stem for a specimen id; `<id>` unless overridden. */
  fileStem?: (id: string) => string
}

const ROTATION = 0.2
const FORCE_KN = 5_000
const MOMENT_KNMM = 1e7
const DISPLACEMENT_MM = 500
const STRESS_MPA = 2_000
const STRAIN = 5

const col = (name: string, unit: string, typicalMax?: number): TimeSeriesColumn => ({
  name,
  unit,
  typicalMax
})

const CHORD_ROTATION = col('Chord Rotation [rads]', 'rad', ROTATION)
const MOMENT = col('Moment [kN-mm]', 'kN·mm', MOMENT_KNMM)
const STORY_DRIFT = col('Total story drift angle (rad)', 'rad', ROTATION)
const ACTUATOR_FORCE = col('Force in the actuator (kN)', 'kN', FORCE_KN)
const SIGMA_TRUE = col('Sigma_true', 'MPa', STRESS_MPA)
const E_TRUE = col('e_true', '-', STRAIN)
const COORDINATE = col('coordinate', 'mm', 1_000)
const RESIDUAL_STRESS = col('residual_stress', 'MPa', STRESS_MPA)
const ELONGATION = col('Elongation [mm]', 'mm', 20)
const LOAD = col('Load [kN]', 'kN', 100)

export const TIME_SERIES_KINDS: Partial<Record<DatabaseId, TimeSeriesKind[]>> = {
  braces: [
    {
      key: 'force_displacement',
      directory: 'braces/force_displacement',
      columns: [col('Displacement [mm]', 'mm', DISPLACEMENT_MM), col('Force [kN]', 'kN', FORCE_KN)],
      required: true
    }
  ],
  columns: [
    {
      key: 'axial_shortening',
      directory: 'columns/axial_shortening_rotation',
      columns: [CHORD_ROTATION, col('Axial Shortening [mm]', 'mm', DISPLACEMENT_MM)],
      required: false
    },
    {
      key: 'moment_strong',
      directory: 'columns/moment_rotation_strong',
      columns: [CHORD_ROTATION, MOMENT],
      required: true
    },
    {
      key: 'moment_weak',
      directory: 'columns/moment_rotation_weak',
      columns: [CHORD_ROTATION, MOMENT],
      required: false
    }
  ],
  connections: [
    {
      key: 'beam',
      directory: 'connections/Beam_moment_rotation',
      columns: [CHORD_ROTATION, MOMENT],
      required: false
    },
    {
      key: 'beam_west',
      directory: 'connections/Beam_moment_rotation_west',
      columns: [CHORD_ROTATION, MOMENT],
      required: false
    },
    {
      key: 'global',
      directory: 'connections/Global',
      columns: [STORY_DRIFT, ACTUATOR_FORCE],
      required: false
    },
    {
      key: 'global_west',
      directory: 'connections/Global_west',
      columns: [STORY_DRIFT, ACTUATOR_FORCE],
      required: false
    },
    {
      key: 'panel_zone',
      directory: 'connections/Panel_zone',
      columns: [
        col('panel zone shear distortion (rad)', 'rad', ROTATION),
        col('panel zone shear force (kN)', 'kN', FORCE_KN)
      ],
      required: false
    }
  ],
  hss: [
    {
      key: 'moment_rotation',
      directory: 'hss_columns/Moment_Rotation',
      columns: [col('rotation (rad)', 'rad', ROTATION), col('moment (kN.m)', 'kN·m', 1_000)],
      required: true
    }
  ],
  cyclic: [
    {
      key: 'stress_strain',
      directory: 'material/cyclic_coupons/stress_strain',
      columns: [E_TRUE, SIGMA_TRUE],
      required: true
    }
  ],
  residuals: [
    {
      key: 'distribution_f1',
      directory: 'residual_stresses/Distributions/Distributions_F1',
      columns: [COORDINATE, RESIDUAL_STRESS],
      required: true
    },
    {
      key: 'distribution_f2',
      directory: 'residual_stresses/Distributions/Distributions_F2',
      columns: [COORDINATE, RESIDUAL_STRESS],
      required: false
    },
    {
      key: 'distribution_w1',
      directory: 'residual_stresses/Distributions/Distributions_W1',
      columns: [COORDINATE, RESIDUAL_STRESS],
      required: true
    },
    {
      key: 'qp_coefficient',
      directory: 'residual_stresses/QP_Coefficients',
      columns: [col('qp_coefficient', 'MPa', 1_000)],
      required: false
    }
  ],
  tensile: [
    {
      key: 'stress_strain',
      directory: 'material/tensile_coupons/stress_strain',
      columns: [E_TRUE, SIGMA_TRUE],
      required: true
    }
  ],
  ebf: [
    {
      key: 'processed_data',
      directory: 'eccentric_braced_frames/processed_data',
      columns: [col('data_ind', '-'), col('gamma_t', 'rad', 1), col('V', 'kN', FORCE_KN)],
      required: true,
      // The repository names these `id<id>.csv` (`processed_data/id74.csv`).
      fileStem: (id) => `id${id}`
    }
  ],
  'ductile-fracture': [
    {
      key: 'force_elongation',
      directory: 'material/ductile_fracture/force_elongation',
      columns: [ELONGATION, LOAD],
      required: true
    },
    {
      key: 'force_elongation_simulation',
      directory: 'material/ductile_fracture/force_elongation_simulation',
      columns: [ELONGATION, LOAD],
      required: false
    },
    {
      key: 'force_radial',
      directory: 'material/ductile_fracture/force_radial',
      columns: [col('Radial elongation [mm]', 'mm', 20), LOAD],
      required: false
    },
    {
      key: 'force_radial_simulation',
      directory: 'material/ductile_fracture/force_radial_simulation',
      columns: [col('Radial elongation [mm]', 'mm', 20), LOAD],
      required: false
    },
    {
      key: 'epeq_simulation',
      directory: 'material/ductile_fracture/equivalent_plastic_strain_elongation_simulation',
      columns: [ELONGATION, col('Equivalent plastic strain', '-', STRAIN)],
      required: false
    },
    {
      key: 'lode_simulation',
      directory: 'material/ductile_fracture/lode_angle_elongation_simulation',
      columns: [ELONGATION, col('Lode angle', '-', 2)],
      required: false
    },
    {
      key: 'triax_simulation',
      directory: 'material/ductile_fracture/triaxiality_elongation_simulation',
      columns: [ELONGATION, col('Triaxiality', '-', 20)],
      required: false
    }
  ]
}

export function timeSeriesKindsFor(database: DatabaseId | null): TimeSeriesKind[] {
  return database ? TIME_SERIES_KINDS[database] ?? [] : []
}

/** The headers a file of this kind must carry. */
export function requiredColumns(kind: TimeSeriesKind): string[] {
  return kind.columns.map((column) => column.name)
}

/** Filename stem (without `.csv`) of a specimen's file of this kind. */
export function fileStemFor(kind: TimeSeriesKind, id: string): string {
  return kind.fileStem ? kind.fileStem(id) : id
}

/**
 * The kinds whose column set the file's headers satisfy, so a bulk drop can
 * tell a file's kind from its content. Several kinds share a header set
 * (`beam` and `beam_west`, the F1/F2/W1 distributions); the caller decides.
 */
export function kindsMatchingHeaders(kinds: TimeSeriesKind[], text: string): TimeSeriesKind[] {
  const headers = new Set(parseCsv(text)[0]?.map((header) => header.trim()) ?? [])
  return kinds.filter(
    (kind) => kind.columns.length > 0 && kind.columns.every((column) => headers.has(column.name))
  )
}

/** What a client-side look at a time-series file found. */
export interface TimeSeriesReport {
  /** Data rows (the header excluded). */
  rows: number
  /** What the server would reject: no data, a missing column, a value that is not a number. */
  errors: string[]
  /** What looks wrong but is the contributor's call: values on the wrong scale. */
  warnings: string[]
  /** Per declared column present in the file. */
  stats: Record<string, { min: number; max: number }>
  /** The first two declared columns (an index for a single-column kind), for the preview. */
  x: number[]
  y: number[]
}

/** Two decades above the database's largest value, or three below it. */
const RANGE_HIGH = 100
const RANGE_LOW = 1 / 1000

function short(value: number): string {
  return String(Number(value.toPrecision(3)))
}

function withUnit(column: TimeSeriesColumn): string {
  const scale = short(column.typicalMax!)
  return column.unit === '-' ? `~${scale}` : `~${scale} ${column.unit}`
}

/**
 * Look at a time-series file the way the server will, plus the sanity checks
 * the server cannot make. Never throws: everything it finds goes into the
 * report, and a file with errors still attaches so the card can say what is
 * wrong with it.
 */
export function checkTimeSeriesFile(kind: TimeSeriesKind, text: string): TimeSeriesReport {
  const report: TimeSeriesReport = { rows: 0, errors: [], warnings: [], stats: {}, x: [], y: [] }
  const parsed = parseCsv(text)
  if (parsed.length < 2) {
    report.errors.push('The file has no data rows.')
    return report
  }
  const data = parsed.slice(1)
  report.rows = data.length

  const headers = parsed[0].map((header) => header.trim())
  const missing = kind.columns.filter((column) => !headers.includes(column.name))
  if (missing.length) {
    report.errors.push(
      `Missing required column(s): ${missing.map((column) => column.name).join(', ')}`
    )
  }

  const values = new Map<string, number[]>()
  for (const column of kind.columns) {
    const index = headers.indexOf(column.name)
    if (index === -1) continue
    const series: number[] = []
    let min = Infinity
    let max = -Infinity
    let flagged = false
    data.forEach((row, offset) => {
      const raw = (row[index] ?? '').trim()
      // Line number in the file, the header being line 1: what a contributor
      // sees when they open the file to fix it.
      const line = offset + 2
      if (raw === '') {
        if (!flagged)
          report.errors.push(`Column "${column.name}" has an empty cell (line ${line}).`)
        flagged = true
        series.push(NaN)
        return
      }
      const value = Number(raw)
      if (!Number.isFinite(value)) {
        if (!flagged) {
          report.errors.push(
            `Column "${column.name}" has a value that is not a number (line ${line}: "${raw}").`
          )
        }
        flagged = true
        series.push(NaN)
        return
      }
      if (value < min) min = value
      if (value > max) max = value
      series.push(value)
    })
    values.set(column.name, series)
    if (min <= max) {
      report.stats[column.name] = { min, max }
      const peak = Math.max(Math.abs(min), Math.abs(max))
      if (column.typicalMax !== undefined) {
        if (peak > column.typicalMax * RANGE_HIGH) {
          report.warnings.push(
            `Values in "${column.name}" reach ${short(peak)}, far above the ${withUnit(
              column
            )} seen in the database. Check the unit.`
          )
        } else if (peak > 0 && peak < column.typicalMax * RANGE_LOW) {
          report.warnings.push(
            `Values in "${column.name}" peak at ${short(peak)}, far below the ${withUnit(
              column
            )} seen in the database. Check the unit.`
          )
        }
      }
    }
  }

  const [first, second] = kind.columns
  const xs = second ? values.get(first?.name ?? '') : data.map((_, index) => index)
  const ys = values.get((second ?? first)?.name ?? '')
  if (xs && ys) {
    for (let index = 0; index < ys.length; index++) {
      const x = xs[index]
      const y = ys[index]
      if (Number.isFinite(x) && Number.isFinite(y)) {
        report.x.push(x)
        report.y.push(y)
      }
    }
  }
  return report
}
