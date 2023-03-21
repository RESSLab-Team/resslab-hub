"""
Entrypoint for FastAPI application
https://fastapi.tiangolo.com/tutorial/bigger-applications/
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from resslab_hub import __name__ as title
from resslab_hub import __version__
from resslab_hub.config import settings
from resslab_hub.routers import (
    analytics,
    braces,
    columns,
    connections,
    materials,
    residual_stress,
    root,
)
from resslab_hub.utils.database import upgrade_database
from resslab_hub.utils.fastapi import use_route_names_as_operation_ids

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=title,
    version=__version__,
    root_path=settings.root_path,  # type: ignore
)

if settings.cors_enabled:
    logging.debug("cors enabled")
else:
    logging.warning("cors disabled")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(root.router)
app.include_router(analytics.router)
app.include_router(braces.router)
app.include_router(columns.router)
app.include_router(connections.router)
app.include_router(materials.router)
app.include_router(residual_stress.router)
add_pagination(app)
use_route_names_as_operation_ids(app)

if settings.database_upgrade:
    upgrade_database()
