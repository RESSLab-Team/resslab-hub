import { Type } from '@/backend'
import i18n from '@/plugins/i18n'
import type { DatabaseId } from '@/utils/navigation'

export interface ContributionDatabase {
  /** Value for the `type` query parameter of `POST /validate`. */
  type: Type
  /** Path of the primary CSV inside the uploaded archive. */
  csvPath: string
  /** i18n namespace holding this database's field labels. */
  namespace: string
  /**
   * Whether `POST /validate` knows this database. Every database has a
   * validator since resslab-hub#243, so this is true everywhere today; it
   * stays as the switch for a new tab whose validator is not written yet
   * (`validate_one_file` raises `NotImplementedError`, which surfaces as a
   * 500, so the frontend must skip the request rather than send it).
   */
  qualityCheckSupported: boolean
}

export const CONTRIBUTION_DATABASES: Record<DatabaseId, ContributionDatabase> = {
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
    qualityCheckSupported: true
  },
  tensile: {
    type: Type.AllTensileCoupons,
    csvPath: 'material/tensile_coupons/tensile_coupons.csv',
    namespace: 'tensile_coupon',
    qualityCheckSupported: true
  },
  'ductile-fracture': {
    type: Type.AllDuctileFractures,
    csvPath: 'material/ductile_fracture/ductile_fracture.csv',
    namespace: 'ductile_fracture',
    qualityCheckSupported: true
  }
}

/** Base of the data repository on GitHub, where the per-database guides live. */
export const DATA_REPOSITORY_URL = 'https://github.com/RESSLab-Team/resslab-hub-data'

/**
 * The README next to the database's primary CSV in the data repository: it
 * explains the identifier convention, the expected response files (folder,
 * headers, units) and how to submit. Written by the researchers, so it is
 * linked rather than copied.
 */
export function contributionGuideUrl(database: DatabaseId): string {
  const path = CONTRIBUTION_DATABASES[database].csvPath
  const directory = path.slice(0, path.lastIndexOf('/'))
  return `${DATA_REPOSITORY_URL}/blob/main/${directory}/README.md`
}

/** `f_yn` → `F yn`; a readable fallback when a column has no translation. */
export function prettify(column: string): string {
  const spaced = column.replace(/_/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

/**
 * The name to show for a column outside the contribution editor (specimen
 * drawer, curation panels): its translation, else its dictionary symbol, else
 * the prettified column name (#328). The translations come from the
 * per-database i18n dictionaries of the data tables, which cover only the
 * columns those tables display.
 *
 * The symbol can carry `<sub>`/`<sup>` markup, so the result must go through
 * `TextSubscript` (or `stripSubSup()` for a `title` attribute), never a bare
 * `{{ }}`. Where the contributor types the CSV header, show the raw column
 * name instead.
 */
export function fieldDisplay(database: DatabaseId, column: string, symbol?: string): string {
  const key = `${CONTRIBUTION_DATABASES[database].namespace}.${column}`
  if (i18n.global.te(key)) return i18n.global.t(key)
  const trimmed = symbol?.trim()
  // Some dictionaries write LaTeX or code (`f_{y,n}`, `\varepsilon_y`, `K_p`
  // for nine PID gains): not readable as a label, keep the prettified name.
  if (trimmed && !/[_\\{}]/.test(trimmed)) return trimmed
  return prettify(column)
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
export function buildCsv(columns: string[], rows: Array<Record<string, string>>): string {
  const header = columns.map(escapeCsv).join(',')
  const body = rows
    .map((cells) => columns.map((column) => escapeCsv(cells[column]?.trim() || 'NR')).join(','))
    .join('\n')
  return `${header}\n${body}\n`
}
