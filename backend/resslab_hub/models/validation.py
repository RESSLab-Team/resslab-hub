"""
Response models for the ``/validate`` endpoint.

The CSV validator already produces structured errors (row, column, value,
message); these models carry that structure to the frontend so it can map each
issue back to a spreadsheet cell instead of re-parsing formatted strings.

The legacy ``error_results`` / ``valid_results`` string arrays are kept
alongside the structured ``results`` list purely for backward compatibility with
the data repository's validation CI, which renders them with ``jq``. They can be
dropped once that workflow is migrated to ``results``.
"""

from typing import List, Optional

from pydantic import BaseModel


class ValidationIssue(BaseModel):
    """A single error or warning, anchored to a cell where possible."""

    #: 0 = file/header-level; N = the Nth data row (1-based, header excluded).
    row: int
    #: Column name, or a structural marker: "headers", "row", "file", or an FK field.
    column: str
    #: The offending value, stringified. ``None`` when there is no cell value.
    value: Optional[str] = None
    message: str


class FileValidationResult(BaseModel):
    """Structured validation outcome for one file in the archive."""

    #: Basename, for display (e.g. ``S1.csv``).
    file: str
    #: Archive-relative path (e.g. ``residual_stresses/QP_Coefficients/S1.csv``).
    #: Disambiguates time-series kinds that share a basename.
    path: str
    valid: bool
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []


class LegacyFileResult(BaseModel):
    """Back-compat shape: flat error/warning strings, as the endpoint used to emit."""

    file: str
    valid: bool
    errors_count: Optional[int] = None
    errors: Optional[List[str]] = None
    warnings: List[str] = []


class ValidationResponse(BaseModel):
    valid: bool
    message: str
    error_count: int
    #: Structured results — the contribution wizard consumes these.
    results: List[FileValidationResult] = []
    #: Legacy string arrays, kept until the data-repo CI is migrated.
    error_results: List[LegacyFileResult] = []
    valid_results: List[LegacyFileResult] = []
