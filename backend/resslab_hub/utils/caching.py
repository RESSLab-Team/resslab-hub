"""
HTTP caching for the read-only data API — browser-side and server-side.

The datasets are static between uploads (POST /upload), and the frontend
fetches each dataset wholesale once per visit, so the hot URL space is small
and identical for every visitor. Freshness rides on a process-wide *data
version* token, invalidated by :func:`bump_data_version` after a successful
upload. Two layers share it:

1. Browser side: every 200 JSON GET carries the token as a weak ETag plus
   ``Cache-Control: max-age=...``. Within ``max_age`` the browser doesn't ask
   at all; after it, a revalidation whose ``If-None-Match`` matches the token
   is answered 304 *before* the request reaches the database.

2. Server side: the rendered JSON bytes of each URL are kept in an in-process
   LRU, so only the first request for a URL after a (re)start or an upload
   pays the SQL + serialization cost — every other visitor gets the stored
   bytes without touching the database. Entries die with the data version,
   after ``max_age`` seconds (the token is per-process, so this bounds
   staleness on replicas that didn't handle the upload to the same window the
   browser cache already has), or by LRU eviction under a byte budget.

Deliberately per-process, no shared store: a restart or a second worker just
means a fresh token and an empty cache — never stale data beyond ``max_age``.
"""

import time
from collections import OrderedDict
from secrets import token_hex
from typing import Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_data_version = token_hex(8)

# The periodic cache warmer (utils/warmup.py) re-renders entries *before* they
# expire, which requires bypassing both the 304 shortcut and the stored-body
# lookup while still storing the fresh result. The bypass is gated on a
# per-process secret so external clients can't use it to hammer the database.
REFRESH_HEADER = "x-cache-refresh"
_refresh_token = token_hex(16)


def refresh_token() -> str:
    return _refresh_token


def bump_data_version() -> None:
    """Invalidate every cached data response (call after a successful upload)."""
    global _data_version
    _data_version = token_hex(8)


def data_etag() -> str:
    return f'W/"{_data_version}"'


# Whole-dataset JSON payloads run a few MB each and the hot URL space is small
# (per component: dataset + fields/counts/range/matrix/distinct), so 64 MiB
# holds it comfortably. Oversized outliers are skipped rather than allowed to
# flush everything else out.
_MAX_TOTAL_BYTES = 64 * 2**20
_MAX_ENTRY_BYTES = 8 * 2**20


class HTTPCacheMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_age: int):
        super().__init__(app)
        self.max_age = max_age
        # url -> (data version, monotonic expiry, content-type, body)
        self._entries: "OrderedDict[str, Tuple[str, float, str, bytes]]" = OrderedDict()
        self._total_bytes = 0

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method != "GET" or _excluded(request.url.path):
            return await call_next(request)
        version = _data_version
        etag = data_etag()
        headers = {"ETag": etag, "Cache-Control": f"public, max-age={self.max_age}"}
        refreshing = request.headers.get(REFRESH_HEADER) == _refresh_token
        # Only JSON data responses ever receive this ETag, so a match proves
        # the client already holds the current data version — answer without
        # running the endpoint (no database round-trip).
        if not refreshing and etag in request.headers.get("if-none-match", ""):
            return Response(status_code=304, headers=headers)
        key = f"{request.url.path}?{request.url.query}"
        stored = None if refreshing else self._lookup(key, version)
        if stored is not None:
            content_type, body = stored
            return Response(content=body, media_type=content_type, headers=headers)
        response = await call_next(request)
        if response.status_code != 200 or not response.headers.get(
            "content-type", ""
        ).startswith("application/json"):
            return response
        # JSON responses are rendered in one piece, so draining the iterator
        # costs nothing extra; streaming CSVs never reach this point.
        body = b"".join([chunk async for chunk in response.body_iterator])
        if _data_version == version:  # no upload landed mid-request
            self._store(key, version, response.headers["content-type"], body)
        return Response(
            content=body,
            status_code=200,
            headers={**dict(response.headers), **headers},
        )

    def _lookup(self, key: str, version: str) -> Optional[Tuple[str, bytes]]:
        entry = self._entries.get(key)
        if entry is None:
            return None
        entry_version, expires, content_type, body = entry
        if entry_version != version or time.monotonic() >= expires:
            self._delete(key)
            return None
        self._entries.move_to_end(key)
        return content_type, body

    def _store(self, key: str, version: str, content_type: str, body: bytes) -> None:
        if len(body) > _MAX_ENTRY_BYTES:
            return
        if key in self._entries:
            self._delete(key)
        expires = time.monotonic() + self.max_age
        self._entries[key] = (version, expires, content_type, body)
        self._total_bytes += len(body)
        while self._total_bytes > _MAX_TOTAL_BYTES:
            self._delete(next(iter(self._entries)))

    def _delete(self, key: str) -> None:
        _, _, _, body = self._entries.pop(key)
        self._total_bytes -= len(body)


def _excluded(path: str) -> bool:
    # Analytics computes live user counts, root/healthz/readyz are deployment
    # probes, docs are dev-facing. CSV downloads are skipped by the
    # content-type check. Contributions live on GitHub and move on their own,
    # so an hour-old copy would show a submission that no longer exists and
    # make every update collide (#321).
    return path in ("/", "/healthz", "/readyz") or path.startswith(
        ("/analytics", "/contributions", "/docs", "/redoc", "/openapi")
    )
