"""
Handle / requests
"""

from secrets import compare_digest
from tarfile import open
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from resslab_hub import __name__ as name
from resslab_hub import __version__
from resslab_hub.config import settings
from resslab_hub.data.uploader import Type, upload_all
from resslab_hub.data.validator import validate_all
from resslab_hub.models import Info

router = APIRouter()

security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)) -> str:
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
            [primary_uploads, secondary_uploads] = upload_all(type, [tmpdir])
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Upload successful",
                    "primary_uploads": primary_uploads,
                    "secondary_uploads": secondary_uploads,
                },
            )
    except Exception:
        print("HTTP 500", Exception)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(Exception)
        )
    finally:
        await file.close()


@router.post("/validate", dependencies=[Depends(get_current_username)])
async def validate_data(
    file: UploadFile = File(...),
    type: Type = Query(...),
):
    try:
        with TemporaryDirectory() as tmpdir:
            with open(fileobj=file.file, mode="r:gz") as tar_file:
                tar_file.extractall(tmpdir)

            results = validate_all(type, [tmpdir])

            response = {
                "valid": all(result.is_valid() for result in results),
                "results": [
                    {
                        "file": result.filename,
                        "valid": result.is_valid(),
                        "errors": [str(err) for err in result.errors],
                        "warnings": [str(warn) for warn in result.warnings],
                    }
                    for result in results
                ],
            }
            # If any validation errors exist, return 422
            if not response["valid"]:
                return HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(response),
                )
            return JSONResponse(status_code=status.HTTP_200_OK, content=response)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(Exception)
        )
    finally:
        await file.close()


@router.get("/user")
async def get_user(username: str = Depends(get_current_username)):
    return {"username": username}
