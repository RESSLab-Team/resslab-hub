"""
The contribution editor builds the upload archive from its own copy of the
data-repo layout (``frontend/src/utils/contribution.ts`` for the primary CSV,
``frontend/src/utils/timeseries.ts`` for the time-series directories). The
submission then rejects anything outside ``get_args_all``'s layout with a 400
that the automatic check never showed. Pin the two copies together.
"""

import re
from pathlib import Path

import pytest

from resslab_hub.contributions.submission import _layout_for
from resslab_hub.data.uploader import Type

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src" / "utils"


def _layouts():
    return [_layout_for(t) for t in Type if t.value.startswith("all-")]


def _frontend_values(filename: str, key: str) -> list:
    source = FRONTEND / filename
    if not source.is_file():
        pytest.skip(f"{source} not available")
    return re.findall(rf"{key}: '([^']+)'", source.read_text(encoding="utf-8"))


def test_primary_csv_paths_match_the_uploader():
    primaries = {layout.primary_csv for layout in _layouts()}
    for csv_path in _frontend_values("contribution.ts", "csvPath"):
        assert csv_path in primaries, csv_path


def test_time_series_directories_match_the_uploader():
    curve_dirs = {d for layout in _layouts() for d in layout.curve_dirs}
    for directory in _frontend_values("timeseries.ts", "directory"):
        assert directory in curve_dirs, directory
