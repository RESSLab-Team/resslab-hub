"""
Entrypoint for FastAPI application
https://fastapi.tiangolo.com/tutorial/bigger-applications/
"""

import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi_pagination import add_pagination
from githubkit.exception import RequestFailed
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from resslab_hub import __name__ as title
from resslab_hub import __version__
from resslab_hub.auth import mailer
from resslab_hub.auth.csrf import CSRFMiddleware
from resslab_hub.config import refuse_default_secrets, settings
from resslab_hub.contributions.github import aclose_github, describe_error
from resslab_hub.routers import (
    admin,
    agent,
    analytics,
    auth,
    braces,
    columns,
    connections,
    contributions,
    curation,
    dictionary,
    ductile_fracture,
    eccentric_braced_frame,
    hss_columns,
    materials,
    residual_stress,
    root,
    tensile_coupon,
    verification,
)
from resslab_hub.routers import map as map_router
from resslab_hub.utils.caching import HTTPCacheMiddleware
from resslab_hub.utils.database import upgrade_database
from resslab_hub.utils.rate_limit import limiter
from resslab_hub.utils.warmup import warmup


# Function to determine if --log-level debug is set
def is_debug_mode():
    return "--log-level" in sys.argv and "debug" in sys.argv


# A deployment with a default or missing secret must not serve requests.
# Raise before the app exists, so the reason is the last line of the pod log.
refuse_default_secrets()

logger = logging.getLogger()

logger.setLevel(logging.DEBUG if is_debug_mode() else logging.INFO)
logger.propagate = True

logger.debug("Debug logging enabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Say in the log where the sign-in mails go, loud when nowhere (#247).
    mailer.check_at_startup()
    try:
        # Warm the response cache at startup (readinessProbe on /readyz waits
        # for it) and refresh entries before they expire, so no visitor ever
        # pays the cold database path. Refresh at 80% of the cache TTL;
        # disabled with caching (dev).
        async with warmup(app, interval=settings.cache_max_age * 0.8):
            yield
    finally:
        # Release the GitHub App's shared connection pool (contributions).
        await aclose_github()


app = FastAPI(
    lifespan=lifespan,
    title=title,
    debug=is_debug_mode(),  # Set debug mode based on log level
    version=__version__,
    root_path=settings.root_path,  # type: ignore
    # Short operation ids, so the generated client has short function names.
    generate_unique_id_function=lambda route: route.name,
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down and retry."},
    )


# Cache the read-only data endpoints (see utils/caching.py): browser-side
# via ETag + max-age, server-side via an in-process store of rendered JSON
# bodies. Added first so it sits innermost — it must see (and store)
# uncompressed bodies; GZip below then compresses every response, cache hits
# included, on the way out. Dev sets cache_max_age = 0 so local data reloads
# show up immediately.
if settings.cache_max_age > 0:
    app.add_middleware(HTTPCacheMiddleware, max_age=settings.cache_max_age)

# Compress JSON/CSV responses (highly compressible numeric payloads).
# minimum_size avoids the overhead of compressing tiny responses.
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Refuse cookie-authenticated writes that another site started (#247). There
# is no CORS layer to pair it with any more: the app is same-origin everywhere,
# behind Traefik in the deployments and behind the Vite proxy in development,
# so nothing legitimate is cross-origin. Requests carrying no session cookie
# (the data-repo CI with its Basic credential) pass through untouched.
app.add_middleware(CSRFMiddleware)

# Timestamped per-request log line + Server-Timing response header, so a slow
# request seen in the browser can be split into in-app time (this number,
# shown by devtools in the Network → Timing tab) vs. time spent in the
# LB/ingress path in front of the pod. Declared after the add_middleware
# calls above so it wraps them (outermost): the duration covers cache hits,
# gzip and endpoint work alike.
_timing_logger = logging.getLogger("resslab_hub.timing")
# stdout, not the default stderr: uvicorn's access log writes to stdout and
# these lines belong beside it in `kubectl logs`.
_timing_handler = logging.StreamHandler(sys.stdout)
_timing_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
_timing_logger.addHandler(_timing_handler)
_timing_logger.setLevel(logging.INFO)
_timing_logger.propagate = False


@app.middleware("http")
async def server_timing(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["Server-Timing"] = f"app;dur={duration_ms:.0f}"
    if request.url.path not in ("/", "/healthz", "/readyz"):  # probe endpoints
        query = f"?{request.url.query}" if request.url.query else ""
        _timing_logger.info(
            "%s %s%s -> %d in %.0f ms",
            request.method,
            request.url.path,
            query,
            response.status_code,
            duration_ms,
        )
    return response


# A GitHub call that a route did not catch (the data repo refused a commit,
# a pull request, a read). It is GitHub that failed, so 502, and with
# GitHub's own reason: a bare 500 sent people to the logs for a 403.
@app.exception_handler(RequestFailed)
async def github_error_handler(request: Request, exc: RequestFailed):
    detail = describe_error(exc)
    logger.error(f"{detail} ({exc.request.method} {exc.request.url.path})")
    return JSONResponse(status_code=502, content={"detail": detail})


# Custom error handler for detailed logging
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP Exception: {exc.detail}")
    # Keep the headers the raiser set: a 401 from the machine-credential path
    # carries WWW-Authenticate, which is what makes `curl -f -u ...` report a
    # bad password cleanly instead of a bare 401.
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


# Anything no other handler caught. Without this, Starlette answers a plain
# text "Internal Server Error", and a script that reads JSON (the data CI)
# can't say what went wrong. Fixed message: the details stay in the logs.
@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error ({request.method} {request.url.path})")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(root.router)
app.include_router(auth.router)
app.include_router(contributions.router)
app.include_router(curation.router)
app.include_router(verification.router)
app.include_router(admin.router)
app.include_router(analytics.router)
app.include_router(dictionary.router)
app.include_router(agent.router)
app.include_router(braces.router)
app.include_router(columns.router)
app.include_router(connections.router)
app.include_router(materials.router)
app.include_router(residual_stress.router)
app.include_router(hss_columns.router)
app.include_router(eccentric_braced_frame.router)
app.include_router(tensile_coupon.router)
app.include_router(ductile_fracture.router)
app.include_router(map_router.router)
add_pagination(app)

if settings.database_upgrade:
    upgrade_database()
