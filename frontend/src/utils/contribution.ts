import { Type } from '@/backend'
import i18n from '@/plugins/i18n'
import { dictionaryFor } from '@/utils/dictionary'
import type { DatabaseId } from '@/utils/navigation'

export interface ContributionDatabase {
  /** Value for the `type` query parameter of `POST /validate`. */
  type: Type
  /** Path of the primary CSV inside the uploaded archive. */
  csvPath: string
  /** i18n namespace holding this database's field labels. */
  namespace: string
  /**
   * The backend's `validate_one_file` has no branch for these types and raises
   * `NotImplementedError`, which surfaces as a 500. Skip the request instead.
   */
  qualityCheckSupported: boolean
}

const DATABASE_META: Record<DatabaseId, ContributionDatabase> = {
  connections: {
    type: Type.AllConnections,
    csvPath: 'connections/connections.csv',
    namespace: 'connection',
    qualityCheckSupported: true
  },
  columns: {
    type: Type.AllColumns,
    csvPath: 'columns/steel_columns.csv',
    namespace: 'column',
    qualityCheckSupported: true
  },
  braces: {
    type: Type.AllBraces,
    csvPath: 'braces/steel_braces.csv',
    namespace: 'brace',
    qualityCheckSupported: true
  },
  hss: {
    type: Type.AllHssColumns,
    csvPath: 'hss_columns/hss_columns.csv',
    namespace: 'hss',
    qualityCheckSupported: true
  },
  cyclic: {
    type: Type.AllMaterial,
    csvPath: 'material/cyclic_coupons/steel_material.csv',
    namespace: 'material',
    qualityCheckSupported: true
  },
  residuals: {
    type: Type.AllResidualStresses,
    csvPath: 'residual_stresses/residual_stresses.csv',
    namespace: 'residual',
    qualityCheckSupported: true
  },
  ebf: {
    type: Type.AllEccentricBracedFrames,
    csvPath: 'eccentric_braced_frames/eccentric_braced_frames.csv',
    namespace: 'ebf',
    qualityCheckSupported: false
  },
  tensile: {
    type: Type.AllTensileCoupons,
    csvPath: 'material/tensile_coupons/tensile_coupons.csv',
    namespace: 'tensile_coupon',
    qualityCheckSupported: false
  },
  'ductile-fracture': {
    type: Type.AllDuctileFractures,
    csvPath: 'material/ductile_fracture/ductile_fracture.csv',
    namespace: 'ductile_fracture',
    qualityCheckSupported: false
  }
}

export interface ContributionDatabaseConfig extends ContributionDatabase {
  /** Table columns, in the order the CSV header will list them (dictionary order). */
  columns: string[]
}

/**
 * Per-database contribution config. Columns come from the baked data dictionary
 * — the same source that generates the ORM/validator, so they match the
 * validator's `__table__.c` exactly (no more `_8t`/`_count`/derived fixups).
 */
export const CONTRIBUTION_DATABASES = Object.fromEntries(
  (Object.keys(DATABASE_META) as DatabaseId[]).map((id) => [
    id,
    { ...DATABASE_META[id], columns: dictionaryFor(id).map((column) => column.name) }
  ])
) as Record<DatabaseId, ContributionDatabaseConfig>

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

export function escapeCsv(value: string): string {
  return /[",\r\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value
}

/**
 * Serialize the experiments into a CSV, one data row per experiment.
 *
 * Blank fields become `NR` ("not reported"), which the validator skips — an
 * empty string would instead fail every numeric and date check, burying the
 * real problems under noise.
 */
export function buildCsv(database: DatabaseId, rows: Array<Record<string, string>>): string {
  const { columns } = CONTRIBUTION_DATABASES[database]
  const header = columns.map(escapeCsv).join(',')
  const body = rows
    .map((cells) => columns.map((column) => escapeCsv(cells[column]?.trim() || 'NR')).join(','))
    .join('\n')
  return `${header}\n${body}\n`
}
