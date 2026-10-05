"""
Group specimen rows into map sites. Pure functions, no database, so the
rules are easy to test (routers/map.py feeds them).
"""

from collections import defaultdict
from dataclasses import dataclass
from math import isfinite
from typing import Dict, Iterable, List, Optional, Tuple

from resslab_hub.models.map import MapCategory, MapProgram, MapSite


@dataclass
class ProgramRow:
    """
    One row of the per-category query: the specimens of one program and year
    at one raw coordinate.
    """

    category: MapCategory
    lat: float
    lng: float
    program: Optional[str]
    year: Optional[int]
    n: int
    first_id: str
    reference: Optional[str] = None
    link: Optional[str] = None
    figure: Optional[str] = None


def _fmt(value: float) -> str:
    text = f"{value:.2f}"
    return "0.00" if text == "-0.00" else text


def site_key(lat: float, lng: float) -> str:
    """
    The site id: coordinates rounded to 2 decimals (about 1 km). The data has
    a few points per campus (EPFL has three), this puts them in one site.
    """
    return f"{_fmt(lat)},{_fmt(lng)}"


def usable(lat: Optional[float], lng: Optional[float]) -> bool:
    """
    True when a row can go on the map.
    """
    if lat is None or lng is None:
        return False
    return isfinite(lat) and isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180


def _program_name(row: ProgramRow) -> str:
    for candidate in (row.program, row.reference):
        if candidate and candidate.strip():
            return candidate.strip()
    return "-"


def merge_rows(rows: Iterable[ProgramRow]) -> List[MapSite]:
    """
    Merge the rows of every category into sites, biggest site first.

    Rows of the same site, category, program and year are summed (they come
    from two raw coordinates of one campus). Rows with unusable coordinates
    are ignored, the caller counts them as skipped.
    """
    # sid -> (category, program, year) -> merged program
    programs: Dict[str, Dict[Tuple[MapCategory, str, Optional[int]], MapProgram]]
    programs = defaultdict(dict)
    # sid -> [sum lat * n, sum lng * n, n]
    centre: Dict[str, List[float]] = defaultdict(lambda: [0.0, 0.0, 0])

    for row in rows:
        if row.n <= 0 or not usable(row.lat, row.lng):
            continue
        sid = site_key(row.lat, row.lng)
        acc = centre[sid]
        acc[0] += row.lat * row.n
        acc[1] += row.lng * row.n
        acc[2] += row.n

        name = _program_name(row)
        key = (row.category, name, row.year)
        known = programs[sid].get(key)
        if known is None:
            programs[sid][key] = MapProgram(
                category=row.category,
                program=name,
                year=row.year,
                n=row.n,
                reference=row.reference or None,
                link=row.link or None,
                first_id=row.first_id,
                figure=row.figure or None,
            )
        else:
            known.n += row.n
            known.first_id = min(known.first_id, row.first_id)
            known.reference = known.reference or row.reference or None
            known.link = known.link or row.link or None
            known.figure = known.figure or row.figure or None

    sites = []
    for sid, by_key in programs.items():
        lat_sum, lng_sum, n = centre[sid]
        counts: Dict[MapCategory, int] = defaultdict(int)
        for program in by_key.values():
            counts[program.category] += program.n
        sites.append(
            MapSite(
                sid=sid,
                lat=round(lat_sum / n, 4),
                lng=round(lng_sum / n, 4),
                n=int(n),
                counts=dict(counts),
                programs=sorted(
                    by_key.values(),
                    key=lambda p: (-p.n, p.category.value, p.program, p.year or 0),
                ),
            )
        )
    sites.sort(key=lambda s: (-s.n, s.sid))
    return sites
