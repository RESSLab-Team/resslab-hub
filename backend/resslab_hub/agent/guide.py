"""
The agent guide: Markdown pages that tell any AI agent how to turn a
researcher's files into a RESSLab Hub submission, and how to check it with
``POST /agent/validate`` (routers/agent.py, docs/src/contributing-data.md).

Only the method is written by hand (``guide.md``). The rest comes from what
the hub already uses, so the guide can't drift from the checks:

- the folder layout from ``get_args_all`` (uploader) and the response-file
  headers from ``validate_one_file`` (validator);
- the contributor guide and the data dictionary from the database, the same
  rows ``/dictionary`` serves;
- "In the hub now" from the data itself: the range the validator compares
  with, and the text values already in use.
"""

import re
import time
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from logging import exception
from os import path
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import String, func, select
from sqlalchemy.orm import Session

from resslab_hub.data.curation_status import STATUS_COLUMN
from resslab_hub.data.not_reported import NOT_REPORTED_COLUMN
from resslab_hub.data.uploader import Type, get_args_all
from resslab_hub.data.validator import (
    PRIMARY_TYPES,
    TableValidator,
    engine,
    validate_one_file,
)

#: Frontend DatabaseId -> the archive type ``/validate`` takes for it. The
#: frontend has the same map (``CONTRIBUTION_DATABASES``); the backend had
#: none, because ``/validate`` takes the type itself.
DATABASE_TYPES: Dict[str, Type] = {
    "braces": Type.ALL_BRACE,
    "columns": Type.ALL_COLUMN,
    "connections": Type.ALL_CONNECTION,
    "hss": Type.ALL_HSS_COLUMN,
    "ebf": Type.ALL_ECCENTRIC_BRACED_FRAME,
    "cyclic": Type.ALL_MATERIAL,
    "tensile": Type.ALL_TENSILE_COUPON,
    "ductile-fracture": Type.ALL_DUCTILE_FRACTURE,
    "residuals": Type.ALL_RESIDUAL_STRESS,
}

METHOD = Template((Path(__file__).parent / "guide.md").read_text(encoding="utf-8"))

#: A text column with more distinct values than this is free text (names,
#: references): listing them would not help to map a vocabulary.
MAX_LISTED_VALUES = 30
#: Longer values are notes, not a vocabulary.
MAX_LISTED_LENGTH = 60
#: Missing markers, and the words some old rows use for them: never a value
#: to copy.
_MISSING = ("", "na", "nr", "nan", "not applicable", "not reported")
_NUMBER = re.compile(r"^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*$")


@dataclass(frozen=True)
class ResponseFolder:
    #: Archive path of the folder, e.g. ``braces/force_displacement``.
    folder: str
    #: File name pattern, ``<id>.csv`` (``id<id>.csv`` for EBF).
    file_name: str
    #: Headers the validator requires, in its own order.
    columns: Tuple[str, ...]


@dataclass(frozen=True)
class Layout:
    #: The database folder, e.g. ``braces`` or ``material/tensile_coupons``.
    folder: str
    #: Archive path of the main CSV.
    primary_csv: str
    #: ORM model of the main table.
    model: Any
    responses: Tuple[ResponseFolder, ...]


@dataclass(frozen=True)
class Urls:
    #: Where the SPA is served, e.g. ``https://resslab-hub.epfl.ch``.
    site: str
    #: Where the API is reached, ``/api`` included.
    api: str


@lru_cache(maxsize=None)
def layout(database: str) -> Layout:
    """The folder layout ``/validate`` expects for one database."""
    primary_csv = None
    model = None
    responses = []
    for file_type, pattern in get_args_all(DATABASE_TYPES[database], ""):
        if file_type in (Type.DICTIONARY, Type.README):
            continue
        validator = validate_one_file(file_type, pattern)
        if file_type in PRIMARY_TYPES:
            primary_csv = pattern
            model = validator.base_model
        else:
            responses.append(
                ResponseFolder(
                    folder=path.dirname(pattern),
                    file_name=f"{validator.filename_prefix}<id>.csv",
                    columns=tuple(validator.required_columns),
                )
            )
    assert primary_csv is not None, f"No main CSV for {database}"
    return Layout(
        folder=path.dirname(primary_csv),
        primary_csv=primary_csv,
        model=model,
        responses=tuple(responses),
    )


# --- In the hub now ---------------------------------------------------------


def _plain(number) -> str:
    """The way the validator writes a bound in its range warning."""
    return format(Decimal(str(number)).normalize(), "f")


def existing_values(database: str) -> Dict[str, str]:
    """Column -> what the hub already holds, as Markdown for one table cell.

    Numbers: the range the validator compares a new value with (same query,
    same 20-value minimum). Text: the values in use, most frequent first, when
    there are few of them. Empty when the database can't be reached: the
    guide still works without it.
    """
    model = layout(database).model
    found: Dict[str, str] = {}
    for key, (count, minimum, maximum) in TableValidator(model)._range_stats().items():
        found[key] = f"{_plain(minimum)} to {_plain(maximum)} ({count} values)"

    skipped = {"id", STATUS_COLUMN, NOT_REPORTED_COLUMN}
    text_columns = [
        column
        for column in model.__table__.c
        if isinstance(column.type, String) and column.key not in skipped
    ]
    try:
        with Session(engine) as session:
            for column in text_columns:
                count = func.count()
                rows = session.execute(
                    select(column, count)
                    .where(
                        column.is_not(None),
                        func.lower(func.trim(column)).not_in(_MISSING),
                    )
                    .group_by(column)
                    .order_by(count.desc(), column)
                    .limit(MAX_LISTED_VALUES + 1)
                ).all()
                values = list(dict.fromkeys(str(value).strip() for value, _ in rows))
                if (
                    not values
                    or len(values) > MAX_LISTED_VALUES
                    or any(len(value) > MAX_LISTED_LENGTH for value in values)
                    # A text column that holds numbers (some gusset plate
                    # lengths): its values are no vocabulary.
                    or any(_NUMBER.match(value) for value in values)
                ):
                    continue
                found[column.key] = ", ".join(f"`{value}`" for value in values)
    except Exception:
        exception(f"Agent guide: existing values of {database} skipped")
    return found


class ExistingValuesCache:
    """``existing_values`` per database, kept until the data changes.

    The response cache (utils/caching.py) stores JSON only, so the guide keeps
    its own copy, on the same data version and the same lifetime.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, Tuple[str, float, Dict[str, str]]] = {}

    def get(self, database: str, version: str) -> Optional[Dict]:
        entry = self._entries.get(database)
        if entry is None:
            return None
        entry_version, expires, values = entry
        if entry_version != version or time.monotonic() >= expires:
            return None
        return values

    def put(self, database: str, version: str, max_age: int, values: Dict) -> None:
        if max_age > 0:
            self._entries[database] = (version, time.monotonic() + max_age, values)

    def clear(self) -> None:
        self._entries.clear()


# --- Rendering --------------------------------------------------------------


def _cell(text: Any) -> str:
    """Text that fits in one Markdown table cell."""
    return " ".join(str(text or "").split()).replace("|", "\\|")


def _demote(markdown: str) -> str:
    """Two heading levels down, so a README (``#`` title) fits under our ``##``.

    Lines inside fenced code blocks are left alone (a ``#`` there is a shell
    comment or a placeholder, not a heading).
    """
    lines = []
    fenced = False
    for line in markdown.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced and re.match(r"#{1,4} ", line):
            line = "##" + line
        lines.append(line)
    return "\n".join(lines)


def readme_title(readme: Optional[str], fallback: str) -> str:
    """``# Steel braces database`` -> ``Steel braces``."""
    for line in (readme or "").splitlines():
        if line.startswith("# "):
            return re.sub(r"\s+database$", "", line[2:].strip(), flags=re.I)
    return fallback


def readme_summary(readme: Optional[str]) -> str:
    """The first paragraph under the title of a README."""
    paragraph: List[str] = []
    for line in (readme or "").splitlines():
        if line.startswith("#"):
            if paragraph:
                break
            continue
        if not line.strip():
            if paragraph:
                break
            continue
        paragraph.append(line.strip())
    return " ".join(paragraph)


def _method(urls: Urls, database: str, folder: str) -> str:
    return METHOD.substitute(
        api=urls.api,
        database=database,
        folder=folder,
        contribute_url=f"{urls.site}/contribute/new",
    )


def render_index(urls: Urls, readmes: Dict[str, str]) -> str:
    """``GET /agent/guide``: what the hub is, the method, the databases."""
    rows = [
        f"| {_cell(readme_title(readmes.get(database), database))} "
        f"| `{database}` | {_cell(readme_summary(readmes.get(database)))} "
        f"| {urls.api}/agent/guide/{database} |"
        for database in DATABASE_TYPES
    ]
    return "\n\n".join(
        [
            "# RESSLab Hub: guide for AI agents",
            f"RESSLab Hub ({urls.site}) is an open database of tests on "
            "structural steel components, run by the Resilient Steel "
            "Structures Laboratory (RESSLab) at EPFL. Researchers add their "
            "own tests to it. This guide is for an AI agent that helps a "
            "researcher convert their files to the hub template and check "
            "them before they submit.",
            "Find the database of the researcher's tests below, then read its "
            "page. Each database page repeats the method, and adds the folder "
            "layout, the contributor guide and the data dictionary of that "
            "database. That one page is enough to do the work.",
            "## Databases",
            "| Database | Id | What it holds | Guide |\n"
            "| --- | --- | --- | --- |\n" + "\n".join(rows),
            _method(urls, "<database>", "<folder>"),
        ]
    )


def _layout_section(database: str) -> str:
    folders = layout(database)
    root = folders.folder + "/"
    main = folders.primary_csv[len(root) :]
    tree = [root, f"  {main}    main table, one row per test"]
    for response in folders.responses:
        sub = response.folder[len(root) :]
        tree.append(f"  {sub}/{response.file_name}    one file per test")
    parts = [
        "## Folder layout",
        "Build exactly this folder. The names of the folders and of the main "
        "table are fixed. Paths in the check report start with "
        f"`{root}`.",
        "```text\n" + "\n".join(tree) + "\n```",
    ]
    if folders.responses:
        rows = [
            f"| `{response.folder}/` | `{response.file_name}` | "
            + ", ".join(f"`{_cell(column)}`" for column in response.columns)
            + " |"
            for response in folders.responses
        ]
        parts += [
            "| Folder | File name | Required headers (exact text) |\n"
            "| --- | --- | --- |\n" + "\n".join(rows),
            "One file per test, named after the `id` of the test in the main "
            "table. A response file whose name matches no `id` is an error. "
            "Write the required headers only: the hub ignores other columns "
            "(a time column, for example), so leave them out. The contributor "
            "guide below gives the column order, the units, the sign rules, "
            "and which responses each test must have. Numbers only, one row "
            "per sample.",
        ]
    return "\n\n".join(parts)


def _dictionary_section(columns: Sequence[Any], values: Dict[str, str]) -> str:
    rows = [
        "| "
        + " | ".join(
            [
                f"`{_cell(column.name)}`",
                _cell(column.description),
                _cell(column.unit),
                _cell(column.type),
                "no" if column.nullable else "yes",
                _cell(column.example),
                values.get(column.name, "").replace("|", "\\|"),
            ]
        )
        + " |"
        for column in columns
    ]
    return "\n\n".join(
        [
            "## Data dictionary",
            "The main table has these columns, in this order. "
            '"Required" yes means the column needs a real value: `NA` or '
            '`NR` there gives an error or a warning. "In the hub now" gives, '
            "for numbers, the range of the tests already in the hub (a value "
            "far outside it gets a warning) and, for text, the values already "
            "in use, most frequent first.",
            "| Column | Description | Unit | Type | Required | Example "
            "| In the hub now |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows),
        ]
    )


def render_database(
    urls: Urls,
    database: str,
    readme: Optional[str],
    columns: Sequence[Any],
    values: Dict[str, str],
) -> str:
    """``GET /agent/guide/{database}``: everything for one database."""
    title = readme_title(readme, database)
    folder = layout(database).folder
    parts = [
        f"# RESSLab Hub: prepare a submission to the {title} database",
        f"This page is for an AI agent that helps a researcher. It has all "
        f"you need to convert the researcher's files to the template of the "
        f"{title} database of RESSLab Hub ({urls.site}), and to check them. "
        f"The other databases are listed at {urls.api}/agent/guide.",
        _method(urls, database, folder),
        _layout_section(database),
        "## Contributor guide of this database",
        _demote(readme)
        if readme
        else "This database has no contributor guide yet. Use the folder "
        "layout above and the data dictionary below.",
        _dictionary_section(columns, values),
    ]
    return "\n\n".join(parts) + "\n"
