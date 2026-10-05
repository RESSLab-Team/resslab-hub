"""
Handle /map requests: one record per site for the home overview map.
"""

from dataclasses import dataclass
from typing import Any, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import Integer, String, cast, func, null, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.column import ColumnEntity
from resslab_hub.models.database.connection import Connection
from resslab_hub.models.database.ductile_fracture import DuctileFracture
from resslab_hub.models.database.eccentric_braced_frame import EccentricBracedFrame
from resslab_hub.models.database.hss_column import HSSColumn
from resslab_hub.models.database.material import Material
from resslab_hub.models.database.residual_stress import ResidualStress
from resslab_hub.models.database.tensile_coupon import TensileCoupon
from resslab_hub.models.map import MapCategory, MapSites
from resslab_hub.utils.database import get_session
from resslab_hub.utils.map_sites import ProgramRow, merge_rows, usable

router = APIRouter(
    prefix="/map",
    tags=["map"],
)


@dataclass
class _Source:
    """
    Where one category keeps what the map needs. The columns are not named
    the same in every table (investigator or experimental_program, date or
    year, link or url), so each table says which one to read.
    """

    category: MapCategory
    table: Any
    program: Any
    year: Any
    link: Any
    figure: Optional[Any] = None


_SOURCES = [
    _Source(
        MapCategory.braces,
        Brace,
        Brace.investigator,
        Brace.date,
        Brace.link,
        Brace.boundary_condition,
    ),
    _Source(
        MapCategory.columns,
        ColumnEntity,
        ColumnEntity.experimental_program,
        ColumnEntity.date,
        ColumnEntity.link,
        # One row gives both values, so the pair always matches a real specimen.
        func.concat(ColumnEntity.axis_of_bending, "|", ColumnEntity.boundary_condition),
    ),
    _Source(
        MapCategory.connections,
        Connection,
        Connection.experimental_program,
        Connection.date,
        Connection.link,
        Connection.specimen_type,
    ),
    _Source(
        MapCategory.materials,
        Material,
        Material.experimental_program,
        func.extract("year", Material.date),
        Material.link,
    ),
    _Source(
        MapCategory.tensile_coupon,
        TensileCoupon,
        TensileCoupon.experimental_program,
        TensileCoupon.year,
        TensileCoupon.link,
    ),
    _Source(
        MapCategory.ductile_fracture,
        DuctileFracture,
        DuctileFracture.experimental_program,
        DuctileFracture.date,
        DuctileFracture.link,
        DuctileFracture.specimen_type,
    ),
    _Source(
        MapCategory.residual_stress,
        ResidualStress,
        ResidualStress.experimental_program,
        ResidualStress.date,
        ResidualStress.link,
    ),
    _Source(
        MapCategory.hss_column,
        HSSColumn,
        HSSColumn.investigator,
        HSSColumn.date,
        HSSColumn.url,
        HSSColumn.test_configuration,
    ),
    _Source(
        MapCategory.eccentric_braced_frame,
        EccentricBracedFrame,
        EccentricBracedFrame.investigator,
        EccentricBracedFrame.year,
        EccentricBracedFrame.url,
        EccentricBracedFrame.l_confi,
    ),
]


def _float(value: Any) -> Optional[float]:
    return None if value is None else float(value)


async def _rows(session: AsyncSession, source: _Source) -> tuple:
    """
    The program rows of one category, and how many specimens have no
    coordinates.
    """
    table = source.table
    lat, lng = table.latitude, table.longitude
    # Not labelled "year": tensile coupons and EBF have a real column of that
    # name, and GROUP BY would pick the column over the label.
    year = cast(source.year, Integer)
    figure = (
        func.min(source.figure)
        if source.figure is not None
        else cast(null(), String)  # min(NULL) is an error in Postgres
    )
    result = await session.execute(
        select(
            lat,
            lng,
            source.program,
            year.label("map_year"),
            func.count(),
            func.min(table.id),
            func.min(table.reference),
            func.min(source.link),
            figure,
        )
        .where(lat.isnot(None), lng.isnot(None))
        .group_by(lat, lng, source.program, year)
    )
    rows = []
    skipped = 0
    for r_lat, r_lng, program, r_year, n, first_id, reference, link, fig in result:
        f_lat, f_lng = _float(r_lat), _float(r_lng)
        if not usable(f_lat, f_lng):
            skipped += n
            continue
        rows.append(
            ProgramRow(
                category=source.category,
                lat=f_lat,
                lng=f_lng,
                program=program,
                year=None if r_year is None else int(r_year),
                n=n,
                first_id=str(first_id),
                reference=reference,
                link=link,
                figure=fig,
            )
        )
    missing = await session.scalar(
        select(func.count()).select_from(table).where(or_(lat.is_(None), lng.is_(None)))
    )
    return rows, skipped + (missing or 0)


@router.get("/sites", response_model=MapSites)
async def get_map_sites(session: AsyncSession = Depends(get_session)) -> MapSites:
    """
    Every site with data, with its count per database and its experimental
    programs. Cached like the other data URLs (bumped by /upload).
    """
    rows: List[ProgramRow] = []
    skipped = 0
    # One query per table, in turn: they are small and share one session.
    for source in _SOURCES:
        source_rows, source_skipped = await _rows(session, source)
        rows.extend(source_rows)
        skipped += source_skipped
    return MapSites(sites=merge_rows(rows), skipped=skipped)
