"""
Entrypoint for FastAPI application
https://fastapi.tiangolo.com/tutorial/bigger-applications/
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from resslab_tools import __name__, __version__
from resslab_tools.config import settings
from resslab_tools.routers import root

app = FastAPI(
    title=__name__,
    version=__version__,
    root_path=settings.get('root_path'),
)

if settings.get('cors_enabled'):
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
