"""
Refuse writes that another site started.

The app is same-origin everywhere (Traefik in the deployments, the Vite proxy
in development), so every state-changing request from a browser must come
from our own pages. ``Sec-Fetch-Site`` says so and cannot be set by page
JavaScript; ``Origin`` is the fallback for the few clients that omit it.

Every unsafe request is checked, not only those carrying our session cookie:
the sign-in endpoints have no cookie yet and are the classic login-CSRF
target. Non-browser clients (curl with the machine credential) send neither
header and pass.
"""

from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _host(value: Optional[str]) -> str:
    """Host of an Origin header, ignoring scheme and path."""
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
        return _host(origin) == _host(request.headers.get("host"))
    # Neither header: not a browser. Every cross-site form or fetch sends one.
    return True


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method not in SAFE_METHODS and not is_same_origin(request):
            return JSONResponse(
                status_code=403, content={"detail": "Cross-site request refused."}
            )
        return await call_next(request)
