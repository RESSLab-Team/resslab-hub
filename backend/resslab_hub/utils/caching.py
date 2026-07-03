"""
Client-side HTTP caching for the read-only data API.

The datasets are static between uploads (POST /upload), and the frontend
fetches each dataset wholesale once per visit — so letting browsers cache
those GETs saves an entire dataset per navigation. Freshness rides on a
process-wide *data version* token: every 200 JSON GET carries it as a weak
ETag plus ``Cache-Control: max-age=...``. Within ``max_age`` the browser
doesn't ask at all; after it, a revalidation whose ``If-None-Match`` matches
the token is answered 304 *before* the request reaches the database. A
successful upload bumps the token, so new data is served on the next
revalidation.

Deliberately per-process, no shared store: a restart or a second worker just
means a fresh token, which downgrades a would-be 304 into a full 200 — never
stale data.
"""

from secrets import token_hex

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_data_version = token_hex(8)


def bump_data_version() -> None:
    """Invalidate every cached data response (call after a successful upload)."""
    global _data_version
    _data_version = token_hex(8)


def data_etag() -> str:
    return f'W/"{_data_version}"'


class HTTPCacheMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_age: int):
        super().__init__(app)
        self.max_age = max_age

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method != "GET" or _excluded(request.url.path):
            return await call_next(request)
        etag = data_etag()
        headers = {"ETag": etag, "Cache-Control": f"public, max-age={self.max_age}"}
        # Only JSON data responses ever receive this ETag, so a match proves
        # the client already holds the current data version — answer without
        # running the endpoint (no database round-trip).
        if etag in request.headers.get("if-none-match", ""):
            return Response(status_code=304, headers=headers)
        response = await call_next(request)
        if response.status_code == 200 and response.headers.get(
            "content-type", ""
        ).startswith("application/json"):
            response.headers.update(headers)
        return response


def _excluded(path: str) -> bool:
    # Analytics computes live user counts, root/healthz are deployment probes,
    # docs are dev-facing. CSV downloads are skipped by the content-type check.
    return path in ("/", "/healthz") or path.startswith(
        ("/analytics", "/docs", "/redoc", "/openapi")
    )
