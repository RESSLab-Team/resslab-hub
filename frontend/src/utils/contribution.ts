import {
  BraceField,
  ColumnField,
  ConnectionField,
  DuctileFractureField,
  EccentricBracedFrameField,
  HSSColumnField,
  MaterialField,
  ResidualStressField,
  TensileCouponField,
  Type
} from '@/backend'
import i18n from '@/plugins/i18n'
import type { DatabaseId } from '@/utils/navigation'

/**
 * Columns exposed by the generated `*Field` constants that are SQLAlchemy
 * `column_property` expressions rather than real table columns. The backend
 * validator compares CSV headers against `__table__.c`, so including these
 * would trip its "unexpected columns" warning.
 *
 * Everything matching `_count` is a relationship row-count; the rest are
 * derived values (see `backend/resslab_hub/models/database/*.py`).
 */
const DERIVED_COLUMNS: Partial<Record<DatabaseId, string[]>> = {
  columns: ['built_up'],
  residuals: ['h_over_b'],
  cyclic: ['type', 'year']
}

/**
 * Real table columns the generated client cannot express.
 *
 * `Brace._8t` is declared with a leading underscore, which Pydantic treats as a
 * private attribute — so it is absent from the API schema, from `openapi.json`
 * and from `BraceField`. The validator still requires it in the CSV header
 * (it compares against `__table__.c`), so omitting it fails every braces
 * submission with "Missing required columns: _8t". Drop this entry once the
 * data dictionary renames the column.
 */
const UNEXPOSED_COLUMNS: Partial<Record<DatabaseId, string[]>> = {
  braces: ['_8t']
}

function columnsOf(fields: Record<string, string>, database: DatabaseId): string[] {
  const derived = DERIVED_COLUMNS[database] ?? []
  return [
    // The generated constants repeat a few values under different keys.
    ...new Set(Object.values(fields)),
    ...(UNEXPOSED_COLUMNS[database] ?? [])
  ].filter((column) => !column.endsWith('_count') && !derived.includes(column))
}

export interface ContributionDatabase {
  /** Value for the `type` query parameter of `POST /validate`. */
  type: Type
  /** Path of the primary CSV inside the uploaded archive. */
  csvPath: string
  /** Table columns, in the order the CSV header will list them. */
  columns: string[]
  /** i18n namespace holding this database's field labels. */
  namespace: string
  /**
   * The backend's `validate_one_file` has no branch for these types and raises
   * `NotImplementedError`, which surfaces as a 500. Skip the request instead.
   */
  qualityCheckSupported: boolean
}

export const CONTRIBUTION_DATABASES: Record<DatabaseId, ContributionDatabase> = {
  connections: {
    type: Type.AllConnections,
    csvPath: 'connections/connections.csv',
    columns: columnsOf(ConnectionField, 'connections'),
    namespace: 'connection',
    qualityCheckSupported: true
  },
  columns: {
    type: Type.AllColumns,
    csvPath: 'columns/steel_columns.csv',
    columns: columnsOf(ColumnField, 'columns'),
    namespace: 'column',
    qualityCheckSupported: true
  },
  braces: {
    type: Type.AllBraces,
    csvPath: 'braces/steel_braces.csv',
    columns: columnsOf(BraceField, 'braces'),
    namespace: 'brace',
    qualityCheckSupported: true
  },
  hss: {
    type: Type.AllHssColumns,
    csvPath: 'hss_columns/hss_columns.csv',
    columns: columnsOf(HSSColumnField, 'hss'),
    namespace: 'hss',
    qualityCheckSupported: true
  },
  cyclic: {
    type: Type.AllMaterial,
    csvPath: 'material/cyclic_coupons/steel_material.csv',
    columns: columnsOf(MaterialField, 'cyclic'),
    namespace: 'material',
    qualityCheckSupported: true
  },
  residuals: {
    type: Type.AllResidualStresses,
    csvPath: 'residual_stresses/residual_stresses.csv',
    columns: columnsOf(ResidualStressField, 'residuals'),
    namespace: 'residual',
    qualityCheckSupported: true
  },
  ebf: {
    type: Type.AllEccentricBracedFrames,
    csvPath: 'eccentric_braced_frames/eccentric_braced_frames.csv',
    columns: columnsOf(EccentricBracedFrameField, 'ebf'),
    namespace: 'ebf',
    qualityCheckSupported: false
  },
  tensile: {
    type: Type.AllTensileCoupons,
    csvPath: 'material/tensile_coupons/tensile_coupons.csv',
    columns: columnsOf(TensileCouponField, 'tensile'),
    namespace: 'tensile_coupon',
    qualityCheckSupported: false
  },
  'ductile-fracture': {
    type: Type.AllDuctileFractures,
    csvPath: 'material/ductile_fracture/ductile_fracture.csv',
    columns: columnsOf(DuctileFractureField, 'ductile-fracture'),
    namespace: 'ductile_fracture',
    qualityCheckSupported: false
  }
}

/** `f_yn` → `F yn`; a readable fallback when a column has no translation. */
function prettify(column: string): string {
  const spaced = column.replace(/_/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

/**
 * Field labels come from the per-database i18n dictionaries used by the data
 * tables, which cover only the columns those tables display.
 */
export function fieldLabel(database: DatabaseId, column: string): string {
  const key = `${CONTRIBUTION_DATABASES[database].namespace}.${column}`
  return i18n.global.te(key) ? i18n.global.t(key) : prettify(column)
}

function escapeCsv(value: string): string {
  return /[",\r\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value
}

/**
 * Serialize the form into a one-row CSV.
 *
 * Blank fields become `NR` ("not reported"), which the validator skips — an
 * empty string would instead fail every numeric and date check, burying the
 * real problems under noise.
 */
export function buildCsv(database: DatabaseId, values: Record<string, string>): string {
  const { columns } = CONTRIBUTION_DATABASES[database]
  const row = columns.map((column) => escapeCsv(values[column]?.trim() || 'NR'))
  return `${columns.map(escapeCsv).join(',')}\n${row.join(',')}\n`
}
