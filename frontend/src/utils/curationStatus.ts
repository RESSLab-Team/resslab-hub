/**
 * The review status of a row (#253), mirror of
 * `backend/resslab_hub/data/curation_status.py`.
 *
 * A submission goes live as `unverified`. A curator checks it later and a
 * small pull request on the data repository flips it to `verified`. The Hub
 * sets the column, never a contributor, so the contribution editor leaves it
 * out (`MANAGED_COLUMNS`).
 */

export const STATUS_COLUMN = 'data_curation_status'
export const VERIFIED = 'verified'
export const UNVERIFIED = 'unverified'

/** Columns in the dictionaries that the Hub fills itself. */
export const MANAGED_COLUMNS: ReadonlySet<string> = new Set([STATUS_COLUMN])

/** The search that hides unverified rows: an exact match (`=`) on the column. */
export const VERIFIED_ONLY_SEARCH = `=${VERIFIED}`

/**
 * True only when the row says `unverified`. A row without the column (an
 * older backend, a database without a status) reads as verified, so nothing
 * is flagged by mistake.
 */
export function isUnverified(row: unknown): boolean {
  if (row == null || typeof row !== 'object') return false
  return (row as Record<string, unknown>)[STATUS_COLUMN] === UNVERIFIED
}

/**
 * The `id` search that shows exactly these rows on a dashboard. One id needs
 * the exact match (`=`), or `B1` would also keep `B10`. Several ids go
 * through the value-in-set match (`,`), which is exact already.
 */
export function idsSearch(ids: readonly string[]): string {
  return ids.length === 1 ? `=${ids[0]}` : ids.join(',')
}
