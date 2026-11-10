"""Which values of a row were "not reported" (#427), a column the Hub fills.

The CSVs separate `nr` (not reported: the paper didn't give the value) from
`na` (not applicable: the value doesn't exist for this specimen). A text
column keeps the difference as text. A number, date or yes/no column can only
store NULL, so the uploader also writes the names of these columns whose cell
was `nr` into `not_reported`, a list per row. A NULL whose column is in the
list is not reported, any other NULL is not applicable.

A blank cell counts as not reported too: the contribution flow writes a blank
cell as `NR` when it submits a batch.

Contributors never send this column, so the validator does not require it.
"""

from typing import List

from sqlalchemy import String

NOT_REPORTED_COLUMN = "not_reported"


def is_not_reported(value: str) -> bool:
    """True for a cell that says the value was not reported."""
    return value == "" or value.upper() == "NR"


def not_reported_columns(model, headers: List[str], row: List[str]) -> List[str]:
    """The non-text columns of `model` whose cell in `row` is `nr` or blank.

    In model order. A column with no header in the file is left out: the file
    says nothing about it.
    """
    names = []
    for column in model.__table__.c:
        if isinstance(column.type, String) or column.key not in headers:
            continue
        index = headers.index(column.key)
        value = row[index] if index < len(row) else ""
        if is_not_reported(value):
            names.append(column.key)
    return names
