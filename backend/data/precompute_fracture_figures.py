"""Draw the per-specimen geometry figure of every ductile-fracture entry.

Each row of ``<data_repo>/material/ductile_fracture/ductile_fracture.csv``
becomes ``<id>.svg`` under
``frontend/public/img/ductile-fracture/figures/``, which the specimen drawer
shows (``getDuctileFractureFigure`` in ``frontend/src/utils/component.ts``).

Unlike the SEM images these are a few kB of vector line work, so they are
committed rather than served from the CDN. Rerun this after the data repo
gains specimens or changes their nominal dimensions, and commit the result.

Usage::

    make precompute-fracture-figures            # from backend/
    python data/precompute_fracture_figures.py ../../resslab-hub-data
    python data/precompute_fracture_figures.py <data-repo> <output-dir>
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import List

from fracture_figures_lib import render_specimen_svg

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "public"
    / "img"
    / "ductile-fracture"
    / "figures"
)


def main(argv: List[str]) -> int:
    if not 2 <= len(argv) <= 3:
        print(
            f"Usage: python {argv[0]} <path-to-resslab-hub-data> [output-dir]",
            file=sys.stderr,
        )
        return 2

    data_root = Path(argv[1]).resolve()
    csv_path = data_root / "material" / "ductile_fracture" / "ductile_fracture.csv"
    if not csv_path.is_file():
        print(f"Data file not found: {csv_path}", file=sys.stderr)
        return 1

    output_dir = Path(argv[2]).resolve() if len(argv) == 3 else DEFAULT_OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)

    # utf-8-sig: the data repo's CSVs carry a BOM, which would otherwise end up
    # glued to the first column name.
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    drawn = 0
    skipped = []
    for row in rows:
        specimen_id = (row.get("id") or "").strip()
        if not specimen_id:
            continue
        try:
            svg = render_specimen_svg(row)
        except ValueError as error:
            skipped.append(f"{specimen_id}: {error}")
            continue
        (output_dir / f"{specimen_id}.svg").write_text(svg, encoding="utf-8")
        drawn += 1

    print(f"Wrote {drawn} figure(s) to {output_dir}")
    for message in skipped:
        print(f"  skipped {message}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main([sys.argv[0]] + sys.argv[1:]))
