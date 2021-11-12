"""
Entrypoint for FastAPI application
https://fastapi.tiangolo.com/tutorial/bigger-applications/
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

# pylint: disable=unused-import
import resslab_tools.models.database  # type: ignore
from resslab_tools import __name__ as title
from resslab_tools import __version__
from resslab_tools.config import settings
from resslab_tools.routers import connections, root
from resslab_tools.services.database import engine, metadata

app = FastAPI(
    title=title,
    version=__version__,
    root_path=settings.root_path,  # type: ignore
)

if settings.cors_enabled:  # type: ignore
    print('cors enabled')
else:
    print('cors disabled')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

app.include_router(root.router)
app.include_router(connections.router)
add_pagination(app)


async def async_main():
    """
    async main from https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html
    """
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)  # type: ignore
    await engine.dispose()


@app.on_event("startup")
async def startup():
    """
    on FastAPI startup
    """
    await async_main()
