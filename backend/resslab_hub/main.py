"""
Entrypoint for FastAPI application
https://fastapi.tiangolo.com/tutorial/bigger-applications/
"""

import logging
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi_pagination import add_pagination
from starlette.exceptions import HTTPException as StarletteHTTPException

from resslab_hub import __name__ as title
from resslab_hub import __version__
from resslab_hub.config import settings
from resslab_hub.routers import (
    analytics,
    braces,
    columns,
    connections,
    ductile_fracture,
    eccentric_braced_frame,
    hss_columns,
    materials,
    residual_stress,
    root,
    tensile_coupon,
)
from resslab_hub.utils.database import upgrade_database
from resslab_hub.utils.fastapi import use_route_names_as_operation_ids


# Function to determine if --log-level debug is set
def is_debug_mode():
    return "--log-level" in sys.argv and "debug" in sys.argv


logger = logging.getLogger()

logger.setLevel(logging.DEBUG if is_debug_mode() else logging.INFO)
logger.propagate = True

logger.debug("Debug logging enabled")

app = FastAPI(
    title=title,
    debug=is_debug_mode(),  # Set debug mode based on log level
    version=__version__,
    root_path=settings.root_path,  # type: ignore
)

# Compress JSON/CSV responses (highly compressible numeric payloads).
# minimum_size avoids the overhead of compressing tiny responses.
app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.cors_enabled:
    logging.debug("cors enabled")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    logging.warning("cors disabled")


# Custom error handler for detailed logging
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP Exception: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(root.router)
app.include_router(analytics.router)
app.include_router(braces.router)
app.include_router(columns.router)
app.include_router(connections.router)
app.include_router(materials.router)
app.include_router(residual_stress.router)
app.include_router(hss_columns.router)
app.include_router(eccentric_braced_frame.router)
app.include_router(tensile_coupon.router)
app.include_router(ductile_fracture.router)
add_pagination(app)
use_route_names_as_operation_ids(app)

if settings.database_upgrade:
    upgrade_database()
