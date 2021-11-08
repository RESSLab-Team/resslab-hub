"""
Handle /connections requests
"""
from fastapi import APIRouter
from fastapi_pagination import Page
from fastapi_pagination.ext.databases import paginate
from resslab_tools.models.api import Connection as ConnectionModel
from resslab_tools.models.database import Connection
from resslab_tools.services.database import database
from sqlalchemy import select

router = APIRouter(
    prefix='/connections',
    tags=['connections'],
)


@router.get('', response_model=Page[ConnectionModel])
async def get_connections():
    """
    Get paginated Connections
    """
    return await paginate(database, select(Connection))
