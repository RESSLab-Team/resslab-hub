"""
Refuse cookie-authenticated writes that another site started.

The app is same-origin everywhere: Traefik serves the SPA and the API from one
host in the deployments, and a Vite proxy does the same in development. So a
state-changing request carrying our session cookie must have been sent by our
own pages, and this middleware checks exactly that.

``Sec-Fetch-Site`` is the real check (every browser we support sends it, and it
cannot be set by page JavaScript). ``same-origin`` is our own fetch; ``none``
is the user typing a URL or following a mailed link. The ``Origin`` header is
the fallback for anything that omits it.

Requests with no session cookie are left alone: that is the machine path, where
curl with the Basic credential sends neither header, and where there is no
cookie for another site to ride on.
"""

from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from resslab_hub.auth.sessions import SESSION_COOKIE

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _host(value: Optional[str]) -> str:
    """Host of an Origin/Referer header, ignoring scheme and path."""
    if not value or value == "null":
        return ""
    without_scheme = value.split("://", 1)[-1]
    return without_scheme.split("/", 1)[0].lower()


def is_same_origin(request: Request) -> bool:
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site:
        return fetch_site in ("same-origin", "none")
    origin = request.headers.get("origin")
    if origin:
        # Behind the proxy the Host header is the public host, and the Vite
        # dev proxy is configured without changeOrigin for the same reason.
        return _host(origin) == _host(request.headers.get("host"))
    # No Origin either: not a browser cross-site request. Anything a form or
    # fetch sends cross-site carries one.
    return True


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if (
            request.method not in SAFE_METHODS
            and request.cookies.get(SESSION_COOKIE)
            and not is_same_origin(request)
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-site request refused."},
            )
        return await call_next(request)
