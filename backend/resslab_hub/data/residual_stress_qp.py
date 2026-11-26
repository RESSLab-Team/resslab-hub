"""The two formats of a residual stress QP coefficient file (#228).

``residual_stresses/QP_Coefficients/<id>.csv`` holds the saved fit of one
record, in one of two formats (README of ``residual_stresses/``):

- hot-rolled: one column ``qp_coefficient`` and four rows, the coefficients
  c1 to c4 of the quadratic flange and web distributions;
- built-up: one header row of the 18 names below and one data row, the zone
  widths (mm) and stresses (MPa) of a piecewise constant fit. ``sigma_ffe_top``
  and ``sigma_ffe_bot`` are ``NA`` when the flange has no flame-cut tip zone
  (``dffe_top`` or ``dffe_bot`` is 0).

Both go in the same table, ``residual_stress_qp_coefficient``: the hot-rolled
rows have no ``name``, the built-up rows carry the header as ``name``. The
uploader, the validator and the data import script share these names.
"""

QP_COEFFICIENT_COLUMN = "qp_coefficient"

# Rows of a hot-rolled file, after the header: c1, c2, c3, c4.
HOT_ROLLED_QP_ROWS = 4

BUILT_UP_QP_COLUMNS = (
    "dfc_top",
    "dfe_top",
    "dffe_top",
    "sigma_fc_top",
    "sigma_fe_top",
    "sigma_ffe_top",
    "dwc",
    "dwe_top",
    "dwe_bot",
    "sigma_wc",
    "sigma_we_top",
    "sigma_we_bot",
    "dfc_bot",
    "dfe_bot",
    "dffe_bot",
    "sigma_fc_bot",
    "sigma_fe_bot",
    "sigma_ffe_bot",
)

# A flame-cut tip stress may be NA, but only when its zone has no width.
OPTIONAL_TIP_STRESS = {"sigma_ffe_top": "dffe_top", "sigma_ffe_bot": "dffe_bot"}

# Missing markers of a built-up cell (the data conventions, any case).
MISSING_MARKERS = {"NA", "NR"}


def has_built_up_columns(headers) -> bool:
    """Whether the headers carry the 18 built-up names (in any order)."""
    return set(BUILT_UP_QP_COLUMNS) <= {header.strip() for header in headers}


def built_up_values(row: dict) -> dict:
    """The named values of a built-up data row, without the missing ones.

    ``row`` maps each of the 18 names to its cell. A missing cell (``NA``,
    ``NR`` or empty) is left out, so the table only holds real numbers.
    """
    values = {}
    for name in BUILT_UP_QP_COLUMNS:
        cell = (row.get(name) or "").strip()
        if cell == "" or cell.upper() in MISSING_MARKERS:
            continue
        values[name] = cell
    return values
