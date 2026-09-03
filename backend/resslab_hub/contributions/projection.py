"""
Where a contribution's files live, and how to read one back from its branch.

A submission is not stored anywhere: the branch on the data repository is the
whole record (epic #255). This module holds what the submit path and the read
paths agree on, so the review screen, the edit step and the submit flow all
see a submission the same way:

- the type's own directories, the only places a submission may write,
- the branch name, which says which database a submission targets,
- the changed files, classified against that layout,
- the submitted rows: the head-CSV rows whose id is absent from the base.
"""

from dataclasses import dataclass, field
from os import path
from typing import List, Optional, Tuple

from resslab_hub.data.common import SAFE_ID_PATTERN
from resslab_hub.data.uploader import Type, get_args_all
from resslab_hub.data.validator import ValidationResult
from resslab_hub.models.curation import CurationFile


class SubmissionError(Exception):
    """A submission problem with a transport status and a human-readable detail."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class SubmissionValidationFailed(Exception):
    """Server-side re-validation found errors; carries the full results."""

    def __init__(self, results: List[ValidationResult]):
        super().__init__("Validation failed")
        self.results = results


@dataclass
class _Layout:
    """Where this type's files are allowed to live, from the uploader map."""

    primary_csv: str
    curve_dirs: List[str] = field(default_factory=list)
    dictionary_csvs: List[str] = field(default_factory=list)


def _layout_for(input_type: Type) -> _Layout:
    primary_csv = None
    curve_dirs = []
    dictionary_csvs = []
    for arg_type, pattern in get_args_all(input_type, ""):
        normalized = pattern.lstrip("/")
        if arg_type is Type.DICTIONARY:
            dictionary_csvs.append(normalized)
        elif normalized.endswith("*.csv"):
            curve_dirs.append(path.dirname(normalized))
        elif primary_csv is None:
            primary_csv = normalized
    if primary_csv is None:
        raise SubmissionError(400, f"Type {input_type.value} has no primary CSV.")
    return _Layout(primary_csv, curve_dirs, dictionary_csvs)


def _type_slug(input_type: Type) -> str:
    return input_type.value.removeprefix("all-")


def type_for_branch(branch: str) -> Optional[Type]:
    """``contrib/<type_slug>/<name>`` -> the uploader Type, else None."""
    parts = branch.split("/")
    if len(parts) < 3 or parts[0] != "contrib":
        return None
    try:
        return Type("all-" + parts[1])
    except ValueError:
        return None


def classify_files(files: List[dict], input_type: Type) -> List[CurationFile]:
    """Classify a pull request's changed files against the type's layout."""
    layout = _layout_for(input_type)
    slug = _type_slug(input_type)
    classified = []
    for file in files:
        rel = file["path"]
        directory, filename = path.split(rel)
        stem = path.splitext(filename)[0]
        if rel == layout.primary_csv:
            kind = CurationFile(path=rel, kind="primary")
        elif (
            directory in layout.curve_dirs
            and filename.endswith(".csv")
            and SAFE_ID_PATTERN.fullmatch(stem)
        ):
            kind = CurationFile(
                path=rel,
                kind="timeseries",
                timeseries_dir=directory,
                experiment_id=stem,
            )
        elif directory == f"contributions/{slug}" and filename.endswith(".json"):
            kind = CurationFile(path=rel, kind="provenance")
        else:
            kind = CurationFile(path=rel, kind="other")
        classified.append(kind)
    return classified


def split_batch(
    head_header: List[str], head_rows: List[List[str]], base_ids: set
) -> Tuple[List[List[str]], List[List[str]]]:
    """Split the branch's CSV rows into (already in the base, submitted here).

    Keyed by id and by column name, so it survives CRLF, a different column
    order and legacy columns. Rows with no id stay on the base side: they are
    not something this submission can claim.
    """
    id_index = head_header.index("id")
    kept: List[List[str]] = []
    batch: List[List[str]] = []
    for row in head_rows:
        row_id = row[id_index].strip() if id_index < len(row) else ""
        (batch if row_id and row_id not in base_ids else kept).append(row)
    return kept, batch
