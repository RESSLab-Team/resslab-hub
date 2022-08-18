"""
Handle / requests
"""
from fastapi import APIRouter

from resslab_hub import __name__ as name
from resslab_hub import __version__
from resslab_hub.models import Info

router = APIRouter()


@router.get("/", response_model=Info)
async def root() -> Info:
    """
    Get Info
    """
    return Info(name=name, version=__version__)
