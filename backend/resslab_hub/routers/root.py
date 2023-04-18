"""
Handle / requests
"""
from secrets import compare_digest
from tarfile import open
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from resslab_hub import __name__ as name
from resslab_hub import __version__
from resslab_hub.config import settings
from resslab_hub.data.uploader import Type, upload_all
from resslab_hub.models import Info

router = APIRouter()

security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """
    https://fastapi.tiangolo.com/advanced/security/http-basic-auth/
    """
    current_username = credentials.username
    correct_username: str = settings.api_username  # type: ignore
    is_correct_username = compare_digest(current_username, correct_username)
    current_password = credentials.password
    correct_password: str = settings.api_password  # type: ignore
    is_correct_password = compare_digest(current_password, correct_password)
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return credentials.username


@router.get("/", response_model=Info)
async def root() -> Info:
    """
    Get Info
    """
    return Info(name=name, version=__version__)


@router.post("/upload", dependencies=[Depends(get_current_username)])
async def create_upload_file(
    file: UploadFile = File(...),
    type: Type = Query(...),
):
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
