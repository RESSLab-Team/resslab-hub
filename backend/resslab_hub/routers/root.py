"""
Handle / requests
"""
from tarfile import open
from tempfile import TemporaryDirectory

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.exceptions import HTTPException

from resslab_hub import __name__ as name
from resslab_hub import __version__
from resslab_hub.data.uploader import Type, upload_all
from resslab_hub.models import Info

router = APIRouter()


@router.get("/", response_model=Info)
async def root() -> Info:
    """
    Get Info
    """
    return Info(name=name, version=__version__)


@router.post("/upload")
async def create_upload_file(file: UploadFile = File(...), type: Type = Query(...)):
    try:
        with TemporaryDirectory() as tmpdir:
            with open(fileobj=file.file, mode="r:gz") as tar_file:
                tar_file.extractall(tmpdir)
            upload_all(type, [tmpdir])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        await file.close()
    return {"message": f"Successfuly uploaded {file.filename}"}
