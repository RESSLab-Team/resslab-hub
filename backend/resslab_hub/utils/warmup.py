"""
Response-cache warming — no visitor ever pays the cold path.

The data API's cold path is expensive: the dataset queries run per-row
correlated ``*_count`` subqueries against the multi-hundred-MB time-series
tables, and on a cold Postgres (fresh pod, restarted database, evicted
buffers) the first request per URL costs seconds (measured up to 9 s on
stage). The response cache (utils/caching.py) hides that from every visitor
except the first one per URL per hour.

This module removes the "first visitor" case. On startup the app renders the
known hot URL space through its own ASGI stack — storing the bodies in the
response cache and warming Postgres's buffers — then re-renders it shortly
before the entries would expire, so the cache never goes cold while the
process lives. ``/readyz`` (routers/root.py) reports 503 until the first pass
finishes, so the deployment's readinessProbe holds traffic on fresh pods
until they are warm.
"""

import asyncio
import logging

import httpx

from resslab_hub.utils.caching import REFRESH_HEADER, refresh_token

logger = logging.getLogger("resslab_hub.warmup")

# The frontend's cold-start burst (stores/counts.ts + each dashboard's
# dataset fetch): per database tab the whole-table page, the two sidebar-badge
# distinct calls, and the shared dictionary. The per-tab "sources" field
# mirrors sourcesFetcherFor in stores/counts.ts.
_SOURCE_FIELDS = {
    "braces": "investigator",
    "columns": "experimental_program",
    "connections": "experimental_program",
    "materials": "experimental_program",
    "tensile-coupon": "experimental_program",
    "ductile-fracture": "experimental_program",
    "residual-stress": "experimental_program",
    "hss-column": "reference",
    "eccentric-braced-frame": "investigator",
}


def warm_paths() -> list:
    paths = ["/dictionary"]
    for prefix, source_field in _SOURCE_FIELDS.items():
        paths.append(f"/{prefix}?page=1&size=1000")
        paths.append(f"/{prefix}/distinct")
        paths.append(f"/{prefix}/distinct?fields={source_field}")
    return paths


async def _render_all(client: httpx.AsyncClient, refresh: bool) -> None:
    # Sequential on purpose: warming competes with live traffic for the event
    # loop and the DB pool, so one query at a time keeps the impact low.
    headers = {REFRESH_HEADER: refresh_token()} if refresh else {}
    for path in warm_paths():
        try:
            response = await client.get(path, headers=headers)
            if response.status_code != 200:
                logger.warning("warmup: %s -> %d", path, response.status_code)
        except Exception as exc:
            logger.warning("warmup: %s failed: %s", path, exc)


def install(app, interval: float) -> None:
    """
    Register startup warming + periodic refresh on ``app``.

    ``interval`` is the refresh period in seconds — pass something below the
    response cache's max_age so entries are re-rendered before they expire.
    Non-positive (dev: caching disabled) marks the app warmed and does
    nothing else.
    """
    app.state.warmed = interval <= 0
    if interval <= 0:
        return

    @app.on_event("startup")
    async def _start_warmup() -> None:
        async def _run() -> None:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://warmup"
            ) as client:
                await _render_all(client, refresh=False)
                app.state.warmed = True
                logger.info("initial warmup done (%d URLs)", len(warm_paths()))
                while True:
                    await asyncio.sleep(interval)
                    await _render_all(client, refresh=True)

        asyncio.create_task(_run())
