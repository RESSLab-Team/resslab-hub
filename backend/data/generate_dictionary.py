"""
Bake the data dictionaries into a single frontend asset.

``generate_model.py`` reads the same ``*_data_dictionary.csv`` files but keeps
only column_name/type/nullable to emit ORM + Pydantic models -- it throws away
the description, symbol, unit and example_value. The contribution wizard needs
those four to render tooltips, units, required markers, template downloads and
client-side validation, and the backend container does not ship the data repo at
runtime. So we emit them once, at codegen time, into a committed JSON asset.

Run via ``make generate-dictionary`` (chained into ``make generate-model`` so the
models and this asset are always regenerated from the same source together).

Output: ``frontend/src/assets/contribute/dictionary.json`` -- an object keyed by
the frontend ``DatabaseId``, each value an ordered list of column descriptors.
"""

import csv
import json
import os
import sys
from typing import Dict, List

# DatabaseId (frontend) -> dictionary CSV path, relative to the data repo root.
# Keys and order mirror CONTRIBUTION_DATABASES in the frontend.
DICTIONARIES = {
    "connections": "connections/connections_data_dictionary.csv",
    "columns": "columns/steel_columns_data_dictionary.csv",
    "braces": "braces/steel_braces_data_dictionary.csv",
    "hss": "hss_columns/hss_columns_data_dictionary.csv",
    "cyclic": "material/cyclic_coupons/steel_material_data_dictionary.csv",
    "residuals": "residual_stresses/residual_stresses_data_dictionary.csv",
    "ebf": "eccentric_braced_frames/eccentric_braced_frames_data_dictionary.csv",
    "tensile": "material/tensile_coupons/tensile_coupons_data_dictionary.csv",
    "ductile-fracture": "material/ductile_fracture/ductile_fracture_data_dictionary.csv",
}


def _read_dictionary(csv_path: str) -> List[dict]:
    columns = []
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("column_name") or "").strip()
            if not name:
                continue
            columns.append(
                {
                    "name": name,
                    "description": (row.get("description") or "").strip(),
                    "symbol": (row.get("symbol") or "").strip(),
                    "unit": (row.get("unit") or "").strip(),
                    "type": (row.get("type") or "String").strip(),
                    "example": (row.get("example_value") or "").strip(),
                    # Matches generate_model.py's nullable parsing exactly.
                    "nullable": (row.get("nullable") or "").strip() == "True",
                }
            )
    return columns


def build(data_repo: str) -> Dict[str, List[dict]]:
    result: Dict[str, List[dict]] = {}
    for database_id, rel_path in DICTIONARIES.items():
        csv_path = os.path.join(data_repo, rel_path)
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Dictionary not found: {csv_path}")
        result[database_id] = _read_dictionary(csv_path)
    return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_dictionary.py <data_repo_dir> <output_json>")
        sys.exit(1)

    data_repo = sys.argv[1]
    output = sys.argv[2]

    dictionary = build(data_repo)

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(dictionary, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {os.path.abspath(output)}")
