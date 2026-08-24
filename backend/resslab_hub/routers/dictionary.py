"""
Serve the data dictionary (column metadata for every component database).
"""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.models.api import DatabaseReadmeModel, DictionaryColumnModel
from resslab_hub.models.database.dictionary import DatabaseReadme, DictionaryColumn
from resslab_hub.utils.database import get_session

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


@router.get("", response_model=Dict[str, List[DictionaryColumnModel]])
async def get_dictionary(
    session: AsyncSession = Depends(get_session),
) -> Dict[str, List[DictionaryColumnModel]]:
    """
    All dictionaries keyed by database id, columns in source-CSV order.
    """
    rows = await session.execute(
        select(DictionaryColumn).order_by(
            DictionaryColumn.database, DictionaryColumn.position
        )
    )
    dictionary: Dict[str, List[DictionaryColumnModel]] = {}
    for row in rows.scalars():
        dictionary.setdefault(row.database, []).append(
            DictionaryColumnModel(
                name=row.column_name,
                description=row.description,
                symbol=row.symbol,
                unit=row.unit,
                type=row.type,
                example=row.example,
                nullable=row.nullable,
            )
        )
    return dictionary


@router.get("/{database}/readme", response_model=DatabaseReadmeModel)
async def get_database_readme(
    database: str,
    session: AsyncSession = Depends(get_session),
) -> DatabaseReadmeModel:
    """
    The contributor guide of one database: the README.md of its data-repo
    folder, uploaded alongside the data. Raw markdown; the frontend renders it.
    """
    readme = await session.get(DatabaseReadme, database)
    if readme is None:
        raise HTTPException(status_code=404, detail=f"No README for {database}")
    return DatabaseReadmeModel(database=readme.database, content=readme.content)
