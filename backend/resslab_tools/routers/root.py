"""
Handle / requests
"""
from fastapi import APIRouter
from resslab_tools import __name__, __version__
from resslab_tools.models import Info

router = APIRouter()


@router.get('/', response_model=Info)
async def root() -> Info:
    return Info(
        name=__name__,
        version=__version__
    )
