/**
 * Typed contract for the `POST /validate` response.
 *
 * The backend declares these shapes as Pydantic models, but the OpenAPI 3.1
 * schema they produce is generated as untyped `any` by the current
 * openapi-generator. These interfaces mirror
 * `backend/resslab_hub/models/validation.py` so the frontend keeps real types;
 * `isValidationResponse` guards the cast at the network boundary.
 */

/** A single error or warning, anchored to a cell where possible. */
export interface ValidationIssue {
  /** 0 = file/header-level; N = the Nth data row (1-based, header excluded). */
  row: number
  /** Column name, or a structural marker: `headers`, `row`, `file`, or an FK field. */
  column: string
  /** The offending value, stringified; `null` when there is no cell value. */
  value: string | null
  message: string
}

/** Structured validation outcome for one file in the archive. */
export interface FileValidationResult {
  /** Basename, for display. */
  file: string
  /** Archive-relative path; disambiguates time-series kinds sharing a basename. */
  path: string
  valid: boolean
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
}

export interface ValidationResponse {
  valid: boolean
  message: string
  error_count: number
  /** Structured per-file results — the primary payload. */
  results: FileValidationResult[]
  /** @deprecated legacy string arrays, retained for the data-repo CI. */
  error_results?: unknown[]
  /** @deprecated legacy string arrays, retained for the data-repo CI. */
  valid_results?: unknown[]
}

export function isValidationResponse(data: unknown): data is ValidationResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'valid' in data &&
    'results' in data &&
    Array.isArray((data as { results: unknown }).results)
  )
}
