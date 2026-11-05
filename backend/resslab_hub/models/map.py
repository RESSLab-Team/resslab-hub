"""
Response models for the overview map (GET /map/sites).

Written by hand, not generated from the data dictionaries: they describe an
aggregate over every database, not one table.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class MapCategory(str, Enum):
    """
    One value per database. Same names as each router's Component, so the
    frontend can use them as keys everywhere (colours, routes, labels).
    """

    braces = "braces"
    columns = "columns"
    connections = "connections"
    materials = "materials"
    tensile_coupon = "tensile-coupon"
    ductile_fracture = "ductile-fracture"
    residual_stress = "residual-stress"
    hss_column = "hss-column"
    eccentric_braced_frame = "eccentric-braced-frame"


class MapProgram(BaseModel):
    """
    One experimental program at one site: the specimens of one category that
    share a program (or investigator) and a year.
    """

    category: MapCategory
    #: experimental_program, or investigator for braces, HSS columns and EBF
    program: str
    year: Optional[int] = None
    n: int
    reference: Optional[str] = None
    #: link, or url for HSS columns and EBF
    link: Optional[str] = None
    #: one specimen of the program, for the ?specimen=... deep link
    first_id: str
    #: the column the frontend needs to pick the schematic figure
    #: (boundary condition, specimen type, ...). Columns join two with "|".
    figure: Optional[str] = None


class MapSite(BaseModel):
    """
    One place on the map: every specimen whose coordinates round to the same
    two decimals (about 1 km), so a campus with a few points is one site.
    """

    #: "lat,lng" rounded to 2 decimals, the key of frontend/src/assets/map-sites.json
    sid: str
    #: centroid of the raw coordinates, weighted by specimen count
    lat: float
    lng: float
    n: int
    counts: Dict[MapCategory, int]
    #: sorted by n, biggest first
    programs: List[MapProgram]


class MapSites(BaseModel):
    """
    Every site with data, biggest first.
    """

    sites: List[MapSite]
    #: specimens without usable coordinates, not on the map
    skipped: int
