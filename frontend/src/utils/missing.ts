/**
 * Not reported or not applicable (#427).
 *
 * A number, date or yes/no column stores NULL for both `nr` (the paper didn't
 * give the value) and `na` (the value doesn't exist for this specimen). The
 * record says which one with its `not_reported` list: the names of the columns
 * whose cell was `nr`. A NULL listed there is not reported, any other NULL is
 * not applicable. Text columns keep their own "Not reported" text.
 */

export const NOT_REPORTED = 'NR'
export const NOT_APPLICABLE = 'NA'

/** A record from the API, or a row of the in-browser dataset. */
type MissingRecord = { not_reported?: string[] | null } | Record<string, unknown>

/** True when the record lists `field` as not reported. */
export function isNotReported(record: MissingRecord, field: string): boolean {
  const list = (record as { not_reported?: unknown }).not_reported
  return Array.isArray(list) && list.includes(field)
}

/** `NR` or `NA` for an empty `field` of `record`: the code the filters and the table use. */
export function missingKey(record: MissingRecord, field: string): string {
  return isNotReported(record, field) ? NOT_REPORTED : NOT_APPLICABLE
}
